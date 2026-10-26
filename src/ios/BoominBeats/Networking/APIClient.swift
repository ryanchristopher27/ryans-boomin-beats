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
                // The hosted backend's guard also answers 401; logging in again won't fix that.
                if status == 401, detail?.contains("X-Device-Key") == true {
                    return "The server didn't accept this device's key. Check Device key in Settings."
                }
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

    func get<T: Decodable>(_ path: String, query: [String: String] = [:], headers: [String: String] = [:]) async throws -> T {
        var components = URLComponents(
            url: Config.apiBaseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: false
        )!
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        var request = URLRequest(url: components.url!)
        request.httpMethod = "GET"
        headers.forEach { request.setValue($0.value, forHTTPHeaderField: $0.key) }
        return try await send(request)
    }

    func post<Body: Encodable, T: Decodable>(_ path: String, body: Body) async throws -> T {
        var request = URLRequest(url: Config.apiBaseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return try await send(request)
    }

    /// For callers that need the status and body of a non-2xx answer, such as
    /// sync's 409 (which carries the current document). Throws only for auth and
    /// transport failures.
    func raw(_ method: String, _ path: String, json body: Data? = nil, headers: [String: String] = [:]) async throws -> (status: Int, data: Data) {
        var request = URLRequest(url: Config.apiBaseURL.appendingPathComponent(path))
        request.httpMethod = method
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }
        headers.forEach { request.setValue($0.value, forHTTPHeaderField: $0.key) }
        let (data, http) = try await perform(request)
        return (http.statusCode, data)
    }

    private func send<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, http) = try await perform(request)
        guard (200..<300).contains(http.statusCode) else {
            throw Error.http(status: http.statusCode, detail: Self.detail(from: data))
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw Error.decoding(error)
        }
    }

    private func perform(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        var request = request

        guard let token = await session.validToken() else { throw Error.notAuthenticated }
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        if let deviceKey = Config.deviceKey, !deviceKey.isEmpty {
            request.setValue(deviceKey, forHTTPHeaderField: "X-Device-Key")
        }
        // Harmless on non-LLM routes, which ignore them.
        if let llmKey = Config.llmKey, !llmKey.isEmpty {
            request.setValue(Config.llmProvider, forHTTPHeaderField: "X-LLM-Provider")
            request.setValue(llmKey, forHTTPHeaderField: "X-LLM-Key")
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
        return (data, http)
    }

    /// FastAPI reports errors as {"detail": "..."}; surface that rather than a status code.
    private static func detail(from data: Data) -> String? {
        struct ErrorBody: Decodable { let detail: String? }
        return try? JSONDecoder().decode(ErrorBody.self, from: data).detail
    }
}
