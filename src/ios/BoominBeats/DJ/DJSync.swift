import Foundation
import UIKit

/// Keeps the DJ queue, options, feedback and history in step across devices
/// (SY3), through the backend's shared `dj_state` (SY1).
///
/// Jam-style roles: the **primary** device is the only one that drives Spotify
/// (`QueueStore.isPrimary`); every device can edit. No silent failover: when
/// the primary goes quiet for 60s, others are told and can "Drive from here".
///
/// Flow: every player poll carries `dj {version, primary}`. A newer version
/// pulls the document; a local edit pushes it (debounced) with the version it
/// was based on. On 409, `SyncDoc.merge` keeps this device's changed fields on
/// top of the server's and retries. Sync failures never block the local app:
/// the stores keep working from their own persisted copies.
@MainActor
@Observable
final class DJSync {
    enum Status: Equatable {
        /// No answer from sync yet, or this server has it switched off.
        case unavailable
        /// In step with the server.
        case synced
    }

    private(set) var status: Status = .unavailable
    private(set) var primary: PrimaryInfo?
    /// One-off notice, e.g. after adopting another device's queue on first sync.
    private(set) var notice: String?

    let deviceID: String
    let deviceLabel: String

    var isPrimary: Bool { queue.isPrimary }
    var primaryIsElsewhere: Bool { primary.map { $0.device != deviceID } ?? false }

    private let client: APIClient
    private let queue: QueueStore
    private let settings: DJSettings
    private let nowPlaying: NowPlayingModel

    private var version = 0
    /// The last document both this device and the server agreed on.
    private var base: SyncDoc?
    private var isApplying = false
    private var pushTask: Task<Void, Never>?
    private var isSyncing = false

    private static let deviceKey = "dj_device_id"
    private static let roleKey = "dj_is_primary"

    init(client: APIClient, queue: QueueStore, settings: DJSettings, nowPlaying: NowPlayingModel) {
        self.client = client
        self.queue = queue
        self.settings = settings
        self.nowPlaying = nowPlaying
        if let id = UserDefaults.standard.string(forKey: Self.deviceKey) {
            deviceID = id
        } else {
            deviceID = UUID().uuidString
            UserDefaults.standard.set(deviceID, forKey: Self.deviceKey)
        }
        deviceLabel = UIDevice.current.model  // "iPhone" / "iPad"
        // Start in the last known role, so a participant doesn't drive during the
        // moments before its first poll says otherwise.
        if UserDefaults.standard.object(forKey: Self.roleKey) != nil {
            queue.isPrimary = UserDefaults.standard.bool(forKey: Self.roleKey)
        }
        let changed: () -> Void = { [weak self] in self?.localChanged() }
        queue.onChange = changed
        settings.onChange = changed
        nowPlaying.onChange = changed
        nowPlaying.sync = self
    }

    // MARK: - Driven by the player poll

    func observe(_ dj: DJStatus?) async {
        guard let dj else {
            // Sync off or unreachable. Keep the last known role: a device that was a
            // participant must not start driving because one poll failed.
            if base == nil { status = .unavailable }
            return
        }
        setPrimary(dj.primary)
        if dj.version == 0 {
            await seed()
        } else if dj.version != version, pushTask == nil {
            await pull()
        }
    }

    /// Drive from here: take the primary role (always succeeds).
    func claimPrimary() async {
        let body = try? JSONEncoder().encode(["device": deviceID, "label": deviceLabel])
        guard let (code, data) = try? await client.raw("POST", "dj/primary", json: body),
              code == 200, let env = try? SyncDoc.decoder.decode(SyncEnvelope.self, from: data) else { return }
        setPrimary(env.primary)
    }

    func dismissNotice() { notice = nil }

    // MARK: - Local edits

    private func localChanged() {
        guard !isApplying, base != nil else { return }
        pushTask?.cancel()
        pushTask = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(400))  // coalesce bursts (drag-reorder)
            guard !Task.isCancelled else { return }
            await self?.push()
            self?.pushTask = nil
        }
    }

    private func push(attempt: Int = 0) async {
        guard let base else { return }
        let local = snapshot()
        guard local != base, attempt < 3 else { return }
        guard let body = try? SyncDoc.encoder.encode(PutBody(state: local)),
              let (code, data) = try? await client.raw("PUT", "dj/state", json: body, headers: ["If-Match": String(version)]),
              let env = try? SyncDoc.decoder.decode(SyncEnvelope.self, from: data)
        else { return }  // offline: the local copy stands; the next edit or poll retries
        switch code {
        case 200:
            version = env.version
            self.base = local
            setPrimary(env.primary)
            status = .synced
        case 409:
            // Someone else saved first. Keep our changed fields on top of theirs.
            let server = env.state ?? SyncDoc()
            let merged = SyncDoc.merge(base: base, local: local, server: server)
            adopt(server, version: env.version)
            apply(merged)
            await push(attempt: attempt + 1)
        default:
            return
        }
    }

    // MARK: - Server changes

    private func pull() async {
        guard !isSyncing else { return }
        isSyncing = true
        defer { isSyncing = false }
        let before = snapshot()
        guard let (code, data) = try? await client.raw("GET", "dj/state"), code == 200,
              let env = try? SyncDoc.decoder.decode(SyncEnvelope.self, from: data) else { return }
        guard let server = env.state else { return }
        if base == nil, !before.isEmpty, server != before {
            notice = "Using the queue from your other device."
        }
        // An edit that landed while the GET was in flight is kept on top of the
        // server's copy and pushed, not overwritten (web review W2).
        let current = snapshot()
        let editedMeanwhile = base != nil && current != before
        adopt(server, version: env.version)
        if editedMeanwhile {
            apply(SyncDoc.merge(base: before, local: current, server: server))
            localChanged()
        } else {
            apply(server)
        }
        setPrimary(env.primary)
        status = .synced
    }

    /// No shared state yet: this device uploads its own and becomes primary (the
    /// first device seeds it). Losing that race just means adopting the winner.
    private func seed() async {
        guard !isSyncing else { return }
        isSyncing = true
        defer { isSyncing = false }
        let local = snapshot()
        guard let body = try? SyncDoc.encoder.encode(PutBody(state: local)),
              let (code, data) = try? await client.raw("PUT", "dj/state", json: body, headers: [
                  "If-Match": "0", "X-DJ-Device": deviceID, "X-DJ-Label": deviceLabel,
              ]),
              let env = try? SyncDoc.decoder.decode(SyncEnvelope.self, from: data)
        else { return }
        if code == 200 {
            adopt(local, version: env.version)
            setPrimary(env.primary)
            status = .synced
        } else if code == 409, let server = env.state {
            adopt(server, version: env.version)
            apply(server)
            setPrimary(env.primary)
            status = .synced
        }
    }

    // MARK: - Plumbing

    private func snapshot() -> SyncDoc {
        SyncDoc(queue: queue.syncQueue, options: settings.syncOptions,
                feedback: nowPlaying.syncFeedback, recent: nowPlaying.syncRecent)
    }

    private func adopt(_ doc: SyncDoc, version: Int) {
        base = doc
        self.version = version
    }

    private func apply(_ doc: SyncDoc) {
        isApplying = true
        defer { isApplying = false }
        queue.apply(doc.queue)
        settings.apply(doc.options)
        nowPlaying.apply(feedback: doc.feedback, recent: doc.recent)
    }

    private func setPrimary(_ info: PrimaryInfo?) {
        primary = info
        // With no primary recorded (legacy row), this device drives until someone claims.
        let nowPrimary = info.map { $0.device == deviceID } ?? true
        guard nowPrimary != queue.isPrimary else { return }
        queue.isPrimary = nowPrimary
        UserDefaults.standard.set(nowPrimary, forKey: Self.roleKey)
        if nowPrimary { Task { await queue.startDriving() } }
    }
}

private struct PutBody: Encodable {
    let state: SyncDoc
}
