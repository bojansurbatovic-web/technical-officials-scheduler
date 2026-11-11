import SwiftUI
@preconcurrency import WebKit
import UniformTypeIdentifiers
#if os(iOS)
import UIKit
#else
import AppKit
#endif

/// Hosts the web app and answers its requests (window.webkit.messageHandlers.tos.postMessage → Promise).
@MainActor
final class WebModel: NSObject, ObservableObject, WKScriptMessageHandlerWithReply, WKNavigationDelegate, WKUIDelegate {
    let webView: WKWebView
    private let store = EventStore()
    private var pageReady = false
    private var pendingFiles: [(text: String, name: String)] = []

    override init() {
        let config = WKWebViewConfiguration()
        config.setURLSchemeHandler(LocalScheme(), forURLScheme: LocalScheme.scheme)
        config.websiteDataStore = .default()
        let controller = WKUserContentController()
        config.userContentController = controller
        webView = WKWebView(frame: .zero, configuration: config)
        super.init()
        controller.addScriptMessageHandler(self, contentWorld: .page, name: "tos")
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = false
        #if os(iOS)
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.scrollView.bounces = false
        webView.isOpaque = false
        webView.backgroundColor = .systemGroupedBackground
        webView.scrollView.backgroundColor = .systemGroupedBackground
        #endif
        #if DEBUG
        if #available(iOS 16.4, macOS 13.3, *) { webView.isInspectable = true }
        #endif
        if let url = URL(string: "\(LocalScheme.scheme)://local/index.html") {
            webView.load(URLRequest(url: url))
        }
    }

    // MARK: - Calls from the menu bar / opened files

    func command(_ name: String) {
        let safe = name.filter { $0.isLetter }
        webView.evaluateJavaScript("WTP.App && WTP.App.command('\(safe)')", completionHandler: nil)
    }

    func open(url: URL) {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        guard let data = try? Data(contentsOf: url), let text = String(data: data, encoding: .utf8) else { return }
        if url.path.contains("/Inbox/") { try? FileManager.default.removeItem(at: url) }   // copy made by iOS
        pendingFiles.append((text, url.lastPathComponent))
        flushFiles()
    }

    private func flushFiles() {
        guard pageReady else { return }
        let files = pendingFiles
        pendingFiles.removeAll()
        for f in files {
            guard let json = try? JSONSerialization.data(withJSONObject: [f.text, f.name]),
                  let args = String(data: json, encoding: .utf8) else { continue }
            webView.evaluateJavaScript("WTP.App.openExternal.apply(null, \(args))", completionHandler: nil)
        }
    }

    // MARK: - Messages from the page

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage,
                               replyHandler: @escaping (Any?, String?) -> Void) {
        guard let body = message.body as? [String: Any], let action = body["action"] as? String else {
            replyHandler(nil, "Bad message"); return
        }
        func ok(_ value: Any) { replyHandler(["result": value], nil) }
        let id = (body["id"] as? String) ?? ""
        do {
            switch action {
            case "hello":
                ok(["platform": Self.platformName])
            case "ready":
                pageReady = true
                flushFiles()
                ok(true)
            case "list":
                ok(store.list())
            case "load":
                ok(try store.load(id))
            case "save":
                let meta = (body["meta"] as? [String: Any]) ?? [:]
                try store.save(id, json: (body["json"] as? String) ?? "", meta: meta)
                ok(meta)
            case "delete":
                try store.delete(id)
                ok(true)
            case "share":
                guard let name = body["filename"] as? String, let b64 = body["base64"] as? String,
                      let data = Data(base64Encoded: b64) else { replyHandler(nil, "Nothing to export"); return }
                export(data: data, filename: Self.safeFilename(name)) { result in ok(result) }
            case "copy":
                let text = (body["text"] as? String) ?? ""
                #if os(iOS)
                UIPasteboard.general.string = text
                #else
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(text, forType: .string)
                #endif
                ok(true)
            case "openURL":
                if let s = body["url"] as? String, let url = URL(string: s), url.scheme == "https" { openExternally(url) }
                ok(true)
            default:
                replyHandler(nil, "Unknown action \(action)")
            }
        } catch {
            replyHandler(nil, error.localizedDescription)
        }
    }

    static var platformName: String {
        #if os(macOS)
        return "macos"
        #else
        return UIDevice.current.userInterfaceIdiom == .pad ? "ipados" : "ios"
        #endif
    }

    static func safeFilename(_ name: String) -> String {
        let cleaned = name.components(separatedBy: CharacterSet(charactersIn: "/\\:?%*|\"<>")).joined(separator: "-")
        return cleaned.isEmpty ? "export" : String(cleaned.prefix(120))
    }

    // MARK: - Export: share sheet on iPhone/iPad, save panel on Mac

    private func export(data: Data, filename: String, done: @escaping (String) -> Void) {
        #if os(iOS)
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("export", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent(filename)
        do { try data.write(to: url, options: .atomic) } catch { done("failed"); return }
        let sheet = UIActivityViewController(activityItems: [url], applicationActivities: nil)
        if let pop = sheet.popoverPresentationController {
            pop.sourceView = webView
            pop.sourceRect = CGRect(x: webView.bounds.midX, y: webView.bounds.midY, width: 1, height: 1)
            pop.permittedArrowDirections = []
        }
        sheet.completionWithItemsHandler = { _, completed, _, _ in done(completed ? "shared" : "cancelled") }
        topViewController()?.present(sheet, animated: true)
        #else
        let panel = NSSavePanel()
        panel.nameFieldStringValue = filename
        panel.canCreateDirectories = true
        panel.isExtensionHidden = false
        let finish: (NSApplication.ModalResponse) -> Void = { response in
            guard response == .OK, let url = panel.url else { done("cancelled"); return }
            do { try data.write(to: url, options: .atomic); done("saved") } catch { done("failed") }
        }
        if let window = webView.window { panel.beginSheetModal(for: window, completionHandler: finish) } else { finish(panel.runModal()) }
        #endif
    }

    #if os(iOS)
    private func topViewController() -> UIViewController? {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let window = scenes.flatMap { $0.windows }.first { $0.isKeyWindow } ?? scenes.first?.windows.first
        var top = window?.rootViewController
        while let next = top?.presentedViewController { top = next }
        return top
    }
    #endif

    private func openExternally(_ url: URL) {
        #if os(iOS)
        UIApplication.shared.open(url)
        #else
        NSWorkspace.shared.open(url)
        #endif
    }

    // MARK: - Navigation: only the bundled app runs inside; web links open in the browser

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        if url.scheme == LocalScheme.scheme || url.scheme == "about" || url.scheme == "blob" || url.scheme == "data" {
            decisionHandler(.allow)
        } else {
            if url.scheme == "https" || url.scheme == "mailto" { openExternally(url) }
            decisionHandler(.cancel)
        }
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = navigationAction.request.url, url.scheme == "https" { openExternally(url) }
        return nil
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        pageReady = false
        webView.reload()
    }

    #if os(macOS)
    /// <input type="file"> on the Mac.
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo,
                 completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.json, .plainText, .data]
        if let window = webView.window {
            panel.beginSheetModal(for: window) { completionHandler($0 == .OK ? panel.urls : nil) }
        } else {
            completionHandler(panel.runModal() == .OK ? panel.urls : nil)
        }
    }
    #endif
}
