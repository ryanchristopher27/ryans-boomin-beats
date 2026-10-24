import Testing
@testable import BoominBeats

/// Which token-endpoint failures sign the user out. Before this, any refresh
/// failure did, so a dropped connection at launch wiped the session.
struct SessionTests {
    @Test func successIsNotAFailure() {
        #expect(SpotifySession.TokenError.classify(status: 200) == nil)
    }

    @Test func aRejectedGrantSignsOut() {
        #expect(SpotifySession.TokenError.classify(status: 400) == .rejected(status: 400))
        #expect(SpotifySession.TokenError.classify(status: 401) == .rejected(status: 401))
    }

    @Test func transientFailuresKeepTheSession() {
        for status in [429, 500, 503, -1] {
            #expect(SpotifySession.TokenError.classify(status: status) == .unavailable(status: status))
        }
    }
}
