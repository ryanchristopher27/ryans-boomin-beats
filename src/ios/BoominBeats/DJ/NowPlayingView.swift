import SwiftUI

struct NowPlayingView: View {
    @Environment(NowPlayingModel.self) private var model: NowPlayingModel?
    @Environment(QueueStore.self) private var queue: QueueStore?
    @Environment(SuggestionStore.self) private var suggestions: SuggestionStore?
    @Environment(DJSettings.self) private var settings
    @State private var queued: Set<String> = []
    @State private var editingDestination = false
    @State private var destinationDraft = ""

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

            goalRow
        }
        .padding()
        .background(.quaternary.opacity(0.5), in: RoundedRectangle(cornerRadius: 12))
        .alert("Where should the night end up?", isPresented: $editingDestination) {
            TextField("e.g. 90s R&B, or Daft Punk", text: $destinationDraft)
            Button("Set") {
                let text = destinationDraft.trimmingCharacters(in: .whitespaces)
                if !text.isEmpty { setGoal(DJGoal(kind: .destination, destination: text)) }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("The DJ steers one step at a time, so it can change course as the night does.")
        }
    }

    // MARK: - Goal (DJ6)

    @ViewBuilder
    private var goalRow: some View {
        HStack {
            Text("Goal").font(.subheadline)
            Spacer()
            Menu {
                Button("None") { setGoal(nil) }
                Button("Destination…", systemImage: "location.north") {
                    destinationDraft = settings.goal?.destination ?? ""
                    editingDestination = true
                }
                ForEach(DJGoal.Shape.allCases) { shape in
                    Button(shape.label, systemImage: "chart.line.uptrend.xyaxis") {
                        setGoal(DJGoal(kind: .arc, shape: shape, minutes: settings.goal?.minutes ?? 30))
                    }
                }
                Button("Drift", systemImage: "wind") { setGoal(DJGoal(kind: .drift)) }
            } label: {
                Text(settings.goal?.label ?? "None").lineLimit(1)
            }
        }

        if let goal = settings.goal, goal.kind == .arc {
            Picker("Length", selection: Binding(
                get: { goal.minutes },
                set: { settings.goal?.minutes = $0; refreshCurrent() }
            )) {
                ForEach(DJGoal.arcLengths, id: \.self) { Text("\($0) min").tag($0) }
            }
            .pickerStyle(.segmented)
            TimelineView(.periodic(from: .now, by: 30)) { _ in
                Text("\(min(Int(goal.elapsedMinutes), goal.minutes)) of \(goal.minutes) min")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func setGoal(_ goal: DJGoal?) {
        settings.goal = goal
        refreshCurrent()
    }

    private func refreshCurrent() {
        if let track = model?.state?.track { refresh(track, force: false) }
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
