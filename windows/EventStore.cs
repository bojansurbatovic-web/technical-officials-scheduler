using System.Text.Json.Nodes;

namespace TOScheduler;

/// <summary>
/// Every event is a .wtplan.json file in Documents\Technical Officials Scheduler\Events – the same file format
/// as the web, Apple and Ubuntu versions. A small index keeps the names and dates for the calendar.
/// </summary>
sealed class EventStore
{
    public readonly string Folder;
    string IndexPath => Path.Combine(Folder, ".index.json");
    const string Ext = ".wtplan.json";

    public EventStore()
    {
        var docs = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        if (string.IsNullOrEmpty(docs)) docs = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        Folder = Path.Combine(docs, "Technical Officials Scheduler", "Events");
        Directory.CreateDirectory(Folder);
    }

    string FilePath(string id)
    {
        bool ok = id.Length > 0 && id.Length < 120 && id.All(c => char.IsLetterOrDigit(c) || c == '-' || c == '_');
        if (!ok) throw new InvalidOperationException("Invalid event id");
        return Path.Combine(Folder, id + Ext);
    }

    static string Str(JsonNode? node, string key)
    {
        try { return node is JsonObject o && o[key] is JsonValue v && v.TryGetValue<string>(out var s) ? s : ""; }
        catch { return ""; }
    }

    static void WriteAtomic(string path, string text)
    {
        var tmp = path + ".tmp";
        File.WriteAllText(tmp, text);
        File.Move(tmp, path, true);
    }

    List<JsonNode> ReadIndex()
    {
        try
        {
            if (JsonNode.Parse(File.ReadAllText(IndexPath)) is JsonArray arr)
                return arr.Where(x => x is JsonObject).Select(x => x!.DeepClone()).ToList();
        }
        catch { /* no index yet, or damaged: rebuilt from the files */ }
        return new List<JsonNode>();
    }

    void WriteIndex(IEnumerable<JsonNode> items) =>
        WriteAtomic(IndexPath, new JsonArray(items.Select(x => (JsonNode?)x.DeepClone()).ToArray()).ToJsonString());

    /// <summary>Index entries for the files that exist; files copied into the folder get an entry read from the file.</summary>
    public JsonArray List()
    {
        var ids = Directory.EnumerateFiles(Folder, "*" + Ext)
            .Select(p => Path.GetFileName(p))
            .Where(n => !n.StartsWith('.') && n.EndsWith(Ext, StringComparison.OrdinalIgnoreCase))
            .Select(n => n[..^Ext.Length])
            .ToHashSet();
        var index = ReadIndex().Where(x => ids.Contains(Str(x, "id"))).ToList();
        var known = index.Select(x => Str(x, "id")).ToHashSet();
        foreach (var id in ids.Where(i => !known.Contains(i)))
        {
            try { index.Add(Meta(File.ReadAllText(FilePath(id)), id)); } catch { /* not one of ours */ }
        }
        try { WriteIndex(index); } catch { /* read-only folder: the list still works */ }
        var sorted = index.OrderByDescending(x => Str(x, "updated"), StringComparer.Ordinal).Select(x => (JsonNode?)x.DeepClone());
        return new JsonArray(sorted.ToArray());
    }

    public string Load(string id)
    {
        var path = FilePath(id);
        if (!File.Exists(path)) throw new InvalidOperationException("Event not found");
        return File.ReadAllText(path);
    }

    public void Save(string id, string json, JsonObject meta)
    {
        WriteAtomic(FilePath(id), json);
        var index = ReadIndex().Where(x => Str(x, "id") != id).ToList();
        var m = (JsonObject)meta.DeepClone();
        m["id"] = id;
        index.Add(m);
        WriteIndex(index);
    }

    public void Delete(string id)
    {
        var path = FilePath(id);
        if (File.Exists(path)) File.Delete(path);
        WriteIndex(ReadIndex().Where(x => Str(x, "id") != id));
    }

    static JsonObject Meta(string text, string id)
    {
        var m = new JsonObject
        {
            ["id"] = id, ["name"] = "Event", ["venue"] = "", ["dates"] = new JsonArray(),
            ["races"] = 0, ["officials"] = 0, ["updated"] = ""
        };
        try
        {
            if (JsonNode.Parse(text) is not JsonObject obj) return m;
            var ev = obj["event"] as JsonObject;
            if (ev?["name"] is JsonValue) m["name"] = Str(ev, "name");
            m["venue"] = Str(ev, "venue");
            var races = obj["races"] as JsonArray ?? new JsonArray();
            var evDate = Str(ev, "date");
            var dates = races.Select(r => { var d = Str(r, "date"); return d == "" ? evDate : d; })
                .Where(d => d != "").Distinct().OrderBy(d => d, StringComparer.Ordinal)
                .Select(d => (JsonNode?)JsonValue.Create(d)).ToArray();
            m["dates"] = new JsonArray(dates);
            m["races"] = races.Count;
            m["officials"] = (obj["officials"] as JsonArray)?.Count ?? 0;
        }
        catch { /* keep the defaults */ }
        return m;
    }
}
