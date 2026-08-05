import SwiftUI

@MainActor
@Observable
final class ProfileModel {
    enum LoadState {
        case idle, loading, loaded, failed(String)
    }

    var state: LoadState = .idle
    var user: SpotifyUser?
    var artists: [Artist] = []
    var tracks: [Track] = []
    var timeRange: TimeRange = .shortTerm
    var topCount = 20

    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func load() async {
        state = .loading
        do {
            let response: ProfileResponse = try await client.get(
                "get-profile/",
                query: ["num_tops": String(topCount), "time_period": timeRange.rawValue]
            )
            user = response.profile
            artists = response.topArtists
            tracks = response.topTracks
            state = .loaded
        } catch {
            state = .failed((error as? APIClient.Error)?.errorDescription ?? error.localizedDescription)
        }
    }
}

struct ProfileView: View {
    @Environment(SpotifySession.self) private var session
    @State private var model: ProfileModel?
    @State private var showingSettings = false

    var body: some View {
        NavigationStack {
            Group {
                if let model {
                    content(model)
                } else {
                    ProgressView()
                }
            }
            .navigationTitle("Profile")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { showingSettings = true } label: {
                        Image(systemName: "gearshape")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Log Out", role: .destructive) { session.logOut() }
                }
            }
            .sheet(isPresented: $showingSettings) {
                SettingsView()
                    // The host may have changed; re-fetch against the new one.
                    .onDisappear { Task { await model?.load() } }
            }
        }
        .task {
            if model == nil {
                let m = ProfileModel(client: APIClient(session: session))
                model = m
                await m.load()
            }
        }
    }

    @ViewBuilder
    private func content(_ model: ProfileModel) -> some View {
        @Bindable var model = model

        switch model.state {
        case .idle, .loading:
            ProgressView("Loading your profile…")

        case let .failed(message):
            ContentUnavailableView {
                Label("Couldn't load profile", systemImage: "exclamationmark.triangle")
            } description: {
                Text(message)
            } actions: {
                Button("Try Again") { Task { await model.load() } }
            }

        case .loaded:
            List {
                Section {
                    Picker("Time range", selection: $model.timeRange) {
                        ForEach(TimeRange.allCases) { Text($0.label).tag($0) }
                    }
                    .pickerStyle(.segmented)
                    .onChange(of: model.timeRange) { Task { await model.load() } }
                }

                Section("Top Artists") {
                    ForEach(model.artists.prefix(10)) { artist in
                        HStack(spacing: 12) {
                            artwork(artist.imageURL, size: 44)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(artist.name)
                                if !artist.genres.isEmpty {
                                    Text(artist.genres.prefix(2).joined(separator: " · "))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }

                Section("Top Tracks") {
                    ForEach(model.tracks.prefix(10)) { track in
                        HStack(spacing: 12) {
                            artwork(track.imageURL, size: 44)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(track.title).lineLimit(1)
                                Text(track.artistLine)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                            Spacer()
                            Text(track.duration)
                                .font(.caption.monospacedDigit())
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .refreshable { await model.load() }
        }
    }

    private func artwork(_ url: URL?, size: CGFloat) -> some View {
        AsyncImage(url: url) { image in
            image.resizable().aspectRatio(contentMode: .fill)
        } placeholder: {
            RoundedRectangle(cornerRadius: 4).fill(.quaternary)
        }
        .frame(width: size, height: size)
        .clipShape(RoundedRectangle(cornerRadius: 4))
    }
}
