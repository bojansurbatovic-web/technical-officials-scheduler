import Foundation
import SwiftUI

/// Once a day, in the background, asks the App Store whether a newer version of this app is live and, if so, shows a
/// small banner with an "Update" button that opens the app's App Store page. Sends nothing about the user: it is one
/// public App Store lookup by bundle ID (fallback: www.trisport.me/versions.json). Silent when offline.
enum UpdateChecker {
    struct Update: Equatable {
        let version: String
        let url: URL
    }

    static let manifest = URL(string: "https://www.trisport.me/versions.json")!
    private static let defaults = UserDefaults.standard
    private static let day: TimeInterval = 24 * 3600

    static var currentVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0"
    }

    /// "1.10" > "1.9", "1.3" == "1.3.0"
    static func isNewer(_ latest: String, than current: String) -> Bool {
        func parts(_ v: String) -> [Int] {
            let p = v.split(separator: ".").map { Int($0.filter(\.isNumber)) ?? 0 }
            return p + Array(repeating: 0, count: max(0, 4 - p.count))
        }
        let a = parts(latest), b = parts(current)
        for (x, y) in zip(a, b) where x != y { return x > y }
        return false
    }

    /// The newer version, or nil (none, skipped with "Not now", checked less than a day ago, or offline).
    /// `appKey` is the app's entry in versions.json ("trianatomy", "triofficial", "tricarbon", "scheduler").
    static func check(appKey: String, force: Bool = false) async -> Update? {
        let now = Date().timeIntervalSince1970
        var latest: Update?
        if !force, now - defaults.double(forKey: "updateCheck.last") < day {
            if let v = defaults.string(forKey: "updateCheck.version"),
               let u = defaults.string(forKey: "updateCheck.url").flatMap(URL.init(string:)) {
                latest = Update(version: v, url: u)
            }
        } else {
            latest = await lookupAppStore()
            if latest == nil { latest = await lookupManifest(appKey: appKey) }
            guard let found = latest else { return nil }  // offline: try again next launch
            defaults.set(now, forKey: "updateCheck.last")
            defaults.set(found.version, forKey: "updateCheck.version")
            defaults.set(found.url.absoluteString, forKey: "updateCheck.url")
        }
        guard let l = latest, isNewer(l.version, than: currentVersion) else { return nil }
        if !force, defaults.string(forKey: "updateCheck.dismissed") == l.version { return nil }
        return l
    }

    static func dismiss(_ update: Update) {
        defaults.set(update.version, forKey: "updateCheck.dismissed")
    }

    private static func get(_ url: URL) async -> Any? {
        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 10)
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        guard let (data, resp) = try? await URLSession.shared.data(for: req),
              (resp as? HTTPURLResponse)?.statusCode == 200 else { return nil }
        return try? JSONSerialization.jsonObject(with: data)
    }

    private static func lookupAppStore() async -> Update? {
        guard let bundleID = Bundle.main.bundleIdentifier else { return nil }
        var c = URLComponents(string: "https://itunes.apple.com/lookup")!
        c.queryItems = [URLQueryItem(name: "bundleId", value: bundleID),
                        URLQueryItem(name: "country", value: Locale.current.region?.identifier.lowercased() ?? "us")]
        #if os(macOS)
        c.queryItems?.append(URLQueryItem(name: "entity", value: "macSoftware"))
        #endif
        c.queryItems?.append(URLQueryItem(name: "t", value: String(Int(Date().timeIntervalSince1970 / 3600))))
        guard let url = c.url, let json = await get(url) as? [String: Any],
              let first = (json["results"] as? [[String: Any]])?.first,
              let version = first["version"] as? String,
              let page = (first["trackViewUrl"] as? String).flatMap(URL.init(string:)) else { return nil }
        return Update(version: version, url: page)
    }

    private static func lookupManifest(appKey: String) async -> Update? {
        #if os(macOS)
        let platform = "mac"
        #else
        let platform = "ios"
        #endif
        guard let json = await get(manifest) as? [String: Any],
              let app = (json["apps"] as? [String: Any])?[appKey] as? [String: Any],
              let entry = app[platform] as? [String: Any],
              let version = entry["version"] as? String,
              let url = (entry["url"] as? String).flatMap(URL.init(string:)) else { return nil }
        return Update(version: version, url: url)
    }
}

/// A thin banner at the top of the screen: "Version X is available." [Update] [Not now].
/// `tr` translates the English texts (apps with their own localisation pass their L function).
struct UpdateBanner: ViewModifier {
    let appKey: String
    var tr: (String) -> String = { $0 }
    @State private var update: UpdateChecker.Update?
    @Environment(\.openURL) private var openURL

    func body(content: Content) -> some View {
        content
            .safeAreaInset(edge: .top, spacing: 0) {
                if let u = update {
                    HStack(spacing: 10) {
                        Image(systemName: "arrow.down.app.fill").imageScale(.large)
                        Text(tr("Version {v} is available.").replacingOccurrences(of: "{v}", with: u.version))
                            .font(.subheadline.weight(.semibold))
                            .frame(maxWidth: .infinity, alignment: .leading)
                        Button(tr("Update")) { openURL(u.url) }
                            .buttonStyle(.borderedProminent)
                            .tint(.white).foregroundStyle(.blue)
                            .controlSize(.small)
                        Button {
                            UpdateChecker.dismiss(u)
                            withAnimation { update = nil }
                        } label: {
                            Image(systemName: "xmark").font(.footnote.weight(.bold))
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(tr("Not now"))
                    }
                    .foregroundStyle(.white)
                    .padding(.horizontal, 14).padding(.vertical, 9)
                    .background(Color.blue)
                    .transition(.move(edge: .top).combined(with: .opacity))
                }
            }
            .task {
                if ProcessInfo.processInfo.arguments.contains("-UITests")
                    || ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil { return }
                try? await Task.sleep(nanoseconds: 2_000_000_000)
                let found = await UpdateChecker.check(appKey: appKey)
                withAnimation { update = found }
            }
    }
}

extension View {
    /// Shows an "Update available" banner when the App Store has a newer version (checked at most once a day).
    func updateBanner(appKey: String, tr: @escaping (String) -> String = { $0 }) -> some View {
        modifier(UpdateBanner(appKey: appKey, tr: tr))
    }
}
