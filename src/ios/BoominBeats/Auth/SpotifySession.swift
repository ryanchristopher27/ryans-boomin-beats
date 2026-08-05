import AuthenticationServices
import Foundation
import Observation

/// Owns the Spotify token lifecycle: PKCE login, refresh, Keychain persistence.
///
/// The web app's redirect target is `http://127.0.0.1:5173/profile`, which iOS
/// cannot receive — this uses `boominbeats://callback` via ASWebAuthenticationSession
/// against the SAME client ID.
@MainActor
@Observable
final class SpotifySession {
    enum State: Equatable {
        case loggedOut
        case authenticating
        case loggedIn
        case failed(String)
    }

    private(set) var state: State = .loggedOut
    private(set) var accessToken: String?

    private var refreshToken: String?
    private var expiresAt: Date?
    private var contextProvider = PresentationContextProvider()

    var isLoggedIn: Bool { if case .loggedIn = state { return true }; return false }

    // MARK: - Restore

    /// Rehydrate from the Keychain on launch, refreshing if the token has expired.
    func restore() async {
        guard let token = try? Keychain.read(.accessToken) else { return }
        accessToken = token
        refreshToken = try? Keychain.read(.refreshToken)
        if let raw = try? Keychain.read(.expiresAt), let secs = TimeInterval(raw ?? "") {
            expiresAt = Date(timeIntervalSince1970: secs)
        }

        if let expiresAt, expiresAt > Date().addingTimeInterval(60) {
            state = .loggedIn
            return
        }
        await refresh()
    }

    // MARK: - Login

    func logIn() async {
        state = .authenticating
        let verifier = PKCE.makeVerifier()
        let challenge = PKCE.challenge(for: verifier)

        var components = URLComponents(url: Config.authorizeEndpoint, resolvingAgainstBaseURL: false)!
        components.queryItems = [
            .init(name: "client_id", value: Config.spotifyClientID),
            .init(name: "response_type", value: "code"),
            .init(name: "redirect_uri", value: Config.redirectURI),
            .init(name: "scope", value: Config.scopes),
            .init(name: "code_challenge_method", value: "S256"),
            .init(name: "code_challenge", value: challenge),
            // No show_dialog: through ASWebAuthenticationSession it forces an extra
            // system prompt on every login for no benefit.
        ]

        do {
            let callback = try await authenticate(url: components.url!)
            guard let code = URLComponents(url: callback, resolvingAgainstBaseURL: false)?
                .queryItems?.first(where: { $0.name == "code" })?.value
            else {
                state = .failed("Spotify did not return an authorization code.")
                return
            }
            try await exchange(code: code, verifier: verifier)
            state = .loggedIn
        } catch let error as ASWebAuthenticationSessionError where error.code == .canceledLogin {
            state = .loggedOut
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    private func authenticate(url: URL) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(
                url: url,
                callbackURLScheme: Config.callbackScheme
            ) { callbackURL, error in
                if let error { continuation.resume(throwing: error) }
                else if let callbackURL { continuation.resume(returning: callbackURL) }
                else { continuation.resume(throwing: URLError(.badServerResponse)) }
            }
            session.presentationContextProvider = contextProvider
            session.prefersEphemeralWebBrowserSession = false
            session.start()
        }
    }

    // MARK: - Token exchange / refresh

    private struct TokenResponse: Decodable {
        let access_token: String
        let refresh_token: String?
        let expires_in: Double
    }

    private func exchange(code: String, verifier: String) async throws {
        try await postToken([
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": Config.redirectURI,
            "client_id": Config.spotifyClientID,
            "code_verifier": verifier,
        ])
    }

    func refresh() async {
        guard let refreshToken else {
            state = .loggedOut
            return
        }
        do {
            try await postToken([
                "grant_type": "refresh_token",
                "refresh_token": refreshToken,
                "client_id": Config.spotifyClientID,
            ])
            state = .loggedIn
        } catch {
            // A failed refresh means the grant is gone — force a fresh login.
            logOut()
        }
    }

    private func postToken(_ fields: [String: String]) async throws {
        var request = URLRequest(url: Config.tokenEndpoint)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = fields
            .map { "\($0.key)=\($0.value.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? $0.value)" }
            .joined(separator: "&")
            .data(using: .utf8)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.userAuthenticationRequired)
        }
        let token = try JSONDecoder().decode(TokenResponse.self, from: data)

        accessToken = token.access_token
        try Keychain.write(token.access_token, for: .accessToken)
        if let refresh = token.refresh_token {
            refreshToken = refresh
            try Keychain.write(refresh, for: .refreshToken)
        }
        let expiry = Date().addingTimeInterval(token.expires_in)
        expiresAt = expiry
        try Keychain.write(String(expiry.timeIntervalSince1970), for: .expiresAt)
    }

    /// Returns a valid token, refreshing first if it is close to expiry.
    func validToken() async -> String? {
        if let expiresAt, expiresAt <= Date().addingTimeInterval(60) {
            await refresh()
        }
        return accessToken
    }

    // MARK: - Logout

    func logOut() {
        accessToken = nil
        refreshToken = nil
        expiresAt = nil
        try? Keychain.delete(.accessToken)
        try? Keychain.delete(.refreshToken)
        try? Keychain.delete(.expiresAt)
        state = .loggedOut
    }
}

/// ASWebAuthenticationSession needs a window to present from.
private final class PresentationContextProvider: NSObject, ASWebAuthenticationPresentationContextProviding {
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        ASPresentationAnchor()
    }
}
