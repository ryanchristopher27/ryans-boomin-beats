import Foundation
import UIKit

/// One entry in the app-owned queue. `id` identifies this *entry*, not the track,
/// so the same song can be queued twice and "play later" can re-add a copy.
struct QueueItem: Codable, Identifiable, Equatable {
    var id = UUID()
    let trackID: String
    let title: String
    let artists: [String]
    let image: String
    /// Set when a track already sent to Spotify is removed or moved. Spotify's
    /// queue can't be edited, so the app skips it when it comes up instead.
    var skipOnArrival = false
    /// Added by Autofill/Driver rather than the host (DJ4). Optional so queues
    /// saved before DJ4 still decode — synthesized Codable ignores defaults.
    var addedByDJ: Bool?

    var artistLine: String { artists.joined(separator: ", ") }
    var imageURL: URL? { URL(string: image) }
}

/// A track that appeared in Spotify's queue without the app sending it: a
/// guest's Jam add, or someone queuing directly in Spotify (DJ5).
struct GuestRequest: Codable, Identifiable, Equatable {
    var id = UUID()
    let trackID: String
    let title: String
    let artists: [String]
    let image: String

    var artistLine: String { artists.joined(separator: ", ") }
    var imageURL: URL? { URL(string: image) }
}

/// The app-owned queue (DJ2).
///
/// Spotify's queue only accepts additions, so the editable queue lives here and
/// Spotify only ever holds `sent` — tracks already handed over, in order.
///
/// Adaptive buffer (decided 2026-10-23, replacing the plan's fixed 5): while the
/// app is in the foreground only ONE track is kept ahead in Spotify, so everything
/// after the next song stays freely editable. On the way to the background the
/// buffer is topped up to `Config.backgroundBufferDepth` so music keeps playing
/// while the app is suspended. If iOS kills the app without a background
/// transition, Spotify falls back to autoplay after one song — the known ceiling.
@MainActor
@Observable
final class QueueStore {
    private(set) var sent: [QueueItem] = [] { didSet { save() } }
    private(set) var upcoming: [QueueItem] = [] { didSet { save() } }
    /// Pending guest requests, oldest first (DJ5).
    private(set) var requests: [GuestRequest] = [] { didSet { save() } }
    /// Guest tracks to skip when they come up (declined, or moved "Later").
    /// An array, not a set: the same song can be requested twice.
    private var guestSkips: [String] = [] { didSet { save() } }
    /// Guest tracks the host chose to keep, so they aren't flagged again
    /// while they wait in Spotify's queue. Cleared on arrival.
    private var keptGuests: Set<String> = [] { didSet { save() } }
    /// The previous queue view, for the insertion rule in `detectRequests`.
    private var lastQueueView: [String]?
    private(set) var message: String?
    /// Track ids the app skipped itself (skip-on-arrival), so they aren't
    /// mistaken for the host skipping them.
    private(set) var autoSkipped: Set<String> = []

    /// Tracks lined up after the current one.
    var aheadCount: Int { sent.filter { !$0.skipOnArrival }.count + upcoming.count }

    /// Only the primary device drives Spotify (SY3, Jam-style): it sends tracks,
    /// skips on arrival, and detects requests. Participants just edit the shared
    /// queue. True when sync is off, so a single device behaves as before.
    var isPrimary = true
    /// Called after any change to a synced field, for DJSync to push.
    var onChange: (() -> Void)?

    /// Keeps the screen awake while hosting. Deliberately not persisted, so the
    /// idle timer is never left disabled by a forgotten setting.
    var partyMode = false {
        didSet { UIApplication.shared.isIdleTimerDisabled = partyMode }
    }

    private static let foregroundDepth = 1

    private let client: APIClient
    private var lastTrackID: String?
    private var isToppingUp = false
    private var backgroundTask = UIBackgroundTaskIdentifier.invalid

    init(client: APIClient) {
        self.client = client
        load()
    }

    // MARK: - Edits

    func add(_ item: QueueItem) async {
        upcoming.append(item)
        await topUp(to: Self.foregroundDepth)
    }

    func moveUpcoming(from source: IndexSet, to destination: Int) {
        upcoming.move(fromOffsets: source, toOffset: destination)
    }

    func removeUpcoming(at offsets: IndexSet) {
        upcoming.remove(atOffsets: offsets)
    }

    /// Removing a sent track can't take it out of Spotify; it gets skipped on
    /// arrival, and a replacement is sent so the buffer stays at depth.
    func removeSent(_ item: QueueItem) async {
        markSkip(item)
        await topUp(to: Self.foregroundDepth)
    }

    /// Skip it where it is and re-add a fresh copy at the end of Up Next.
    func playLater(_ item: QueueItem) async {
        markSkip(item)
        upcoming.append(QueueItem(trackID: item.trackID, title: item.title, artists: item.artists, image: item.image))
        await topUp(to: Self.foregroundDepth)
    }

    private func markSkip(_ item: QueueItem) {
        guard let i = sent.firstIndex(where: { $0.id == item.id }) else { return }
        sent[i].skipOnArrival = true
    }

    // MARK: - Playback events

    /// Called after every player-state poll. Acts only when the track changes,
    /// and only on the primary (participants learn the result through sync).
    func observe(_ state: PlaybackState) async {
        guard isPrimary, let trackID = state.track?.id, trackID != lastTrackID else { return }
        lastTrackID = trackID

        // Guest skips first: after "Later" the app re-sends the same track, but the
        // guest's copy was queued earlier, so it is the one arriving now.
        if let i = guestSkips.firstIndex(of: trackID) {
            guestSkips.remove(at: i)
            await skipCurrent(trackID)
        } else {
            let (remaining, arrived) = Self.arrival(of: trackID, in: sent)
            sent = remaining
            if let arrived {
                if arrived.skipOnArrival { await skipCurrent(trackID) }
            } else {
                // A request that arrives undecided just plays: Spotify already put it there.
                requests.removeAll { $0.trackID == trackID }
                keptGuests.remove(trackID)
            }
        }
        await topUp(to: Self.foregroundDepth)
    }

    private func skipCurrent(_ trackID: String) async {
        autoSkipped.insert(trackID)
        _ = try? await client.post("player/next/", body: NoBody()) as CommandResult
        // What plays next may be the same track id (after "Later", the app's own
        // copy follows the skipped guest copy), which the track-change check in
        // `observe` would miss, leaving a stale `sent` entry that blocks top-ups.
        // Forget the last track so the next poll re-observes whatever is playing.
        lastTrackID = nil
    }

    /// On return to the foreground: drop sent tracks that played while the app
    /// was suspended, using Spotify's real queue as the source of truth.
    func reconcile(with state: PlaybackState) async {
        guard isPrimary else { return }
        lastTrackID = nil
        await observe(state)

        guard let response: SpotifyQueue = try? await client.get("player/queue/") else { return }
        sent = Self.reconciled(sent, against: response.queue.map(\.id))
        record(response.queue, smartShuffle: state.smartShuffle ?? false)
        await topUp(to: Self.foregroundDepth)
    }

    // MARK: - Guest requests (DJ5)

    /// Read Spotify's queue and pick up new guest requests. Called on a ~10s
    /// cadence while the app is in the foreground.
    func pollRequests(smartShuffle: Bool) async {
        guard isPrimary, let response: SpotifyQueue = try? await client.get("player/queue/") else { return }
        record(response.queue, smartShuffle: smartShuffle)
    }

    private func record(_ queue: [Track], smartShuffle: Bool) {
        let view = queue.map(\.id)
        let found = Self.detectRequests(
            previous: lastQueueView,
            current: view,
            appIDs: Set(sent.map(\.trackID)),
            ignoring: Set(requests.map(\.trackID)).union(keptGuests).union(guestSkips),
            insertionsAllowed: !smartShuffle
        )
        requests += found.map { i in
            let t = queue[i]
            return GuestRequest(trackID: t.id, title: t.title, artists: t.artists, image: t.image)
        }
        lastQueueView = view
    }

    /// Leave it where Spotify put it.
    func keep(_ request: GuestRequest) {
        requests.removeAll { $0.id == request.id }
        keptGuests.insert(request.trackID)
    }

    /// Skip it when it comes up and add it to the end of Up Next instead.
    func later(_ request: GuestRequest) async {
        requests.removeAll { $0.id == request.id }
        guestSkips.append(request.trackID)
        upcoming.append(QueueItem(trackID: request.trackID, title: request.title, artists: request.artists, image: request.image))
        await topUp(to: Self.foregroundDepth)
    }

    /// Skip it when it comes up.
    func decline(_ request: GuestRequest) {
        requests.removeAll { $0.id == request.id }
        guestSkips.append(request.trackID)
    }

    // MARK: - Pure queue logic (unit-tested in BoominBeatsTests)

    /// Indices in `current` (Spotify's queue view) that are guest requests.
    ///
    /// Two signals, either is enough:
    /// - **Wedged:** a non-app track ahead of one of the app's own tracks. Spotify
    ///   plays the user queue first-in, first-out before the context, so only a
    ///   queued track can sit there (the DJ0.1 finding). Reliable, but typically
    ///   one top-up late, since the app keeps only one track ahead.
    /// - **Inserted:** a track absent from the previous view that now sits before
    ///   the last track the two views share. Context tracks only ever enter the
    ///   view at its tail as it slides, so a mid-view newcomer was queued by
    ///   someone. Catches requests on the next poll. Off under Smart Shuffle,
    ///   which inserts its own recommendations mid-queue.
    nonisolated static func detectRequests(
        previous: [String]?,
        current: [String],
        appIDs: Set<String>,
        ignoring: Set<String>,
        insertionsAllowed: Bool
    ) -> [Int] {
        let lastApp = current.lastIndex(where: appIDs.contains)
        let previousSet = Set(previous ?? [])
        let lastShared = insertionsAllowed && !previousSet.isEmpty
            ? current.lastIndex(where: previousSet.contains) : nil
        var seen = Set<String>()
        var found: [Int] = []
        for (i, id) in current.enumerated() where !appIDs.contains(id) && !ignoring.contains(id) {
            let wedged = lastApp.map { i < $0 } ?? false
            let inserted = lastShared.map { i < $0 && !previousSet.contains(id) } ?? false
            if (wedged || inserted), seen.insert(id).inserted { found.append(i) }
        }
        return found
    }

    /// How many upcoming tracks GET /me/player/queue returns at most.
    nonisolated static let spotifyQueueWindow = 20

    /// Spotify plays queued tracks in order, so arriving at sent[i] means
    /// everything before it has already played or been skipped elsewhere.
    nonisolated static func arrival(of trackID: String, in sent: [QueueItem]) -> (remaining: [QueueItem], arrived: QueueItem?) {
        guard let i = sent.firstIndex(where: { $0.trackID == trackID }) else { return (sent, nil) }
        return (Array(sent[(i + 1)...]), sent[i])
    }

    /// `sent` minus whatever Spotify has already played, given the ids in its
    /// queue view. Played tracks are a *prefix* of `sent` (Spotify plays the user
    /// queue first-in, first-out), so drop everything before the first one still
    /// visible, then match the rest in order so a track queued twice pairs with
    /// the right copy.
    ///
    /// The view is capped at `spotifyQueueWindow` and is nearly always full (the
    /// playing context pads it), so a trailing unmatched track may simply be past
    /// the window: keep those when the view is full (review S2). Ceiling: if 20+
    /// non-app tracks sit ahead of ours (a very busy Jam), nothing of ours is
    /// visible and everything is treated as played.
    nonisolated static func reconciled(_ sent: [QueueItem], against queue: [String]) -> [QueueItem] {
        guard let start = sent.firstIndex(where: { queue.contains($0.trackID) }) else { return [] }
        var remaining = queue[...]
        var kept: [QueueItem] = []
        for (offset, item) in sent[start...].enumerated() {
            if let i = remaining.firstIndex(of: item.trackID) {
                kept.append(item)
                remaining = remaining[(i + 1)...]
            } else if queue.count >= spotifyQueueWindow {
                // Possibly just past the visible window, and so is everything
                // after it. A track that truly vanished isn't stuck: once nothing
                // before it is visible it becomes a prefix and is dropped.
                kept.append(contentsOf: sent[(start + offset)...])
                break
            }
        }
        return kept
    }

    /// Top up to the background depth before iOS suspends the app.
    func prepareForBackground() async {
        backgroundTask = UIApplication.shared.beginBackgroundTask(withName: "queue-top-up") { [weak self] in
            // The expiration handler runs on the main thread and must end the task synchronously.
            MainActor.assumeIsolated { self?.endBackgroundTask() }
        }
        await topUp(to: Config.backgroundBufferDepth)
        endBackgroundTask()
    }

    private func endBackgroundTask() {
        guard backgroundTask != .invalid else { return }
        UIApplication.shared.endBackgroundTask(backgroundTask)
        backgroundTask = .invalid
    }

    /// Send tracks from Up Next until `depth` non-skipped tracks are ahead in Spotify.
    private func topUp(to depth: Int) async {
        guard isPrimary, !isToppingUp else { return }
        isToppingUp = true
        defer { isToppingUp = false }

        while sent.filter({ !$0.skipOnArrival }).count < depth, let next = upcoming.first {
            do {
                let result: QueueResult = try await client.post("spotify/queue/", body: QueueRequest(trackIDs: [next.trackID]))
                guard result.queued == 1 else {
                    message = NowPlayingModel.describe(result.error ?? "")
                    return
                }
            } catch {
                message = (error as? APIClient.Error)?.errorDescription ?? error.localizedDescription
                return
            }
            message = nil
            upcoming.removeFirst()
            sent.append(next)
        }
    }

    // MARK: - Persistence

    private struct Snapshot: Codable {
        let sent: [QueueItem]
        let upcoming: [QueueItem]
        // Optional so pre-DJ5 queue files still decode.
        var requests: [GuestRequest]?
        var guestSkips: [String]?
        var keptGuests: [String]?
    }

    private static var fileURL: URL {
        URL.applicationSupportDirectory.appending(path: "queue.json")
    }

    private func load() {
        guard let data = try? Data(contentsOf: Self.fileURL),
              let snapshot = try? JSONDecoder().decode(Snapshot.self, from: data) else { return }
        sent = snapshot.sent
        upcoming = snapshot.upcoming
        requests = snapshot.requests ?? []
        guestSkips = snapshot.guestSkips ?? []
        keptGuests = Set(snapshot.keptGuests ?? [])
    }

    /// The synced fields, for DJSync.
    var syncQueue: SyncDoc.Queue {
        SyncDoc.Queue(sent: sent, upcoming: upcoming, requests: requests,
                      guestSkips: guestSkips, keptGuests: keptGuests.sorted())
    }

    /// Adopt the shared queue from another device (DJSync).
    func apply(_ q: SyncDoc.Queue) {
        sent = q.sent
        upcoming = q.upcoming
        requests = q.requests
        guestSkips = q.guestSkips
        keptGuests = Set(q.keptGuests)
        // A participant's add only reaches Spotify through the primary.
        Task { await topUp(to: Self.foregroundDepth) }
    }

    /// Became primary mid-session: resume driving from the shared queue.
    func startDriving() async {
        lastTrackID = nil
        lastQueueView = nil
        await topUp(to: Self.foregroundDepth)
    }

    private func save() {
        onChange?()
        do {
            try FileManager.default.createDirectory(at: .applicationSupportDirectory, withIntermediateDirectories: true)
            let snapshot = Snapshot(sent: sent, upcoming: upcoming, requests: requests,
                                    guestSkips: guestSkips, keptGuests: Array(keptGuests))
            try JSONEncoder().encode(snapshot).write(to: Self.fileURL, options: .atomic)
        } catch {
            message = "Couldn't save the queue: \(error.localizedDescription)"
        }
    }
}

private struct QueueRequest: Encodable {
    let trackIDs: [String]
    enum CodingKeys: String, CodingKey { case trackIDs = "track_ids" }
}

private struct QueueResult: Decodable {
    let queued: Int
    let error: String?
}

/// Decodes GET /player/queue/.
private struct SpotifyQueue: Decodable {
    let queue: [Track]
}
