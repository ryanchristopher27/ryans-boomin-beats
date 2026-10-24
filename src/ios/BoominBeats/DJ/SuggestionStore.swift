import Foundation

/// Decodes POST /dj/suggest/ (routers/dj.py).
struct MoveSuggestions: Decodable {
    struct Move: Decodable, Identifiable {
        let move: String
        let tracks: [Pick]
        var id: String { move }

        var label: String { move.capitalized }

        var summary: String {
            switch move {
            case "hold": return "Keep the vibe"
            case "lift": return "Raise the energy"
            case "drop": return "Give the room a breather"
            case "pivot": return "Change genre, keep a thread"
            case "curveball": return "Something unexpected"
            case "toward": return "Next step toward your goal"
            case "drift": return "Somewhere new"
            default: return ""
            }
        }

        var symbol: String {
            switch move {
            case "hold": return "equal.circle"
            case "lift": return "arrow.up.circle"
            case "drop": return "arrow.down.circle"
            case "pivot": return "arrow.triangle.turn.up.right.circle"
            case "curveball": return "sparkles"
            case "toward": return "location.north.circle"
            case "drift": return "wind"
            default: return "music.note"
            }
        }
    }

    struct Pick: Decodable, Identifiable {
        let id: String
        let title: String
        let artists: [String]
        let image: String
        let reason: String

        var artistLine: String { artists.joined(separator: ", ") }
        var imageURL: URL? { URL(string: image) }

        var queueItem: QueueItem {
            QueueItem(trackID: id, title: title, artists: artists, image: image)
        }
    }

    let moves: [Move]
    let error: String?
}

private struct TrackRef: Encodable {
    let id: String
    let title: String
    let artist: String

    init(_ track: Track) {
        id = track.id; title = track.title; artist = track.artists.first ?? ""
    }
    init(_ item: QueueItem) {
        id = item.trackID; title = item.title; artist = item.artists.first ?? ""
    }
    init(_ avoided: AvoidedTrack) {
        id = avoided.id; title = avoided.title; artist = avoided.artist
    }
}

private struct SuggestRequest: Encodable {
    let nowPlaying: TrackRef
    let recent: [TrackRef]
    let upcoming: [TrackRef]
    let adventurousness: Double
    let clean: Bool
    let liked: [TrackRef]
    let disliked: [TrackRef]
    let skipped: [TrackRef]
    let avoidTracks: [TrackRef]
    let avoidArtists: [String]
    let goal: GoalPayload?

    struct GoalPayload: Encodable {
        let kind: String
        let destination: String
        let shape: String
        let minutes: Int
        let elapsedMinutes: Double

        init(_ goal: DJGoal) {
            kind = goal.kind.rawValue
            destination = goal.destination
            shape = goal.shape.rawValue
            minutes = goal.minutes
            elapsedMinutes = goal.elapsedMinutes
        }

        enum CodingKeys: String, CodingKey {
            case kind, destination, shape, minutes
            case elapsedMinutes = "elapsed_minutes"
        }
    }

    enum CodingKeys: String, CodingKey {
        case nowPlaying = "now_playing"
        case avoidTracks = "avoid_tracks"
        case avoidArtists = "avoid_artists"
        case recent, upcoming, adventurousness, clean, liked, disliked, skipped, goal
    }
}

/// Prefetches move suggestions on every track change (DJ3), so they're ready
/// before the host opens them. A call takes ~6s (DJ3 result), well inside a
/// 3–4 minute track. Results are cached per track id.
@MainActor
@Observable
final class SuggestionStore {
    enum State {
        case idle
        case needsKey
        case loading
        case loaded([MoveSuggestions.Move])
        case failed(String)
    }

    private(set) var state: State = .idle
    private var cache: [String: [MoveSuggestions.Move]] = [:]
    private var inFlight: String?
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    var isLoading: Bool { if case .loading = state { return true }; return false }

    /// Whisper mode: nothing is fetched until the host asks.
    func reset() { state = .idle }

    func load(
        for track: Track,
        session: NowPlayingModel,
        queue: QueueStore,
        settings: DJSettings,
        force: Bool = false
    ) async {
        guard let key = Config.llmKey, !key.isEmpty else {
            state = .needsKey
            return
        }
        // Settings that change the answer are part of the cache key.
        let cacheKey = "\(track.id)|\(Int(settings.adventurousness * 3))|\(settings.cleanOnly)|\(Self.goalKey(settings.goal))"
        if !force, let cached = cache[cacheKey] {
            state = .loaded(cached)
            await autopilot(queue: queue, settings: settings)
            return
        }
        // Repeated taps must not stack requests for the same answer: Groq's
        // on-demand tier allows ~8k tokens/min and one call costs ~3k (DJ4
        // result). Keyed, not a global flag, so a track change can still start
        // its own load while a cancelled one unwinds.
        guard inFlight != cacheKey else { return }
        inFlight = cacheKey
        defer { if inFlight == cacheKey { inFlight = nil } }

        state = .loading
        let body = SuggestRequest(
            nowPlaying: TrackRef(track),
            recent: session.recent.map(TrackRef.init),
            upcoming: (queue.sent + queue.upcoming).map(TrackRef.init),
            adventurousness: settings.adventurousness,
            clean: settings.cleanOnly,
            liked: session.liked.map(TrackRef.init),
            disliked: session.disliked.map(TrackRef.init),
            skipped: session.skipped.map(TrackRef.init),
            avoidTracks: settings.avoidTracks.map(TrackRef.init),
            avoidArtists: settings.avoidArtists,
            goal: settings.goal.map { SuggestRequest.GoalPayload($0) }
        )
        do {
            let response: MoveSuggestions = try await client.post("dj/suggest/", body: body)
            // A newer track change may have started its own load meanwhile.
            guard !Task.isCancelled, inFlight == cacheKey else { return }
            if response.moves.isEmpty {
                state = .failed(response.error ?? "No suggestions this time.")
            } else {
                // Only the current track's set is ever shown; a small cache covers
                // flipping back after a quick skip without growing unbounded.
                if cache.count > 20 { cache.removeAll() }
                cache[cacheKey] = response.moves
                state = .loaded(response.moves)
                await autopilot(queue: queue, settings: settings)
            }
        } catch {
            guard !Task.isCancelled else { return }
            state = .failed((error as? APIClient.Error)?.errorDescription ?? error.localizedDescription)
        }
    }

    /// Part of the cache key for a goal. An arc's instruction changes as it
    /// progresses, so its key moves on every 5 minutes.
    nonisolated static func goalKey(_ goal: DJGoal?) -> String {
        guard let goal else { return "none" }
        switch goal.kind {
        case .destination: return "dest:\(goal.destination)"
        case .arc: return "arc:\(goal.shape.rawValue):\(goal.minutes):\(Int(goal.elapsedMinutes / 5))"
        case .drift: return "drift"
        }
    }

    /// Picks in the order autopilot should take them: with a goal, every pick
    /// from the goal's move (`lead`) first; then the other moves ranked by
    /// adventurousness (safe → hold/lift/drop, bold → pivot/curveball first),
    /// interleaved one per move per round. Anything already queued is skipped.
    nonisolated static func autopilotCandidates(
        moves: [MoveSuggestions.Move],
        adventurousness a: Double,
        excluding queued: Set<String>,
        lead: String? = nil
    ) -> [MoveSuggestions.Pick] {
        let order = a < 0.34 ? ["hold", "lift", "drop"]
            : a < 0.67 ? ["hold", "lift", "pivot", "drop", "curveball"]
            : ["pivot", "curveball", "lift", "hold"]
        let lists = order.compactMap { name in moves.first { $0.move == name }?.tracks }
        var candidates = (lead.flatMap { name in moves.first { $0.move == name }?.tracks } ?? [])
            .filter { !queued.contains($0.id) }
        for i in 0..<(lists.map(\.count).max() ?? 0) {
            for list in lists where i < list.count && !queued.contains(list[i].id) {
                candidates.append(list[i])
            }
        }
        return candidates
    }

    /// Autofill and Driver (DJ4): keep `mode.autopilotTarget` tracks lined up,
    /// drawing from the current moves. Adventurousness picks which moves lead;
    /// picks are interleaved across moves so Driver's three aren't all one move.
    /// Driver's goal-setting (destination / arc) arrives with DJ6.
    func autopilot(queue: QueueStore, settings: DJSettings) async {
        let target = settings.mode.autopilotTarget
        guard target > 0, queue.aheadCount < target, case let .loaded(moves) = state else { return }

        var candidates = Self.autopilotCandidates(
            moves: moves,
            adventurousness: settings.adventurousness,
            excluding: Set((queue.sent + queue.upcoming).map(\.trackID)),
            lead: settings.goal.map { $0.kind == .drift ? "drift" : "toward" }
        )
        while queue.aheadCount < target, !candidates.isEmpty {
            var item = candidates.removeFirst().queueItem
            item.addedByDJ = true
            await queue.add(item)
        }
    }
}
