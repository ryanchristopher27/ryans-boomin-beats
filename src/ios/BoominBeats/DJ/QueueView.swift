import SwiftUI

struct QueueView: View {
    @Environment(QueueStore.self) private var queue: QueueStore?
    @State private var showingSearch = false

    var body: some View {
        NavigationStack {
            Group {
                if let queue {
                    list(queue)
                } else {
                    ProgressView()
                }
            }
            .navigationTitle("Queue")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { EditButton() }
                ToolbarItem(placement: .topBarTrailing) {
                    if let queue {
                        @Bindable var queue = queue
                        Toggle(isOn: $queue.partyMode) {
                            Label("Party Mode", systemImage: queue.partyMode ? "sun.max.fill" : "sun.max")
                        }
                        .toggleStyle(.button)
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showingSearch = true } label: { Image(systemName: "plus") }
                }
            }
            .sheet(isPresented: $showingSearch) { AddTrackView() }
        }
    }

    private func list(_ queue: QueueStore) -> some View {
        List {
            SyncBanner()
            if queue.partyMode {
                Label("Party mode: screen stays on", systemImage: "sun.max.fill")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let message = queue.message {
                Text(message).font(.footnote).foregroundStyle(.red)
            }

            if !queue.requests.isEmpty {
                Section {
                    ForEach(queue.requests) { request in
                        VStack(alignment: .leading, spacing: 8) {
                            HStack(spacing: 12) {
                                artwork(request.imageURL)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(request.title).lineLimit(1)
                                    Text(request.artistLine)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                            }
                            HStack {
                                Button("Keep") { queue.keep(request) }
                                Button("Later") { Task { await queue.later(request) } }
                                Button("Decline", role: .destructive) { queue.decline(request) }
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                        }
                    }
                } header: {
                    Text("Requests")
                } footer: {
                    Text("Added in Spotify by someone else. Keep plays it where Spotify put it, Later moves it to the end of Up Next, Decline skips it.")
                }
            }

            if !queue.sent.isEmpty {
                Section {
                    ForEach(queue.sent) { item in
                        row(item)
                            .opacity(item.skipOnArrival ? 0.4 : 1)
                            .swipeActions {
                                if !item.skipOnArrival {
                                    Button("Remove", role: .destructive) {
                                        Task { await queue.removeSent(item) }
                                    }
                                    Button("Later") {
                                        Task { await queue.playLater(item) }
                                    }
                                    .tint(.orange)
                                }
                            }
                    }
                } header: {
                    Text("Sent to Spotify")
                } footer: {
                    Text("Already in Spotify's queue. Removed tracks are skipped when they come up.")
                }
            }

            Section("Up Next") {
                if queue.upcoming.isEmpty {
                    Text("Tap + to add songs.").foregroundStyle(.secondary)
                }
                ForEach(queue.upcoming) { row($0) }
                    .onMove { queue.moveUpcoming(from: $0, to: $1) }
                    .onDelete { queue.removeUpcoming(at: $0) }
            }
        }
    }

    private func artwork(_ url: URL?) -> some View {
        AsyncImage(url: url) { image in
            image.resizable().aspectRatio(contentMode: .fill)
        } placeholder: {
            RoundedRectangle(cornerRadius: 4).fill(.quaternary)
        }
        .frame(width: 44, height: 44)
        .clipShape(RoundedRectangle(cornerRadius: 4))
    }

    private func row(_ item: QueueItem) -> some View {
        HStack(spacing: 12) {
            artwork(item.imageURL)

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    if item.addedByDJ == true {
                        Image(systemName: "sparkles").font(.caption).foregroundStyle(.tint)
                            .accessibilityLabel("Added by the DJ")
                    }
                    Text(item.title)
                        .lineLimit(1)
                        .strikethrough(item.skipOnArrival)
                }
                Text(item.skipOnArrival ? "Will be skipped" : item.artistLine)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
    }
}

/// Decodes GET /search/ (routers/search.py). Deezer results since Q3: `id` is
/// an ISRC key, not a Spotify id, so adding one resolves it first.
private struct SearchResponse: Decodable {
    struct Result: Decodable, Identifiable {
        let id: String
        let title: String
        let artists: [String]
        let image: String
        var isrc: String?

        var imageURL: URL? { URL(string: image) }
    }
    let tracks: [Result]
}

private struct AddTrackView: View {
    private func row(_ result: SearchResponse.Result) -> some View {
        let state = status[result.id]
        let isAdding = adding.contains(result.id)
        let note = Self.note(state)
        return Button {
            add(result)
        } label: {
            HStack(spacing: 12) {
                AsyncImage(url: result.imageURL) { image in
                    image.resizable().aspectRatio(contentMode: .fill)
                } placeholder: {
                    RoundedRectangle(cornerRadius: 4).fill(.quaternary)
                }
                .frame(width: 44, height: 44)
                .clipShape(RoundedRectangle(cornerRadius: 4))
                .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 2) {
                    Text(result.title).foregroundStyle(.primary).lineLimit(1)
                    Text(note ?? result.artists.joined(separator: ", "))
                        .font(.caption)
                        .foregroundStyle(note == nil ? Color.secondary : Color.orange)
                        .lineLimit(1)
                }
                Spacer()
                if isAdding {
                    ProgressView()
                } else {
                    Image(systemName: state == .added ? "checkmark.circle.fill" : "plus.circle")
                }
            }
        }
        .disabled(isAdding || state == .added || state == .notOnSpotify)
    }

    private func add(_ result: SearchResponse.Result) {
        adding.insert(result.id)
        Task {
            let r = await queue?.addSong(isrc: result.isrc, title: result.title, artists: result.artists,
                                         cleanOnly: settings.cleanOnly) ?? .unavailable
            status[result.id] = r
            adding.remove(result.id)
        }
    }

    static func note(_ result: QueueStore.PickResult?) -> String? {
        switch result {
        case .notOnSpotify: return "Not on Spotify"
        case .explicitOnly: return "Explicit version only"
        case .unavailable: return "Couldn't add that right now"
        default: return nil
        }
    }

    @Environment(SpotifySession.self) private var session
    @Environment(QueueStore.self) private var queue: QueueStore?
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var results: [SearchResponse.Result] = []
    @Environment(DJSettings.self) private var settings
    @State private var status: [String: QueueStore.PickResult] = [:]
    @State private var adding: Set<String> = []
    @State private var error: String?

    var body: some View {
        NavigationStack {
            List {
                if let error {
                    Text(error).font(.footnote).foregroundStyle(.red)
                }
                ForEach(results) { result in
                    row(result)
                }
            }
            .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "Song name")
            .navigationTitle("Add to Queue")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } }
            }
            // Debounced: re-runs (and cancels the previous search) on each keystroke.
            .task(id: query) {
                let q = query.trimmingCharacters(in: .whitespaces)
                // Each search spends Spotify's small daily quota (tracker e2df2d).
                guard q.count >= 3 else { results = []; return }
                try? await Task.sleep(for: .milliseconds(350))
                guard !Task.isCancelled else { return }
                do {
                    let response: SearchResponse = try await APIClient(session: session).get("search/", query: ["searchValue": q])
                    results = response.tracks
                    error = nil
                } catch {
                    self.error = (error as? APIClient.Error)?.errorDescription ?? error.localizedDescription
                }
            }
        }
    }
}
