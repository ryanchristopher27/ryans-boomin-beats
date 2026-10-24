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
    private(set) var message: String?
    /// Track ids the app skipped itself (skip-on-arrival), so they aren't
    /// mistaken for the host skipping them.
    private(set) var autoSkipped: Set<String> = []

    /// Tracks lined up after the current one.
    var aheadCount: Int { sent.filter { !$0.skipOnArrival }.count + upcoming.count }

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

    /// Called after every player-state poll. Acts only when the track changes.
    func observe(_ state: PlaybackState) async {
        guard let trackID = state.track?.id, trackID != lastTrackID else { return }
        lastTrackID = trackID

        // Spotify plays queued tracks in order, so arriving at sent[i] means
        // everything before it has already played or been skipped elsewhere.
        if let i = sent.firstIndex(where: { $0.trackID == trackID }) {
            let arrived = sent[i]
            sent.removeFirst(i + 1)
            if arrived.skipOnArrival {
                autoSkipped.insert(arrived.trackID)
                _ = try? await client.post("player/next/", body: NoBody()) as CommandResult
            }
        }
        await topUp(to: Self.foregroundDepth)
    }

    /// On return to the foreground: drop sent tracks that played while the app
    /// was suspended, using Spotify's real queue as the source of truth.
    func reconcile(with state: PlaybackState) async {
        lastTrackID = nil
        await observe(state)

        guard let response: SpotifyQueue = try? await client.get("player/queue/") else { return }
        // Match in order, so a track queued twice is matched against the right copy.
        var remaining = response.queue.map(\.id)[...]
        sent = sent.filter { item in
            guard let i = remaining.firstIndex(of: item.trackID) else { return false }
            remaining = remaining[(i + 1)...]
            return true
        }
        await topUp(to: Self.foregroundDepth)
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
        guard !isToppingUp else { return }
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
    }

    private static var fileURL: URL {
        URL.applicationSupportDirectory.appending(path: "queue.json")
    }

    private func load() {
        guard let data = try? Data(contentsOf: Self.fileURL),
              let snapshot = try? JSONDecoder().decode(Snapshot.self, from: data) else { return }
        sent = snapshot.sent
        upcoming = snapshot.upcoming
    }

    private func save() {
        do {
            try FileManager.default.createDirectory(at: .applicationSupportDirectory, withIntermediateDirectories: true)
            try JSONEncoder().encode(Snapshot(sent: sent, upcoming: upcoming)).write(to: Self.fileURL, options: .atomic)
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
