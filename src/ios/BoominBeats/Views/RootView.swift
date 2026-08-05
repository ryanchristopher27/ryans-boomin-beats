import SwiftUI

struct RootView: View {
    @Environment(SpotifySession.self) private var session

    var body: some View {
        Group {
            if session.isLoggedIn {
                ProfileView()
            } else {
                LoginView()
            }
        }
        .animation(.default, value: session.isLoggedIn)
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
