import Foundation

/// Every event is a .wtplan.json file in Documents/Events (visible in the Files app on iPhone and iPad).
/// A small hidden index keeps the names and dates for the calendar.
struct EventStore {
    enum StoreError: LocalizedError {
        case badId, notFound
        var errorDescription: String? { self == .badId ? "Invalid event id" : "Event not found" }
    }

    let folder: URL
    private var indexURL: URL { folder.appendingPathComponent(".index.json") }

    init() {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        folder = docs.appendingPathComponent("Events", isDirectory: true)
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    }

    private func fileURL(_ id: String) throws -> URL {
        let ok = !id.isEmpty && id.count < 120 && id.allSatisfy { $0.isLetter || $0.isNumber || $0 == "-" || $0 == "_" }
        guard ok else { throw StoreError.badId }
        return folder.appendingPathComponent(id + ".wtplan.json")
    }

    private func readIndex() -> [[String: Any]] {
        guard let data = try? Data(contentsOf: indexURL),
              let arr = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] else { return [] }
        return arr
    }

    private func writeIndex(_ items: [[String: Any]]) throws {
        let data = try JSONSerialization.data(withJSONObject: items, options: [])
        try data.write(to: indexURL, options: .atomic)
    }

    /// Index entries for the files that exist; files added in the Files app get an entry read from the file.
    func list() -> [[String: Any]] {
        let names = (try? FileManager.default.contentsOfDirectory(atPath: folder.path)) ?? []
        let ids = names.filter { $0.hasSuffix(".wtplan.json") && !$0.hasPrefix(".") }.map { String($0.dropLast(".wtplan.json".count)) }
        var index = readIndex().filter { ids.contains(($0["id"] as? String) ?? "") }
        let known = Set(index.compactMap { $0["id"] as? String })
        for id in ids where !known.contains(id) {
            if let url = try? fileURL(id), let data = try? Data(contentsOf: url) { index.append(Self.meta(from: data, id: id)) }
        }
        try? writeIndex(index)
        return index.sorted { (($0["updated"] as? String) ?? "") > (($1["updated"] as? String) ?? "") }
    }

    func load(_ id: String) throws -> String {
        let url = try fileURL(id)
        guard let data = try? Data(contentsOf: url), let text = String(data: data, encoding: .utf8) else { throw StoreError.notFound }
        return text
    }

    func save(_ id: String, json: String, meta: [String: Any]) throws {
        try Data(json.utf8).write(to: try fileURL(id), options: .atomic)
        var index = readIndex().filter { ($0["id"] as? String) != id }
        var m = meta
        m["id"] = id
        index.append(m)
        try writeIndex(index)
    }

    func delete(_ id: String) throws {
        let url = try fileURL(id)
        if FileManager.default.fileExists(atPath: url.path) { try FileManager.default.removeItem(at: url) }
        try writeIndex(readIndex().filter { ($0["id"] as? String) != id })
    }

    static func meta(from data: Data, id: String) -> [String: Any] {
        var m: [String: Any] = ["id": id, "name": "Event", "venue": "", "dates": [String](), "races": 0, "officials": 0, "updated": ""]
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return m }
        let event = obj["event"] as? [String: Any] ?? [:]
        m["name"] = (event["name"] as? String) ?? "Event"
        m["venue"] = (event["venue"] as? String) ?? ""
        let races = obj["races"] as? [[String: Any]] ?? []
        let evDate = (event["date"] as? String) ?? ""
        let dates = Set(races.map { r -> String in
            let d = (r["date"] as? String) ?? ""
            return d.isEmpty ? evDate : d
        }.filter { !$0.isEmpty })
        m["dates"] = dates.sorted()
        m["races"] = races.count
        m["officials"] = (obj["officials"] as? [Any])?.count ?? 0
        return m
    }
}
