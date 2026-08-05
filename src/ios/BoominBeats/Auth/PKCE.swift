import CryptoKit
import Foundation

/// PKCE verifier/challenge generation.
///
/// Mirrors the web app's `spotifyAuth.js`, but the browser's `crypto.subtle` +
/// `btoa` become CryptoKit + a base64url encoding. Spotify requires S256.
enum PKCE {
    /// RFC 7636 allows 43–128 chars from the unreserved set.
    static func makeVerifier(length: Int = 64) -> String {
        let allowed = Array("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        var bytes = [UInt8](repeating: 0, count: length)
        _ = SecRandomCopyBytes(kSecRandomDefault, length, &bytes)
        return String(bytes.map { allowed[Int($0) % allowed.count] })
    }

    static func challenge(for verifier: String) -> String {
        let digest = SHA256.hash(data: Data(verifier.utf8))
        return Data(digest).base64URLEncodedString()
    }
}

extension Data {
    /// base64url without padding — what the OAuth spec expects.
    func base64URLEncodedString() -> String {
        base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}
