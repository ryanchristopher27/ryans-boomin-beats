import Foundation
import Security

/// Minimal Keychain wrapper for the few secrets this app holds.
///
/// The web app keeps its Spotify tokens in localStorage, which is readable by any
/// script on the page. On iOS there's no reason to accept that — Keychain items are
/// encrypted at rest and scoped to this app.
enum Keychain {
    enum Key: String, CaseIterable {
        case accessToken = "spotify_access_token"
        case refreshToken = "spotify_refresh_token"
        case expiresAt = "spotify_expires_at"
        case deviceKey = "device_key"
        case llmProvider = "llm_provider"
        case llmKey = "llm_key"
    }

    enum Error: Swift.Error, LocalizedError {
        case unexpectedStatus(OSStatus)
        case dataDecodingFailed

        /// Without this, the default description is "Keychain.Error error 0",
        /// which hides the OSStatus that actually says what went wrong.
        var errorDescription: String? {
            switch self {
            case let .unexpectedStatus(status):
                let message = SecCopyErrorMessageString(status, nil) as String?
                    ?? "unknown Keychain error"
                if status == errSecMissingEntitlement {
                    return "Keychain unavailable (\(status): \(message)). The build needs a "
                        + "keychain-access-groups entitlement — unsigned Simulator builds can't "
                        + "write to the Keychain."
                }
                return "Keychain error \(status): \(message)"
            case .dataDecodingFailed:
                return "Could not encode the value for the Keychain."
            }
        }
    }

    private static func query(_ key: Key) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: "com.ryanchristopher.boominbeats",
            kSecAttrAccount as String: key.rawValue,
        ]
    }

    static func write(_ value: String, for key: Key) throws {
        guard let data = value.data(using: .utf8) else { throw Error.dataDecodingFailed }
        var q = query(key)
        SecItemDelete(q as CFDictionary)
        q[kSecValueData as String] = data
        // afterFirstUnlock so a background refresh can still read the token.
        q[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        let status = SecItemAdd(q as CFDictionary, nil)
        guard status == errSecSuccess else { throw Error.unexpectedStatus(status) }
    }

    static func read(_ key: Key) throws -> String? {
        var q = query(key)
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &item)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else { throw Error.unexpectedStatus(status) }
        guard let data = item as? Data, let s = String(data: data, encoding: .utf8) else {
            throw Error.dataDecodingFailed
        }
        return s
    }

    static func delete(_ key: Key) throws {
        let status = SecItemDelete(query(key) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw Error.unexpectedStatus(status)
        }
    }

    /// Clears every stored secret — used on logout.
    static func deleteAll() {
        for key in Key.allCases { try? delete(key) }
    }
}
