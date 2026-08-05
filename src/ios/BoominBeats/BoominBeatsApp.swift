import OSLog
import SwiftUI

@main
struct BoominBeatsApp: App {
    @State private var session = SpotifySession()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(session)
                .task {
                    #if DEBUG
                    Diagnostics.keychainSelfTest()
                    #endif
                    await session.restore()
                }
        }
    }
}

#if DEBUG
/// Startup checks whose results are readable from `log stream --predicate
/// 'subsystem == "com.ryanchristopher.boominbeats"'` — so failures can be
/// diagnosed from the host without driving the UI.
enum Diagnostics {
    static let log = Logger(subsystem: "com.ryanchristopher.boominbeats", category: "diagnostics")

    static func keychainSelfTest() {
        let probe = "selftest-\(UUID().uuidString.prefix(8))"
        do {
            try Keychain.write(probe, for: .deviceKey)
            let read = try Keychain.read(.deviceKey)
            try Keychain.delete(.deviceKey)
            log.info("KEYCHAIN OK write/read/delete round-trip; matched=\(read == probe, privacy: .public)")
        } catch let error as Keychain.Error {
            log.error("KEYCHAIN FAILED \(error.errorDescription ?? "no description", privacy: .public)")
        } catch {
            log.error("KEYCHAIN FAILED \(String(describing: error), privacy: .public)")
        }
    }
}
#endif
