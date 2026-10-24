import Foundation

/// Runtime configuration. The API host is overridable at runtime so one build can
/// point at the Mac during development or the hosted instance later (D1.3) — the
/// "configurable base URL" option from the 2026-08-03 plan.
enum Config {
    /// Spotify client ID. Deliberately the SAME id the web app uses: grandfathered
    /// endpoint access follows the client ID, and registering a new app would
    /// forfeit it (see the V1 result in docs/plan.md).
    static let spotifyClientID = "a700071d47504ba68082a5a59d2b0bc0"

    static let redirectURI = "boominbeats://callback"
    static let callbackScheme = "boominbeats"

    static let scopes = [
        "user-top-read",
        "playlist-read-private",
        "playlist-modify-private",
        "playlist-modify-public",
        "user-modify-playback-state",
        "user-read-playback-state",
        "user-library-read",
        "user-library-modify",
        "user-read-recently-played",
    ].joined(separator: " ")

    static let authorizeEndpoint = URL(string: "https://accounts.spotify.com/authorize")!
    static let tokenEndpoint = URL(string: "https://accounts.spotify.com/api/token")!

    // MARK: - Backend

    private static let apiBaseKey = "api_base_url"

    /// Defaults to the Mac's LAN address during development. Override in Settings.
    static var apiBaseURL: URL {
        get {
            if let s = UserDefaults.standard.string(forKey: apiBaseKey), let u = URL(string: s) {
                return u
            }
            return URL(string: "http://127.0.0.1:8005")!
        }
        set { UserDefaults.standard.set(newValue.absoluteString, forKey: apiBaseKey) }
    }

    /// Shared secret for the hosted instance (D1.1). Empty for the local instance,
    /// where the guard is a no-op. Stored in the Keychain, not UserDefaults.
    static var deviceKey: String? {
        get { try? Keychain.read(.deviceKey) }
        set {
            if let newValue, !newValue.isEmpty {
                try? Keychain.write(newValue, for: .deviceKey)
            } else {
                try? Keychain.delete(.deviceKey)
            }
        }
    }

    // MARK: - LLM (BYOK)

    /// Matches services/llm_auth.py SUPPORTED_PROVIDERS.
    static let llmProviders = ["groq", "claude", "openai"]

    static var llmProvider: String {
        get { (try? Keychain.read(.llmProvider)) ?? "groq" }
        set { try? Keychain.write(newValue, for: .llmProvider) }
    }

    /// The user's own provider key, sent per request as X-LLM-Key. Keychain only.
    static var llmKey: String? {
        get { try? Keychain.read(.llmKey) }
        set {
            if let newValue, !newValue.isEmpty {
                try? Keychain.write(newValue, for: .llmKey)
            } else {
                try? Keychain.delete(.llmKey)
            }
        }
    }

    // MARK: - DJ

    private static let bufferDepthKey = "background_buffer_depth"
    static let bufferDepthRange = 1...10

    /// How many tracks the queue hands to Spotify when the app goes to the
    /// background (DJ2's adaptive buffer). The foreground depth is fixed at 1.
    static var backgroundBufferDepth: Int {
        get {
            let v = UserDefaults.standard.integer(forKey: bufferDepthKey)
            return bufferDepthRange.contains(v) ? v : 5
        }
        set { UserDefaults.standard.set(newValue, forKey: bufferDepthKey) }
    }
}
