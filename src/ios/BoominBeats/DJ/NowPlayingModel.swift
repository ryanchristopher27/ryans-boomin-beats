import Foundation

/// Decodes GET /player/state/ (routers/player.py). Everything but `active` is
/// absent when nothing is playing on any device.
struct PlaybackState: Decodable {
    struct Device: Decodable {
        let name: String
        let type: String
    }

    let active: Bool
    let isPlaying: Bool?
    let progressMs: Int?
    let device: Device?
    let track: Track?
    let disallows: [String]?
    let smartShuffle: Bool?
    /// Sync status (SY3); present when the request named this device.
    let dj: DJStatus?

    enum CodingKeys: String, CodingKey {
        case active, device, track, disallows, dj
        case isPlaying = "is_playing"
        case progressMs = "progress_ms"
        case smartShuffle = "smart_shuffle"
    }

    func allows(_ action: String) -> Bool { !(disallows ?? []).contains(action) }
}

/// Player commands answer 200 with either {"ok": true} or {"error": ...}.
struct CommandResult: Decodable {
    let ok: Bool?
    let error: String?
}

struct NoBody: Encodable {}

@MainActor
@Observable
final class NowPlayingModel {
    enum Command: String {
        case play, pause, next, previous
    }

    private(set) var state: PlaybackState?
    private(set) var message: String?
    /// Whether `message` came from a failed state poll rather than a command.
    /// A poll error is stale once a later poll succeeds; a command error isn't,
    /// and must survive the re-read that follows every command.
    private var messageFromPoll = false
    /// Tracks played this session, most recent first — context for suggestions.
    private(set) var recent: [Track] = []
    /// Session feedback for suggestions (DJ4), most recent first, capped at 5.
    private(set) var skipped: [Track] = []
    private(set) var liked: [Track] = []
    private(set) var disliked: [Track] = []
    /// When `state` was fetched; progress is interpolated from here between polls.
    private var fetchedAt = Date()
    private var lastRequestPoll = Date.distantPast
    /// Consecutive failed polls, for backoff (tracker 477d21).
    private var failures = 0

    private let client: APIClient
    private let queue: QueueStore
    /// Set by MainTabs once the sync engine exists.
    weak var sync: DJSync?
    /// Called after a change to synced feedback/recent, for DJSync to push.
    var onChange: (() -> Void)?

    init(client: APIClient, queue: QueueStore) {
        self.client = client
        self.queue = queue
    }

    var isPlaying: Bool { state?.isPlaying ?? false }

    /// Progress at `date`, advancing locally between polls while playing.
    func progressMs(at date: Date) -> Int {
        guard let state, let base = state.progressMs else { return 0 }
        let elapsed = isPlaying ? Int(date.timeIntervalSince(fetchedAt) * 1000) : 0
        return min(base + elapsed, state.track?.durationMs ?? .max)
    }

    /// Foreground poll loop; ends when the calling task is cancelled. Polls every
    /// ~2s, but wakes just after the current track should end so the change shows
    /// up promptly instead of up to a full interval late.
    func run() async {
        await refresh()
        // Each run starts on a return to the foreground: catch up with whatever
        // Spotify played from the buffer while the app was suspended.
        if let state { await queue.reconcile(with: state) }
        while !Task.isCancelled {
            try? await Task.sleep(for: .seconds(nextDelay()))
            await refresh()
        }
    }

    func refresh() async {
        do {
            let headers = sync.map { ["X-DJ-Device": $0.deviceID] } ?? [:]
            let s: PlaybackState = try await client.get("player/state/", headers: headers)
            // History and skips are recorded by the primary only; others get them via sync.
            if queue.isPrimary, let previous = state?.track, previous.id != s.track?.id {
                // Left before halfway = a skip, unless the queue skipped it itself.
                if progressMs(at: Date()) < previous.durationMs / 2, !queue.autoSkipped.contains(previous.id) {
                    Self.push(previous, onto: &skipped)
                }
                recent.removeAll { $0.id == previous.id }
                recent.insert(previous, at: 0)
                recent = Array(recent.prefix(10))
                onChange?()
            }
            state = s
            fetchedAt = Date()
            if messageFromPoll || (message == Self.noDevice && s.active) {
                message = nil
                messageFromPoll = false
            }
            await sync?.observe(s.dj)
            await queue.observe(s)
            // Guest requests (DJ5): Spotify's queue is a separate, slower read, so
            // poll it every ~10s rather than on every 2s state poll.
            if Date().timeIntervalSince(lastRequestPoll) >= 10 {
                lastRequestPoll = Date()
                await queue.pollRequests(smartShuffle: s.smartShuffle ?? false)
            }
            failures = 0
        } catch {
            message = (error as? APIClient.Error)?.errorDescription ?? error.localizedDescription
            messageFromPoll = true
            failures += 1
        }
    }

    func rate(_ track: Track, more: Bool) {
        liked.removeAll { $0.id == track.id }
        disliked.removeAll { $0.id == track.id }
        if more { Self.push(track, onto: &liked) } else { Self.push(track, onto: &disliked) }
        onChange?()
    }

    /// The synced feedback and history, for DJSync.
    var syncFeedback: SyncDoc.Feedback {
        SyncDoc.Feedback(liked: liked.map(SyncDoc.TrackRef.init), disliked: disliked.map(SyncDoc.TrackRef.init),
                         skipped: skipped.map(SyncDoc.TrackRef.init))
    }

    var syncRecent: [SyncDoc.TrackRef] { recent.map(SyncDoc.TrackRef.init) }

    /// Adopt feedback and history from another device (DJSync).
    func apply(feedback f: SyncDoc.Feedback, recent r: [SyncDoc.TrackRef]) {
        liked = f.liked.map(\.track)
        disliked = f.disliked.map(\.track)
        skipped = f.skipped.map(\.track)
        recent = r.map(\.track)
    }

    private static func push(_ track: Track, onto list: inout [Track]) {
        list.removeAll { $0.id == track.id }
        list.insert(track, at: 0)
        list = Array(list.prefix(5))
    }

    func send(_ command: Command) async {
        do {
            let result: CommandResult = try await client.post("player/\(command.rawValue)/", body: NoBody())
            message = result.error.map(Self.describe)
            messageFromPoll = false
        } catch {
            message = (error as? APIClient.Error)?.errorDescription ?? error.localizedDescription
            messageFromPoll = false
        }
        // Spotify's player state lags a command slightly; re-read after a beat.
        try? await Task.sleep(for: .milliseconds(400))
        await refresh()
    }

    /// Spotify rate-limits /me/player per app (tracker 477d21: every device polling
    /// every 2 s drew 1,157 429s in 38 minutes), and progress is interpolated
    /// locally, so poll every 5 s. The driver also wakes just after the track
    /// should end, so the next song is handled promptly. Failures back off
    /// 5, 10, 20, 40, 60 s.
    nonisolated static func pollDelay(active: Bool, playing: Bool, remaining: Double?, driving: Bool, failures: Int) -> Double {
        if failures > 0 { return min(60, 5 * pow(2, Double(failures - 1))) }
        guard active else { return 10 }
        guard playing, let remaining else { return 5 }
        if driving, remaining < 5.5 { return max(0.3, remaining + 0.3) }
        return 5
    }

    private func nextDelay() -> Double {
        let remaining = state?.track.map { Double($0.durationMs - progressMs(at: Date())) / 1000 }
        return Self.pollDelay(active: state?.active ?? false, playing: isPlaying, remaining: remaining,
                              driving: queue.isPrimary, failures: failures)
    }

    private static let noDevice = "Open Spotify on any device to start playback."

    static func describe(_ error: String) -> String {
        switch error {
        case "no_active_device": return noDevice
        case "premium_required": return "Playback control needs Spotify Premium."
        default: return "Spotify didn't allow that right now."
        }
    }
}
