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
        let type = Self.mime(for: file.pathExtension)
        // Video is read in pieces: answer "Range: bytes=a-b" requests with 206 and just those bytes.
        if let range = urlSchemeTask.request.value(forHTTPHeaderField: "Range"), let r = Self.byteRange(range, size: data.count) {
            let headers = ["Content-Type": type, "Content-Length": String(r.count), "Accept-Ranges": "bytes",
                           "Content-Range": "bytes \(r.lowerBound)-\(r.upperBound - 1)/\(data.count)", "Cache-Control": "no-store"]
            let resp = HTTPURLResponse(url: url, statusCode: 206, httpVersion: "HTTP/1.1", headerFields: headers)!
            urlSchemeTask.didReceive(resp)
            urlSchemeTask.didReceive(data.subdata(in: r))
            urlSchemeTask.didFinish()
            return
        }
        let headers = ["Content-Type": type, "Content-Length": String(data.count), "Accept-Ranges": "bytes", "Cache-Control": "no-store"]
        let resp = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!
        urlSchemeTask.didReceive(resp)
        urlSchemeTask.didReceive(data)
        urlSchemeTask.didFinish()
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {}

    /// "bytes=0-1", "bytes=100-", "bytes=-500" → the byte range inside a file of `size` bytes.
    static func byteRange(_ header: String, size: Int) -> Range<Int>? {
        guard size > 0, header.hasPrefix("bytes="), !header.contains(",") else { return nil }
        let spec = header.dropFirst(6).split(separator: "-", omittingEmptySubsequences: false)
        guard spec.count == 2 else { return nil }
        let a = Int(spec[0].trimmingCharacters(in: .whitespaces)), b = Int(spec[1].trimmingCharacters(in: .whitespaces))
        var lo: Int, hi: Int
        switch (a, b) {
        case let (x?, y?): lo = x; hi = min(y, size - 1)
        case let (x?, nil): lo = x; hi = size - 1
        case let (nil, y?): lo = max(0, size - y); hi = size - 1
        default: return nil
        }
        guard lo >= 0, lo <= hi, lo < size else { return nil }
        return lo..<(hi + 1)
    }

    static func mime(for ext: String) -> String {
        switch ext.lowercased() {
        case "html": return "text/html; charset=utf-8"
        case "js": return "text/javascript; charset=utf-8"
        case "css": return "text/css; charset=utf-8"
        case "json", "webmanifest": return "application/json"
        case "png": return "image/png"
        case "svg": return "image/svg+xml"
        case "jpg", "jpeg": return "image/jpeg"
        case "mp4": return "video/mp4"
        default: return "application/octet-stream"
        }
    }
}
