import Foundation

struct AvoidedTrack: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let artist: String
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
            // Goal-setting (destination / energy arc) arrives with DJ6.
            case .driver: return "Keeps 3 songs lined up, choosing the moves itself."
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

    private let defaults = UserDefaults.standard

    private enum Keys {
        static let mode = "dj_mode"
        static let adventurousness = "dj_adventurousness"
        static let clean = "dj_clean_only"
        static let avoidTracks = "dj_avoid_tracks"
        static let avoidArtists = "dj_avoid_artists"
    }

    init() {
        mode = defaults.string(forKey: Keys.mode).flatMap(Mode.init) ?? .copilot
        adventurousness = defaults.object(forKey: Keys.adventurousness) as? Double ?? 0.5
        cleanOnly = defaults.bool(forKey: Keys.clean)
        avoidTracks = Self.loadList(Keys.avoidTracks) ?? []
        avoidArtists = Self.loadList(Keys.avoidArtists) ?? []
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
