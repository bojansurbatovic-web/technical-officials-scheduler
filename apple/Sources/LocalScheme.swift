import Foundation
@preconcurrency import WebKit

/// Serves the bundled web app from tos-app://local/… so it runs with a normal origin
/// (scripts, storage and the Content-Security-Policy behave as on a web server). Nothing is loaded from the network.
final class LocalScheme: NSObject, WKURLSchemeHandler {
    static let scheme = "tos-app"
    private let root: URL? = Bundle.main.url(forResource: "web", withExtension: nil)?.standardizedFileURL

    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        guard let url = urlSchemeTask.request.url, let root = root else {
            urlSchemeTask.didFailWithError(URLError(.fileDoesNotExist)); return
        }
        var path = url.path
        if path.isEmpty || path == "/" { path = "/index.html" }
        let file = root.appendingPathComponent(String(path.dropFirst())).standardizedFileURL
        guard file.path.hasPrefix(root.path + "/"), let data = try? Data(contentsOf: file) else {
            let resp = HTTPURLResponse(url: url, statusCode: 404, httpVersion: "HTTP/1.1", headerFields: ["Content-Type": "text/plain"])!
            urlSchemeTask.didReceive(resp)
            urlSchemeTask.didReceive(Data("Not found".utf8))
            urlSchemeTask.didFinish()
            return
        }
        let headers = ["Content-Type": Self.mime(for: file.pathExtension), "Content-Length": String(data.count), "Cache-Control": "no-store"]
        let resp = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!
        urlSchemeTask.didReceive(resp)
        urlSchemeTask.didReceive(data)
        urlSchemeTask.didFinish()
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {}

    static func mime(for ext: String) -> String {
        switch ext.lowercased() {
        case "html": return "text/html; charset=utf-8"
        case "js": return "text/javascript; charset=utf-8"
        case "css": return "text/css; charset=utf-8"
        case "json", "webmanifest": return "application/json"
        case "png": return "image/png"
        case "svg": return "image/svg+xml"
        default: return "application/octet-stream"
        }
    }
}
