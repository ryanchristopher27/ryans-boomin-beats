import SwiftUI

struct NowPlayingView: View {
    @Environment(NowPlayingModel.self) private var model: NowPlayingModel?
    @Environment(QueueStore.self) private var queue: QueueStore?
    @Environment(SuggestionStore.self) private var suggestions: SuggestionStore?
    @Environment(DJSettings.self) private var settings
    @State private var queued: Set<String> = []

    var body: some View {
        NavigationStack {
            Group {
                if let model {
                    content(model)
                } else {
                    ProgressView()
                }
            }
            .navigationTitle("Now Playing")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    @ViewBuilder
    private func content(_ model: NowPlayingModel) -> some View {
        ScrollView {
        VStack(spacing: 24) {
            if let state = model.state, state.active {
                if let track = state.track {
                    player(model, state: state, track: track)
                    controls
                    moves(for: track)
                } else {
                    ContentUnavailableView(
                        "Not a song",
                        systemImage: "waveform",
                        description: Text("Spotify is playing something other than a track.")
                    )
                }
            } else if model.state != nil {
                ContentUnavailableView(
                    "Nothing playing",
                    systemImage: "speaker.slash",
                    description: Text("Start Spotify on any device and it'll show up here.")
                )
            } else {
                ProgressView()
            }

            if let message = model.message {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
            }
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        }
    }

    // MARK: - Moves (DJ3)

    @ViewBuilder
    private func moves(for track: Track) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Next Moves").font(.title3.bold())
                Spacer()
                if let suggestions {
                    Button { refresh(track) } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(suggestions.isLoading)
                }
            }

            switch suggestions?.state ?? .idle {
            case .idle:
                Button("Get moves") { refresh(track) }
                    .buttonStyle(.bordered)
            case .needsKey:
                Text("Add an AI provider and key in Settings (Profile tab → gear) to get suggestions.")
                    .font(.footnote).foregroundStyle(.secondary)
            case .loading:
                HStack(spacing: 8) {
                    ProgressView()
                    Text("Reading the room…").font(.footnote).foregroundStyle(.secondary)
                }
            case let .failed(message):
                Text(message).font(.footnote).foregroundStyle(.red)
            case let .loaded(moves):
                ForEach(moves) { move in
                    VStack(alignment: .leading, spacing: 8) {
                        Label {
                            HStack(alignment: .firstTextBaseline, spacing: 8) {
                                Text(move.label).font(.headline)
                                Text(move.summary).font(.caption).foregroundStyle(.secondary)
                            }
                        } icon: {
                            Image(systemName: move.symbol)
                        }
                        ForEach(move.tracks) { pick($0, playing: track) }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: - DJ controls (DJ4)

    private var controls: some View {
        @Bindable var settings = settings
        return VStack(alignment: .leading, spacing: 12) {
            Picker("DJ control", selection: $settings.mode) {
                ForEach(DJSettings.Mode.allCases) { Text($0.label).tag($0) }
            }
            .pickerStyle(.segmented)
            Text(settings.mode.summary).font(.caption).foregroundStyle(.secondary)

            HStack {
                Text("Safe").font(.caption)
                // Re-fetch only when the drag ends, not on every tick.
                Slider(value: $settings.adventurousness, in: 0...1) { editing in
                    if !editing, let track = model?.state?.track { refresh(track, force: false) }
                }
                Text("Bold").font(.caption)
            }
            Toggle("Clean only", isOn: $settings.cleanOnly)
                .font(.subheadline)
                .onChange(of: settings.cleanOnly) {
                    if let track = model?.state?.track { refresh(track, force: false) }
                }
        }
        .padding()
        .background(.quaternary.opacity(0.5), in: RoundedRectangle(cornerRadius: 12))
    }

    private func feedbackButton(_ model: NowPlayingModel, track: Track, more: Bool) -> some View {
        let active = (more ? model.liked : model.disliked).first?.id == track.id
        return Button {
            model.rate(track, more: more)
            refresh(track)
        } label: {
            Label(more ? "More like this" : "Less like this",
                  systemImage: more ? (active ? "hand.thumbsup.fill" : "hand.thumbsup")
                                    : (active ? "hand.thumbsdown.fill" : "hand.thumbsdown"))
                .labelStyle(.iconOnly)
                .font(.title3)
        }
        .accessibilityLabel(more ? "More like this" : "Less like this")
    }

    /// `force` bypasses the cache; settings changes just re-key it.
    private func refresh(_ track: Track, force: Bool = true) {
        guard let suggestions, let model, let queue else { return }
        Task { await suggestions.load(for: track, session: model, queue: queue, settings: settings, force: force) }
    }

    private func pick(_ pick: MoveSuggestions.Pick, playing track: Track) -> some View {
        HStack(alignment: .top, spacing: 12) {
            AsyncImage(url: pick.imageURL) { image in
                image.resizable().aspectRatio(contentMode: .fill)
            } placeholder: {
                RoundedRectangle(cornerRadius: 4).fill(.quaternary)
            }
            .frame(width: 44, height: 44)
            .clipShape(RoundedRectangle(cornerRadius: 4))

            VStack(alignment: .leading, spacing: 2) {
                Text(pick.title).lineLimit(1)
                Text(pick.artistLine).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                Text(pick.reason).font(.caption2).foregroundStyle(.secondary).lineLimit(2)
            }
            Spacer()
            // A visible menu rather than a long-press: discoverable for a host
            // mid-party, and drivable from the Simulator.
            Menu {
                Button("Never suggest this song", systemImage: "nosign") {
                    settings.avoid(AvoidedTrack(id: pick.id, title: pick.title, artist: pick.artists.first ?? ""))
                    refresh(track)
                }
                if let artist = pick.artists.first {
                    Button("Never suggest \(artist)", systemImage: "person.crop.circle.badge.xmark") {
                        settings.avoid(artist: artist)
                        refresh(track)
                    }
                }
            } label: {
                Image(systemName: "ellipsis.circle").font(.title2).foregroundStyle(.secondary)
            }
            .accessibilityLabel("More options for \(pick.title)")
            Button {
                queued.insert(pick.id)
                Task { await queue?.add(pick.queueItem) }
            } label: {
                Image(systemName: queued.contains(pick.id) ? "checkmark.circle.fill" : "plus.circle")
                    .font(.title2)
            }
            .disabled(queued.contains(pick.id))
        }
    }

    private func player(_ model: NowPlayingModel, state: PlaybackState, track: Track) -> some View {
        VStack(spacing: 24) {
            AsyncImage(url: track.imageURL) { image in
                image.resizable().aspectRatio(contentMode: .fit)
            } placeholder: {
                RoundedRectangle(cornerRadius: 12).fill(.quaternary)
            }
            .frame(maxWidth: 260, maxHeight: 260)
            .aspectRatio(1, contentMode: .fit)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .shadow(radius: 12, y: 6)

            VStack(spacing: 4) {
                Text(track.title)
                    .font(.title2.bold())
                    .lineLimit(2)
                Text(track.artistLine)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            .multilineTextAlignment(.center)

            TimelineView(.periodic(from: .now, by: 0.5)) { context in
                let progress = model.progressMs(at: context.date)
                VStack(spacing: 4) {
                    ProgressView(value: Double(progress), total: Double(max(track.durationMs, 1)))
                    HStack {
                        Text(Self.clock(progress))
                        Spacer()
                        Text(track.duration)
                    }
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
                }
            }

            HStack(spacing: 48) {
                control("backward.fill", enabled: state.allows("skipping_prev")) {
                    await model.send(.previous)
                }
                if model.isPlaying {
                    control("pause.circle.fill", size: 64, enabled: state.allows("pausing")) {
                        await model.send(.pause)
                    }
                } else {
                    control("play.circle.fill", size: 64, enabled: state.allows("resuming")) {
                        await model.send(.play)
                    }
                }
                control("forward.fill", enabled: state.allows("skipping_next")) {
                    await model.send(.next)
                }
            }

            HStack {
                feedbackButton(model, track: track, more: false)
                Spacer()
                if let device = state.device {
                    Label(device.name, systemImage: "hifispeaker")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                feedbackButton(model, track: track, more: true)
            }
        }
    }

    private func control(
        _ symbol: String,
        size: CGFloat = 28,
        enabled: Bool,
        action: @escaping () async -> Void
    ) -> some View {
        Button { Task { await action() } } label: {
            Image(systemName: symbol).font(.system(size: size))
        }
        .disabled(!enabled)
    }

    private static func clock(_ ms: Int) -> String {
        let total = ms / 1000
        return String(format: "%d:%02d", total / 60, total % 60)
    }
}
