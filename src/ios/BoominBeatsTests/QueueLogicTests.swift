import Foundation
import Testing
@testable import BoominBeats

/// Pure queue logic behind the app-owned queue (DJ2) and autopilot (DJ4).
/// Review W4: these paths were only ever checked by hand in the Simulator.
/// Run: xcodebuild test -scheme BoominBeats -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
struct QueueLogicTests {
    private func item(_ id: String, skip: Bool = false) -> QueueItem {
        QueueItem(trackID: id, title: id, artists: ["A"], image: "", skipOnArrival: skip)
    }

    private func ids(_ items: [QueueItem]) -> [String] { items.map(\.trackID) }

    // MARK: arrival

    @Test func arrivalDropsEverythingUpToTheArrivedTrack() {
        let (rest, arrived) = QueueStore.arrival(of: "b", in: [item("a"), item("b"), item("c")])
        #expect(arrived?.trackID == "b")
        #expect(ids(rest) == ["c"])
    }

    @Test func arrivalOfAnUnknownTrackChangesNothing() {
        let sent = [item("a"), item("b")]
        let (rest, arrived) = QueueStore.arrival(of: "guest", in: sent)
        #expect(arrived == nil)
        #expect(ids(rest) == ["a", "b"])
    }

    @Test func arrivalMatchesTheFirstCopyOfADuplicate() {
        // "Later" re-adds a copy: the skip-flagged original arrives first.
        let (rest, arrived) = QueueStore.arrival(of: "x", in: [item("x", skip: true), item("y"), item("x")])
        #expect(arrived?.skipOnArrival == true)
        #expect(ids(rest) == ["y", "x"])
    }

    // MARK: reconcile

    @Test func reconcileDropsThePlayedPrefix() {
        let kept = QueueStore.reconciled([item("a"), item("b"), item("c")], against: ["b", "c", "ctx1"])
        #expect(ids(kept) == ["b", "c"])
    }

    @Test func reconcileDropsEverythingWhenNothingIsVisible() {
        let full = (1...20).map { "ctx\($0)" }
        #expect(QueueStore.reconciled([item("a"), item("b")], against: full).isEmpty)
    }

    @Test func reconcileMatchesDuplicatesInOrder() {
        let kept = QueueStore.reconciled([item("x"), item("y"), item("x")], against: ["x", "y", "x"])
        #expect(ids(kept) == ["x", "y", "x"])
    }

    @Test func reconcileDropsAMissingTrailingTrackWhenTheViewIsNotFull() {
        // A short view shows the whole queue, so "c" really is gone.
        let kept = QueueStore.reconciled([item("a"), item("b"), item("c")], against: ["a", "b"])
        #expect(ids(kept) == ["a", "b"])
    }

    @Test func reconcileKeepsTracksPastAFullWindow() {
        // Review S2: guests queued ahead push "c" and "d" past the 20-item view.
        let view = ["a"] + (1...18).map { "guest\($0)" } + ["b"]
        let kept = QueueStore.reconciled([item("a"), item("b"), item("c"), item("d")], against: view)
        #expect(ids(kept) == ["a", "b", "c", "d"])
    }

    // MARK: guest requests (DJ5)

    private func detect(_ previous: [String]?, _ current: [String], app: Set<String> = [],
                        ignoring: Set<String> = [], insertions: Bool = true) -> [String] {
        QueueStore.detectRequests(previous: previous, current: current, appIDs: app,
                                  ignoring: ignoring, insertionsAllowed: insertions).map { current[$0] }
    }

    @Test func wedgedTrackAheadOfAnAppTrackIsARequest() {
        // App sent "next"; a guest queued before the app's next top-up.
        #expect(detect(nil, ["g", "next", "c1", "c2"], app: ["next"]) == ["g"])
    }

    @Test func trackAfterTheLastAppTrackIsNotWedged() {
        // Could be a guest or the playing context; on its own it's ambiguous.
        #expect(detect(nil, ["next", "g", "c1"], app: ["next"]).isEmpty)
    }

    @Test func midViewInsertionIsARequestOnTheNextPoll() {
        let before = ["next", "c1", "c2", "c3"]
        #expect(detect(before, ["next", "g", "c1", "c2", "c3"], app: ["next"]) == ["g"])
    }

    @Test func contextSlidingInAtTheTailIsNotARequest() {
        // A track finished: the head left and a new context track joined at the end.
        #expect(detect(["c1", "c2", "c3"], ["c2", "c3", "c4"]).isEmpty)
    }

    @Test func smartShuffleDisablesTheInsertionRule() {
        let before = ["next", "c1", "c2"]
        #expect(detect(before, ["next", "rec", "c1", "c2"], app: ["next"], insertions: false).isEmpty)
    }

    @Test func knownRequestsAreNotFlaggedAgain() {
        #expect(detect(nil, ["g", "next"], app: ["next"], ignoring: ["g"]).isEmpty)
    }

    @Test func aDuplicateRequestIsReportedOnce() {
        #expect(detect(nil, ["g", "g", "next"], app: ["next"]) == ["g"])
    }

    // MARK: autopilot

    private func move(_ name: String, _ ids: [String]) -> MoveSuggestions.Move {
        MoveSuggestions.Move(move: name, tracks: ids.map {
            MoveSuggestions.Pick(id: $0, title: $0, artists: ["A"], image: "", reason: "")
        })
    }

    private var moves: [MoveSuggestions.Move] {
        [move("hold", ["h1", "h2"]), move("lift", ["l1", "l2"]), move("drop", ["d1"]),
         move("pivot", ["p1", "p2"]), move("curveball", ["c1"])]
    }

    @Test func safeAutopilotStaysOnHoldLiftDropAndInterleaves() {
        let picks = SuggestionStore.autopilotCandidates(moves: moves, adventurousness: 0.1, excluding: [])
        #expect(picks.map(\.id) == ["h1", "l1", "d1", "h2", "l2"])
    }

    @Test func boldAutopilotLeadsWithPivotAndCurveball() {
        let picks = SuggestionStore.autopilotCandidates(moves: moves, adventurousness: 0.9, excluding: [])
        #expect(picks.prefix(4).map(\.id) == ["p1", "c1", "l1", "h1"])
    }

    @Test func aGoalMoveLeadsAutopilotWithAllItsPicks() {
        let withGoal = [move("toward", ["t1", "t2"])] + moves
        let picks = SuggestionStore.autopilotCandidates(moves: withGoal, adventurousness: 0.1,
                                                         excluding: ["t2"], lead: "toward")
        #expect(picks.map(\.id).prefix(3) == ["t1", "h1", "l1"])
    }

    @Test func goalCacheKeyMovesWithArcProgress() {
        var arc = DJGoal(kind: .arc, shape: .build, minutes: 30, startedAt: Date())
        let early = SuggestionStore.goalKey(arc)
        arc.startedAt = Date().addingTimeInterval(-6 * 60)
        #expect(SuggestionStore.goalKey(arc) != early)
        #expect(SuggestionStore.goalKey(nil) == "none")
        #expect(SuggestionStore.goalKey(DJGoal(kind: .drift)) == "drift")
    }

    @Test func autopilotSkipsAlreadyQueuedTracks() {
        let picks = SuggestionStore.autopilotCandidates(moves: moves, adventurousness: 0.1, excluding: ["h1", "l1"])
        #expect(picks.first?.id == "d1")
    }
}
