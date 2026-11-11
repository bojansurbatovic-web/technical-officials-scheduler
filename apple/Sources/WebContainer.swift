import SwiftUI
@preconcurrency import WebKit

#if os(iOS)
struct WebContainer: UIViewRepresentable {
    let model: WebModel
    func makeUIView(context: Context) -> WKWebView { model.webView }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
#else
struct WebContainer: NSViewRepresentable {
    let model: WebModel
    func makeNSView(context: Context) -> WKWebView { model.webView }
    func updateNSView(_ nsView: WKWebView, context: Context) {}
}
#endif
