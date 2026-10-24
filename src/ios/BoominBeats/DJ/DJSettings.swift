import Foundation

struct AvoidedTrack: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let artist: String
}

/// Optional steering (DJ6). Not a precomputed path: every suggestion round asks
/// for the next step from what actually played, so the night can wander.
struct DJGoal: Codable, Equatable {
    enum Kind: String, Codable { case destination, arc, drift }
    enum Shape: String, Codable, CaseIterable, Identifiable {
        case build, windDown = "wind_down", peakCool = "peak_cool"
        var id: String { rawValue }
        var label: String {
            switch self {
            case .build: return "Build to peak"
            case .windDown: return "Wind down"
            case .peakCool: return "Peak then cool"
            }
        }
    }

    var kind: Kind
    var destination = ""
    var shape: Shape = .build
    var minutes = 30
    /// When an arc started; its position is worked out at request time.
    var startedAt = Date()

    static let arcLengths = [15, 30, 60]

    var elapsedMinutes: Double { Date().timeIntervalSince(startedAt) / 60 }

    var label: String {
        switch kind {
        case .destination: return "Toward \(destination)"
        case .arc: return "\(shape.label) · \(minutes) min"
        case .drift: return "Drift"
        }
    }
}

/// The host's DJ controls (DJ4), persisted on device. The backend is stateless,
/// so all of this travels with each /dj/suggest/ request.
@MainActor
@Observable
final class DJSettings {
    enum Mode: String, CaseIterable, Identifiable {
        case whisper, copilot, autofill, driver
        var id: String { rawValue }

        var label: String {
            switch self {
            case .whisper: return "Whisper"
            case .copilot: return "Co-pilot"
            case .autofill: return "Autofill"
            case .driver: return "Driver"
            }
        }

        var summary: String {
            switch self {
            case .whisper: return "Suggests only when you ask."
            case .copilot: return "Always has moves ready; you pick."
            case .autofill: return "Adds a pick when the queue runs dry. Swipe it away to veto."
            case .driver: return "Keeps 3 songs lined up, choosing the moves itself. Set a goal to steer it."
            }
        }

        /// How many tracks the DJ keeps lined up after the current one.
        var autopilotTarget: Int {
            switch self {
            case .whisper, .copilot: return 0
            case .autofill: return 1
            case .driver: return 3
            }
        }
    }

    var mode: Mode { didSet { defaults.set(mode.rawValue, forKey: Keys.mode) } }
    /// 0 = safe, 1 = bold.
    var adventurousness: Double { didSet { defaults.set(adventurousness, forKey: Keys.adventurousness) } }
    var cleanOnly: Bool { didSet { defaults.set(cleanOnly, forKey: Keys.clean) } }
    private(set) var avoidTracks: [AvoidedTrack] { didSet { saveList(avoidTracks, Keys.avoidTracks) } }
    private(set) var avoidArtists: [String] { didSet { saveList(avoidArtists, Keys.avoidArtists) } }
    var goal: DJGoal? { didSet { defaults.set(goal.flatMap { try? JSONEncoder().encode($0) }, forKey: Keys.goal) } }

    private let defaults = UserDefaults.standard

    private enum Keys {
        static let mode = "dj_mode"
        static let adventurousness = "dj_adventurousness"
        static let clean = "dj_clean_only"
        static let avoidTracks = "dj_avoid_tracks"
        static let avoidArtists = "dj_avoid_artists"
        static let goal = "dj_goal"
    }

    init() {
        mode = defaults.string(forKey: Keys.mode).flatMap(Mode.init) ?? .copilot
        adventurousness = defaults.object(forKey: Keys.adventurousness) as? Double ?? 0.5
        cleanOnly = defaults.bool(forKey: Keys.clean)
        avoidTracks = Self.loadList(Keys.avoidTracks) ?? []
        avoidArtists = Self.loadList(Keys.avoidArtists) ?? []
        goal = UserDefaults.standard.data(forKey: Keys.goal).flatMap { try? JSONDecoder().decode(DJGoal.self, from: $0) }
    }

    func avoid(_ track: AvoidedTrack) {
        guard !avoidTracks.contains(where: { $0.id == track.id }) else { return }
        avoidTracks.append(track)
    }

    func avoid(artist: String) {
        guard !avoidArtists.contains(where: { $0.caseInsensitiveCompare(artist) == .orderedSame }) else { return }
        avoidArtists.append(artist)
    }

    func removeTracks(at offsets: IndexSet) { avoidTracks.remove(atOffsets: offsets) }
    func removeArtists(at offsets: IndexSet) { avoidArtists.remove(atOffsets: offsets) }

    private func saveList<T: Encodable>(_ list: [T], _ key: String) {
        defaults.set(try? JSONEncoder().encode(list), forKey: key)
    }

    private static func loadList<T: Decodable>(_ key: String) -> [T]? {
        UserDefaults.standard.data(forKey: key).flatMap { try? JSONDecoder().decode([T].self, from: $0) }
    }
}
