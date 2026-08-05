import SwiftUI

/// API host + device key entry.
///
/// The base URL is configurable rather than compiled in because the same build has
/// to reach two deployments: the Mac during development and the hosted instance
/// later (the "one codebase, two deployments" decision in docs/plan.md). The
/// default, 127.0.0.1, only works in the Simulator — on a physical device that
/// address means the phone itself, so a LAN IP is required.
struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss

    @State private var host: String = Config.apiBaseURL.absoluteString
    @State private var deviceKey: String = Config.deviceKey ?? ""
    @State private var probe: ProbeState = .idle

    enum ProbeState: Equatable {
        case idle
        case checking
        case ok(String)
        case failed(String)
    }

    var body: some View {
        NavigationStack {
            Form {
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
            }
            .navigationTitle("Settings")
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
