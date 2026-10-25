import Foundation
import Testing
@testable import BoominBeats

/// Cross-device sync (SY3): the 409 merge and the wire format the server's
/// strict schema (routers/dj_state.py) accepts.
struct SyncTests {
    private func item(_ id: String) -> QueueItem {
        QueueItem(trackID: id, title: id, artists: ["A"], image: "")
    }

    @Test func mergeKeepsBothDevicesEditsToDifferentFields() {
        var base = SyncDoc()
        base.queue.upcoming = [item("a"), item("b")]
        var local = base
        local.queue.upcoming.reverse()          // phone reorders Up Next
        var server = base
        server.options.mode = "driver"           // web changed the dial

        let merged = SyncDoc.merge(base: base, local: local, server: server)
        #expect(merged.queue.upcoming.map(\.trackID) == ["b", "a"])
        #expect(merged.options.mode == "driver")
    }

    @Test func mergePrefersThisDeviceWhenBothChangedTheSameField() {
        let base = SyncDoc()
        var local = base
        local.options.adventurousness = 0.9
        var server = base
        server.options.adventurousness = 0.1
        #expect(SyncDoc.merge(base: base, local: local, server: server).options.adventurousness == 0.9)
    }

    @Test func mergeTakesServerFieldsThisDeviceDidNotTouch() {
        let base = SyncDoc()
        var server = base
        server.recent = [SyncDoc.TrackRef(item("x").asTrackStub)]
        #expect(SyncDoc.merge(base: base, local: base, server: server) == server)
    }

    @Test func encodesTheServersFieldNamesAndISODates() throws {
        var doc = SyncDoc()
        doc.queue.upcoming = [item("a")]
        doc.options.goal = DJGoal(kind: .arc, shape: .windDown, minutes: 30,
                                  startedAt: Date(timeIntervalSince1970: 1_800_000_000))
        let json = try #require(try JSONSerialization.jsonObject(with: SyncDoc.encoder.encode(doc)) as? [String: Any])
        #expect(Set(json.keys) == ["queue", "options", "feedback", "recent"])
        let queue = try #require(json["queue"] as? [String: Any])
        #expect(Set(queue.keys) == ["sent", "upcoming", "requests", "guestSkips", "keptGuests"])
        let upcoming = try #require((queue["upcoming"] as? [[String: Any]])?.first)
        #expect(Set(upcoming.keys) == ["id", "trackID", "title", "artists", "image", "skipOnArrival"])
        let goal = try #require((json["options"] as? [String: Any])?["goal"] as? [String: Any])
        #expect(goal["startedAt"] as? String == "2027-01-15T08:00:00Z")
        #expect(goal["shape"] as? String == "wind_down")
    }

    @Test func decodesWhatTheServerSendsBack() throws {
        let body = """
        {"version": 3, "primary": {"device": "web-1", "label": "MacBook web", "online": false},
         "state": {"queue": {"sent": [], "upcoming": [], "requests": [], "guestSkips": [], "keptGuests": []},
                   "options": {"mode": "autofill", "adventurousness": 0.5, "clean": false, "goal": null,
                               "avoidTracks": [], "avoidArtists": []},
                   "feedback": {"liked": [], "disliked": [], "skipped": []}, "recent": []}}
        """
        let env = try SyncDoc.decoder.decode(SyncEnvelope.self, from: Data(body.utf8))
        #expect(env.version == 3)
        #expect(env.primary == PrimaryInfo(device: "web-1", label: "MacBook web", online: false))
        #expect(env.state?.options.mode == "autofill")
    }
}

private extension QueueItem {
    var asTrackStub: Track {
        Track(id: trackID, title: title, artists: artists, image: image, album: "",
              durationMs: 0, explicit: false, trackURL: "", releaseDate: nil)
    }
}
