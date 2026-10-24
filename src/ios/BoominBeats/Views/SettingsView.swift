import SwiftUI

/// App-wide light/dark override. `system` follows the phone's setting, which
/// the app already did before this existed; the override lets a host keep the
/// app dark at a party with the phone on Light.
enum Appearance: String, CaseIterable, Identifiable {
    case system, light, dark

    static let storageKey = "appearance"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .system: return "System"
        case .light: return "Light"
        case .dark: return "Dark"
        }
    }

    var colorScheme: ColorScheme? {
        switch self {
        case .system: return nil
        case .light: return .light
        case .dark: return .dark
        }
    }
}

/// API host + device key entry.
///
/// The base URL is configurable rather than compiled in because the same build has
/// to reach two deployments: the Mac during development and the hosted instance
/// later (the "one codebase, two deployments" decision in docs/plan.md). The
/// default, 127.0.0.1, only works in the Simulator — on a physical device that
/// address means the phone itself, so a LAN IP is required.
struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    // Optional: Settings is also reachable from the login screen, outside MainTabs.
    @Environment(DJSettings.self) private var dj: DJSettings?

    @State private var host: String = Config.apiBaseURL.absoluteString
    @State private var deviceKey: String = Config.deviceKey ?? ""
    @State private var probe: ProbeState = .idle
    // Applies immediately, like iOS's own appearance setting, rather than on Save.
    @AppStorage(Appearance.storageKey) private var appearance: Appearance = .system
    @State private var bufferDepth = Config.backgroundBufferDepth
    @State private var llmProvider = Config.llmProvider
    @State private var llmKey = Config.llmKey ?? ""

    enum ProbeState: Equatable {
        case idle
        case checking
        case ok(String)
        case failed(String)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Appearance") {
                    Picker("Appearance", selection: $appearance) {
                        ForEach(Appearance.allCases) { Text($0.label).tag($0) }
                    }
                    .pickerStyle(.segmented)
                }

                Section {
                    TextField("http://192.168.1.x:8005", text: $host)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .font(.body.monospaced())
                } header: {
                    Text("API Host")
                } footer: {
                    Text("The Simulator can reach 127.0.0.1 on your Mac. A physical device needs your Mac's LAN address, or the hosted URL.")
                }

                Section {
                    SecureField("Leave empty for local", text: $deviceKey)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                } header: {
                    Text("Device Key")
                } footer: {
                    Text("Required by the hosted instance only. The local backend ignores it. Stored in the Keychain.")
                }

                Section {
                    Button {
                        Task { await check() }
                    } label: {
                        HStack {
                            Text("Test Connection")
                            Spacer()
                            switch probe {
                            case .idle:
                                EmptyView()
                            case .checking:
                                ProgressView()
                            case .ok:
                                Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                            case .failed:
                                Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
                            }
                        }
                    }
                    .disabled(probe == .checking || URL(string: host) == nil)

                    switch probe {
                    case let .ok(message), let .failed(message):
                        Text(message).font(.footnote).foregroundStyle(.secondary)
                    default:
                        EmptyView()
                    }
                }

                Section {
                    Picker("Provider", selection: $llmProvider) {
                        ForEach(Config.llmProviders, id: \.self) { Text($0.capitalized).tag($0) }
                    }
                    SecureField("API key", text: $llmKey)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                } header: {
                    Text("AI")
                } footer: {
                    Text("Your own key, used for DJ suggestions. Stored in the Keychain and sent only to the Boomin Beats backend.")
                }

                Section {
                    Stepper("\(bufferDepth) tracks", value: $bufferDepth, in: Config.bufferDepthRange)
                } header: {
                    Text("Queue When Backgrounded")
                } footer: {
                    Text("While the app is open, one track is sent ahead to Spotify so the rest of the queue stays editable. When you leave the app, this many are sent so music keeps playing.")
                }

                if let dj, !(dj.avoidTracks.isEmpty && dj.avoidArtists.isEmpty) {
                    Section {
                        ForEach(dj.avoidArtists, id: \.self) { Label($0, systemImage: "person.crop.circle.badge.xmark") }
                            .onDelete { dj.removeArtists(at: $0) }
                        ForEach(dj.avoidTracks) { t in
                            Label("\(t.title) — \(t.artist)", systemImage: "nosign")
                        }
                        .onDelete { dj.removeTracks(at: $0) }
                    } header: {
                        Text("Do Not Play")
                    } footer: {
                        Text("The DJ never suggests these. Swipe to remove. Tap ⋯ on a suggestion to add more.")
                    }
                }
            }
            .navigationTitle("Settings")
            // A sheet keeps its own appearance; mirror the choice so the change shows here at once.
            .preferredColorScheme(appearance.colorScheme)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save(); dismiss() }
                        .disabled(URL(string: host) == nil)
                }
            }
        }
    }

    private func save() {
        if let url = URL(string: host.trimmingCharacters(in: .whitespaces)) {
            Config.apiBaseURL = url
        }
        Config.deviceKey = deviceKey.trimmingCharacters(in: .whitespaces)
        Config.backgroundBufferDepth = bufferDepth
        Config.llmProvider = llmProvider
        Config.llmKey = llmKey.trimmingCharacters(in: .whitespaces)
    }

    /// Hits the unguarded root endpoint, which answers without a Spotify token and
    /// without a device key — so a failure here is genuinely connectivity, not auth.
    private func check() async {
        probe = .checking
        guard let url = URL(string: host.trimmingCharacters(in: .whitespaces)) else {
            probe = .failed("That isn't a valid URL.")
            return
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 8
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                probe = .failed("No response.")
                return
            }
            let body = String(data: data, encoding: .utf8) ?? ""
            if http.statusCode == 200, body.contains("\"status\"") {
                probe = .ok("Reached the Boomin Beats API.")
            } else {
                probe = .failed("Responded \(http.statusCode), but this doesn't look like the API.")
            }
        } catch {
            probe = .failed(error.localizedDescription)
        }
    }
}

#Preview {
    SettingsView()
}
