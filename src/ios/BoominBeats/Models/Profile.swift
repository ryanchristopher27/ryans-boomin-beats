import Foundation

/// Decodes GET /get-profile/ (routers/profile.py).
///
/// Note `popularity` is absent by design: Spotify's February 2026 migration removed
/// it from every response, so the backend always returns 0 (see the migration audit
/// in docs/plan.md). Nothing here should surface it.
struct ProfileResponse: Decodable {
    let profile: SpotifyUser
    let topArtists: [Artist]
    let topTracks: [Track]

    enum CodingKeys: String, CodingKey {
        case profile
        case topArtists = "top_artists"
        case topTracks = "top_tracks"
    }
}

struct SpotifyUser: Decodable {
    let id: String
    let displayName: String?
    let images: [SpotifyImage]?

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case images
    }

    var avatarURL: URL? {
        images?.first.flatMap { URL(string: $0.url) }
    }
}

struct SpotifyImage: Decodable {
    let url: String
    let height: Int?
    let width: Int?
}

struct Artist: Decodable, Identifiable {
    let id: String
    let name: String
    let genres: [String]
    let images: [SpotifyImage]
    let url: String

    var imageURL: URL? {
        // Backend sends Spotify's array unmodified: largest first.
        images.last.flatMap { URL(string: $0.url) }
    }
}

struct Track: Decodable, Identifiable {
    let id: String
    let title: String
    let artists: [String]
    let image: String
    let album: String
    let durationMs: Int
    let explicit: Bool
    let trackURL: String
    let releaseDate: String?

    enum CodingKeys: String, CodingKey {
        case id, title, artists, image, album, explicit
        case durationMs = "duration_ms"
        case trackURL = "track_url"
        case releaseDate = "release_date"
    }

    var imageURL: URL? { URL(string: image) }
    var artistLine: String { artists.joined(separator: ", ") }

    var duration: String {
        let total = durationMs / 1000
        return String(format: "%d:%02d", total / 60, total % 60)
    }
}

/// The three windows Spotify exposes, matching the web app's controls.
enum TimeRange: String, CaseIterable, Identifiable {
    case shortTerm = "short_term"
    case mediumTerm = "medium_term"
    case longTerm = "long_term"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .shortTerm: "1 Month"
        case .mediumTerm: "6 Months"
        case .longTerm: "All Time"
        }
    }
}
