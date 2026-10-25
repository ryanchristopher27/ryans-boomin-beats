import SwiftUI

/// Who's driving the DJ (SY3), shown at the top of Now Playing and Queue.
/// Quiet when this device drives; a clear call to action when the primary
/// elsewhere has gone quiet.
struct SyncBanner: View {
    @Environment(DJSync.self) private var sync: DJSync?
    @State private var claiming = false

    var body: some View {
        if let sync, sync.status == .synced, let primary = sync.primary {
            VStack(alignment: .leading, spacing: 6) {
                if sync.isPrimary {
                    Label("Driving from this \(sync.deviceLabel)", systemImage: "dot.radiowaves.left.and.right")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                } else {
                    HStack {
                        Label(primary.online ? "Driving from \(primary.label)" : "\(primary.label) stopped driving",
                              systemImage: primary.online ? "dot.radiowaves.left.and.right" : "exclamationmark.triangle")
                            .font(.footnote)
                            .foregroundStyle(primary.online ? AnyShapeStyle(.secondary) : AnyShapeStyle(.orange))
                        Spacer()
                        Button(claiming ? "Taking over…" : "Drive from here") {
                            claiming = true
                            Task { await sync.claimPrimary(); claiming = false }
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .disabled(claiming)
                    }
                }
                if let notice = sync.notice {
                    HStack {
                        Text(notice).font(.footnote)
                        Spacer()
                        Button("Dismiss") { sync.dismissNotice() }.controlSize(.small)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
