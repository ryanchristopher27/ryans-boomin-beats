import Foundation

/// Thin URLSession client for the Boomin Beats backend.
///
/// Hand-rolled rather than generated from the OpenAPI schema: ten endpoints don't
/// justify a codegen build step, and this keeps the Xcode project dependency-free.
///
/// Auth mirrors what the backend now expects after K1/D1:
///   Authorization: Bearer <spotify token>   — services/spotify_auth.py
///   X-Device-Key: <secret>                  — hosted instance guard, D1.1
///   X-LLM-Provider / X-LLM-Key              — BYOK, services/llm_auth.py
struct APIClient {
    enum Error: Swift.Error, LocalizedError {
        case notAuthenticated
        case http(status: Int, detail: String?)
        case decoding(Swift.Error)
        case transport(Swift.Error)

        var errorDescription: String? {
            switch self {
            case .notAuthenticated:
                return "Log in to Spotify first."
            case let .http(status, detail):
                if status == 401 { return "Session expired. Log in again." }
                return detail ?? "Request failed (\(status))."
            case let .decoding(error):
                return "Unexpected response: \(error.localizedDescription)"
            case let .transport(error):
                return error.localizedDescription
            }
        }
    }

    private let session: SpotifySession

    init(session: SpotifySession) {
        self.session = session
    }

    // MARK: - Requests

    func get<T: Decodable>(_ path: String, query: [String: String] = [:]) async throws -> T {
        var components = URLComponents(
            url: Config.apiBaseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: false
        )!
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        var request = URLRequest(url: components.url!)
        request.httpMethod = "GET"
        return try await send(request)
    }

    func post<Body: Encodable, T: Decodable>(_ path: String, body: Body) async throws -> T {
        var request = URLRequest(url: Config.apiBaseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return try await send(request)
    }

    private func send<T: Decodable>(_ request: URLRequest) async throws -> T {
        var request = request

        guard let token = await session.validToken() else { throw Error.notAuthenticated }
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        if let deviceKey = Config.deviceKey, !deviceKey.isEmpty {
            request.setValue(deviceKey, forHTTPHeaderField: "X-Device-Key")
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw Error.transport(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw Error.http(status: -1, detail: nil)
        }
        guard (200..<300).contains(http.statusCode) else {
            throw Error.http(status: http.statusCode, detail: Self.detail(from: data))
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw Error.decoding(error)
        }
    }

    /// FastAPI reports errors as {"detail": "..."}; surface that rather than a status code.
    private static func detail(from data: Data) -> String? {
        struct ErrorBody: Decodable { let detail: String? }
        return try? JSONDecoder().decode(ErrorBody.self, from: data).detail
    }
}
