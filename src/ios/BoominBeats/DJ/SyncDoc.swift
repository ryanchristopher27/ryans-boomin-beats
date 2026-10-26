import Foundation

/// The shared DJ document (SY3), as stored by `PUT /dj/state`
/// (src/web/backend/routers/dj_state.py). Field names match the server's strict
/// schema exactly; it rejects unknown fields, so keep the two in step.
struct SyncDoc: Codable, Equatable {
    struct Queue: Codable, Equatable {
        var sent: [QueueItem] = []
        var upcoming: [QueueItem] = []
        var requests: [GuestRequest] = []
        var guestSkips: [String] = []
        var keptGuests: [String] = []
    }

    struct Options: Codable, Equatable {
        var mode: String = DJSettings.Mode.copilot.rawValue
        var adventurousness: Double = 0.5
        var clean = false
        var goal: DJGoal?
        var avoidTracks: [AvoidedTrack] = []
        var avoidArtists: [String] = []
    }

    struct Feedback: Codable, Equatable {
        var liked: [TrackRef] = []
        var disliked: [TrackRef] = []
        var skipped: [TrackRef] = []
    }

    /// Just what suggestions need about a track; the server's `TrackRef`.
    struct TrackRef: Codable, Equatable {
        let id: String
        let title: String
        let artists: [String]
        let image: String
        var isrc: String?

        init(_ track: Track) {
            id = track.id; title = track.title; artists = track.artists; image = track.image; isrc = track.isrc
        }

        var track: Track {
            Track(id: id, title: title, artists: artists, image: image, album: "",
                  durationMs: 0, explicit: false, trackURL: "", releaseDate: nil, isrc: isrc)
        }
    }

    var queue = Queue()
    var options = Options()
    var feedback = Feedback()
    var recent: [TrackRef] = []

    // The server stores dates as ISO 8601 strings (Goal.startedAt).
    static let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    static let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()

    var isEmpty: Bool { queue == Queue() && feedback == Feedback() && recent.isEmpty }

    /// Three-way merge after a 409: start from the server's document and keep
    /// every field this device changed since `base` (the last version both
    /// agreed on). Field-level, so a phone reordering Up Next and the web
    /// changing the goal both survive. If both changed the same field, this
    /// device's write wins (it's the one retrying).
    nonisolated static func merge(base: SyncDoc, local: SyncDoc, server: SyncDoc) -> SyncDoc {
        var out = server
        func take<T: Equatable>(_ path: WritableKeyPath<SyncDoc, T>) {
            if local[keyPath: path] != base[keyPath: path] { out[keyPath: path] = local[keyPath: path] }
        }
        take(\.queue.sent)
        take(\.queue.upcoming)
        take(\.queue.requests)
        take(\.queue.guestSkips)
        take(\.queue.keptGuests)
        take(\.options.mode)
        take(\.options.adventurousness)
        take(\.options.clean)
        take(\.options.goal)
        take(\.options.avoidTracks)
        take(\.options.avoidArtists)
        take(\.feedback.liked)
        take(\.feedback.disliked)
        take(\.feedback.skipped)
        take(\.recent)
        return out
    }
}

/// `GET /dj/state` and `PUT /dj/state` responses (200 and 409 alike).
struct SyncEnvelope: Decodable {
    let version: Int
    let state: SyncDoc?
    let primary: PrimaryInfo?
}

/// Who's driving, from the server. Also carried by `/player/state/`'s `dj` field.
struct PrimaryInfo: Decodable, Equatable {
    let device: String
    let label: String
    let online: Bool
}

/// The `dj` field `/player/state/` adds when the request names a device.
struct DJStatus: Decodable {
    let version: Int
    let primary: PrimaryInfo?
}
