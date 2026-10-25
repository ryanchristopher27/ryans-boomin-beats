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

    enum CodingKeys: String, CodingKey {
        case active, device, track, disallows
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

    private let client: APIClient
    private let queue: QueueStore

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
            let s: PlaybackState = try await client.get("player/state/")
            if let previous = state?.track, previous.id != s.track?.id {
                // Left before halfway = a skip, unless the queue skipped it itself.
                if progressMs(at: Date()) < previous.durationMs / 2, !queue.autoSkipped.contains(previous.id) {
                    Self.push(previous, onto: &skipped)
                }
                recent.removeAll { $0.id == previous.id }
                recent.insert(previous, at: 0)
                recent = Array(recent.prefix(10))
            }
            state = s
            fetchedAt = Date()
            if messageFromPoll || (message == Self.noDevice && s.active) {
                message = nil
                messageFromPoll = false
            }
            await queue.observe(s)
            // Guest requests (DJ5): Spotify's queue is a separate, slower read, so
            // poll it every ~10s rather than on every 2s state poll.
            if Date().timeIntervalSince(lastRequestPoll) >= 10 {
                lastRequestPoll = Date()
                await queue.pollRequests(smartShuffle: s.smartShuffle ?? false)
            }
        } catch {
            message = (error as? APIClient.Error)?.errorDescription ?? error.localizedDescription
            messageFromPoll = true
        }
    }

    func rate(_ track: Track, more: Bool) {
        liked.removeAll { $0.id == track.id }
        disliked.removeAll { $0.id == track.id }
        if more { Self.push(track, onto: &liked) } else { Self.push(track, onto: &disliked) }
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

    private func nextDelay() -> Double {
        guard let state, state.active else { return 5 }
        guard isPlaying, let duration = state.track?.durationMs else { return 2 }
        let remaining = Double(duration - progressMs(at: Date())) / 1000
        return min(2, max(0.3, remaining + 0.3))
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
