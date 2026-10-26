import SwiftUI

struct RootView: View {
    @Environment(SpotifySession.self) private var session

    var body: some View {
        Group {
            if session.isLoggedIn {
                MainTabs()
            } else {
                LoginView()
            }
        }
        .animation(.default, value: session.isLoggedIn)
    }
}

/// Owns the DJ models, so playback polling and queue top-ups keep running whichever
/// tab is showing — a tab's own `.task` is cancelled when the user switches away.
struct MainTabs: View {
    @Environment(SpotifySession.self) private var session
    @Environment(\.scenePhase) private var scenePhase
    @State private var nowPlaying: NowPlayingModel?
    @State private var queue: QueueStore?
    @State private var suggestions: SuggestionStore?
    @State private var djSettings = DJSettings()
    @State private var sync: DJSync?
    @State private var tab = MainTab.nowPlaying

    enum MainTab { case nowPlaying, queue, profile }

    /// Suggestions cost an LLM call and ~10-25 Spotify searches from a small
    /// daily quota (tracker e2df2d), so fetch them only while the moves are on
    /// screen, or when Autofill/Driver need picks to queue.
    private var wantsSuggestions: Bool {
        tab == .nowPlaying || djSettings.mode.autopilotTarget > 0
    }

    var body: some View {
        TabView(selection: $tab) {
            Tab("Now Playing", systemImage: "play.circle", value: MainTab.nowPlaying) { NowPlayingView() }
            Tab("Queue", systemImage: "list.bullet", value: MainTab.queue) { QueueView() }
                .badge(queue?.requests.count ?? 0)
            Tab("Profile", systemImage: "person.crop.circle", value: MainTab.profile) { ProfileView() }
        }
        .environment(nowPlaying)
        .environment(queue)
        .environment(suggestions)
        .environment(djSettings)
        .environment(sync)
        // Prefetch at this level, not in a tab. Re-keyed on track change (which
        // cancels a stale load) and on coming back to Now Playing.
        .task(id: "\(nowPlaying?.state?.track?.id ?? "")|\(wantsSuggestions)") {
            if wantsSuggestions { await prefetch() }
        }
        // Switching into Autofill/Driver should act now, not at the next track.
        .onChange(of: djSettings.mode) { if wantsSuggestions { Task { await prefetch() } } }
        // Restarts on every foreground/background flip; polling only runs while
        // active, since iOS suspends the app in the background anyway.
        .task(id: scenePhase == .active) {
            if queue == nil {
                let client = APIClient(session: session)
                let q = QueueStore(client: client)
                queue = q
                let np = NowPlayingModel(client: client, queue: q)
                nowPlaying = np
                suggestions = SuggestionStore(client: client)
                sync = DJSync(client: client, queue: q, settings: djSettings, nowPlaying: np)
            }
            guard scenePhase == .active, let nowPlaying else { return }
            await nowPlaying.run()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background, let queue {
                Task { await queue.prepareForBackground() }
            }
        }
    }

    private func prefetch() async {
        guard let nowPlaying, let queue, let suggestions, let track = nowPlaying.state?.track else { return }
        guard djSettings.mode != .whisper else { suggestions.reset(); return }
        await suggestions.load(for: track, session: nowPlaying, queue: queue, settings: djSettings)
    }
}

struct LoginView: View {
    @Environment(SpotifySession.self) private var session
    @State private var showingSettings = false

    var body: some View {
        VStack(spacing: 24) {
            HStack {
                Spacer()
                Button { showingSettings = true } label: {
                    Image(systemName: "gearshape")
                }
                .padding()
            }

            Spacer()

            Image(systemName: "waveform")
                .font(.system(size: 64, weight: .light))
                .foregroundStyle(.tint)

            VStack(spacing: 6) {
                Text("Boomin Beats")
                    .font(.largeTitle.bold())
                Text("Your Spotify listening, examined.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if case let .failed(message) = session.state {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
            }

            Button {
                Task { await session.logIn() }
            } label: {
                if case .authenticating = session.state {
                    ProgressView().tint(.white).frame(maxWidth: .infinity)
                } else {
                    Text("Connect Spotify").frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .padding(.horizontal, 40)
            .disabled(session.state == .authenticating)

            Spacer()
            Spacer()
        }
        .sheet(isPresented: $showingSettings) { SettingsView() }
    }
}

#Preview {
    LoginView().environment(SpotifySession())
}
