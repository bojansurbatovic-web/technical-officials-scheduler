using System.Diagnostics;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace TOScheduler;

/// <summary>The app window: hosts the planner and answers its requests (same protocol as the Apple apps).</summary>
sealed class MainForm : Form
{
    const string Host = "app.tos-scheduler.example";        // served from the app's own "web" folder, never the network
    static readonly string StartUrl = $"https://{Host}/index.html";
    static readonly string AppData = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Technical Officials Scheduler");

    readonly WebView2 web = new() { Dock = DockStyle.Fill };
    readonly EventStore store = new();
    readonly List<(string Text, string Name)> pendingFiles = new();
    /// <summary>Set TOS_SELFCHECK to a file path to have the app write whether the planner page started.</summary>
    readonly string? selfCheck = Environment.GetEnvironmentVariable("TOS_SELFCHECK");
    bool pageReady, mayClose;
    int contentCrashes;

    public MainForm(string[] args)
    {
        Text = "Technical Officials Scheduler";
        using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream("app.ico"))
            if (s != null) Icon = new Icon(s);
        BackColor = Color.FromArgb(244, 245, 247);
        web.DefaultBackgroundColor = BackColor;
        Controls.Add(web);
        PlaceWindow();
        foreach (var a in args)
            if (File.Exists(a)) QueueFile(a);
        Load += async (_, _) => await StartAsync();
        FormClosing += OnFormClosing;
    }

    // ------------------------------------------------------------------ start-up

    async Task StartAsync()
    {
        try
        {
            Directory.CreateDirectory(AppData);
            var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(AppData, "WebView2"));
            await web.EnsureCoreWebView2Async(env);
        }
        catch (WebView2RuntimeNotFoundException)
        {
            Report("NO-WEBVIEW2");
            var answer = MessageBox.Show(this,
                "Technical Officials Scheduler needs the Microsoft Edge WebView2 Runtime, which is not installed on this PC.\n\nOpen the download page now?",
                Text, MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
            if (answer == DialogResult.Yes) OpenExternally("https://developer.microsoft.com/microsoft-edge/webview2/");
            mayClose = true; Close();
            return;
        }
        catch (Exception ex)
        {
            Report("START-ERROR " + ex.Message);
            MessageBox.Show(this, "The app could not start:\n\n" + ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
            mayClose = true; Close();
            return;
        }

        var core = web.CoreWebView2;
        var set = core.Settings;
        set.AreDevToolsEnabled = false;
        set.AreBrowserAcceleratorKeysEnabled = false;   // no F5 / Ctrl+P / Ctrl+F browser behaviour; the page handles its own keys
        set.IsStatusBarEnabled = false;
        set.IsPasswordAutosaveEnabled = false;
        set.IsGeneralAutofillEnabled = false;
        set.IsZoomControlEnabled = true;
        core.SetVirtualHostNameToFolderMapping(Host, Path.Combine(AppContext.BaseDirectory, "web"), CoreWebView2HostResourceAccessKind.DenyCors);
        await core.AddScriptToExecuteOnDocumentCreatedAsync(ReadResource("bridge.js"));
        core.WebMessageReceived += OnMessage;
        core.NavigationStarting += OnNavigationStarting;
        core.NewWindowRequested += (_, e) => { e.Handled = true; if (IsExternal(e.Uri)) OpenExternally(e.Uri); };
        core.NavigationCompleted += (_, e) =>
        {
            if (!e.IsSuccess && e.WebErrorStatus != CoreWebView2WebErrorStatus.OperationCanceled) ShowLoadError(e.WebErrorStatus.ToString());
        };
        core.ProcessFailed += OnProcessFailed;
        core.ContextMenuRequested += OnContextMenu;
        core.Navigate(StartUrl);
        if (selfCheck != null)
        {
            _ = Task.Delay(30000).ContinueWith(_ => { if (!pageReady) Report("TIMEOUT page did not start"); });
        }
    }

    static string ReadResource(string name)
    {
        using var s = Assembly.GetExecutingAssembly().GetManifestResourceStream(name)
                      ?? throw new InvalidOperationException("Missing resource " + name);
        using var r = new StreamReader(s);
        return r.ReadToEnd();
    }

    void Report(string line)
    {
        if (selfCheck == null) return;
        try { File.AppendAllText(selfCheck, "TOS-SELFCHECK " + line + Environment.NewLine); } catch { /* ignore */ }
    }

    // ------------------------------------------------------------------ messages from the page

    async void OnMessage(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        if (!e.Source.StartsWith($"https://{Host}/", StringComparison.OrdinalIgnoreCase)) return;
        JsonObject? root;
        try { root = JsonNode.Parse(e.WebMessageAsJson) as JsonObject; } catch { return; }
        if (root == null || root["__tos"] is not JsonValue idValue || !idValue.TryGetValue<double>(out var id)) return;
        var msg = root["msg"] as JsonObject ?? new JsonObject();
        var reply = new JsonObject { ["__tos"] = id };
        try { reply["result"] = await HandleAction(msg); }
        catch (Exception ex) { reply["error"] = ex.Message; }
        try { web.CoreWebView2?.PostWebMessageAsJson(reply.ToJsonString()); } catch { /* window closing */ }
    }

    static string Str(JsonObject o, string key) =>
        o[key] is JsonValue v && v.TryGetValue<string>(out var s) ? s : "";

    async Task<JsonNode?> HandleAction(JsonObject msg)
    {
        var id = Str(msg, "id");
        switch (Str(msg, "action"))
        {
            case "hello":
                return new JsonObject { ["platform"] = "windows" };
            case "ready":
                pageReady = true;
                contentCrashes = 0;
                FlushFiles();
                if (selfCheck != null) _ = ReportReady();
                return true;
            case "list":
                return store.List();
            case "load":
                return store.Load(id);
            case "save":
                var meta = msg["meta"] as JsonObject ?? new JsonObject();
                store.Save(id, Str(msg, "json"), meta);
                return meta.DeepClone();
            case "delete":
                store.Delete(id);
                return true;
            case "share":
                var name = Str(msg, "filename");
                byte[] data;
                try { data = Convert.FromBase64String(Str(msg, "base64")); }
                catch { throw new InvalidOperationException("Nothing to export"); }
                await Task.Yield();
                return SaveAs(data, SafeFilename(name));
            case "copy":
                var text = Str(msg, "text");
                if (text.Length == 0) Clipboard.Clear(); else Clipboard.SetText(text);
                return true;
            case "openURL":
                var url = Str(msg, "url");
                if (url.StartsWith("https://", StringComparison.OrdinalIgnoreCase)) OpenExternally(url);
                return true;
            default:
                throw new InvalidOperationException("Unknown action " + Str(msg, "action"));
        }
    }

    async Task ReportReady()
    {
        try
        {
            var js = "document.querySelectorAll('*').length + ' elements | ' + document.title + ' | ' + " +
                     "(document.body.innerText || '').replace(/\\s+/g, ' ').slice(0, 160)";
            var value = await web.CoreWebView2.ExecuteScriptAsync(js);
            Report("READY " + (JsonSerializer.Deserialize<string>(value) ?? value));
        }
        catch (Exception ex) { Report("READY (summary failed: " + ex.Message + ")"); }
    }

    static string SafeFilename(string name)
    {
        var cleaned = string.Join("-", name.Split(Path.GetInvalidFileNameChars().Concat(new[] { '%', '*' }).ToArray()));
        return cleaned.Length == 0 ? "export" : cleaned[..Math.Min(cleaned.Length, 120)];
    }

    /// <summary>Export: the standard Save As dialog.</summary>
    string SaveAs(byte[] data, string filename)
    {
        var ext = Path.GetExtension(filename).TrimStart('.');
        using var dlg = new SaveFileDialog
        {
            FileName = filename,
            Filter = (ext.Length > 0 ? $"{ext.ToUpperInvariant()} file (*.{ext})|*.{ext}|" : "") + "All files (*.*)|*.*",
            DefaultExt = ext,
            AddExtension = true,
            OverwritePrompt = true,
            Title = "Export",
        };
        if (dlg.ShowDialog(this) != DialogResult.OK) return "cancelled";
        try { File.WriteAllBytes(dlg.FileName, data); return "saved"; }
        catch { return "failed"; }
    }

    // ------------------------------------------------------------------ files opened with the app

    void QueueFile(string path)
    {
        try
        {
            var info = new FileInfo(path);
            if (info.Length > 50_000_000) return;
            pendingFiles.Add((File.ReadAllText(path), info.Name));
        }
        catch { /* unreadable: ignore */ }
    }

    void FlushFiles()
    {
        if (!pageReady || web.CoreWebView2 == null) return;
        foreach (var f in pendingFiles)
        {
            var args = JsonSerializer.Serialize(new[] { f.Text, f.Name });
            _ = web.CoreWebView2.ExecuteScriptAsync($"WTP.App.openExternal.apply(null, {args})");
        }
        pendingFiles.Clear();
    }

    // ------------------------------------------------------------------ navigation: only the bundled app runs inside

    static bool IsInternal(string uri) =>
        uri.StartsWith($"https://{Host}/", StringComparison.OrdinalIgnoreCase) ||
        uri.StartsWith("about:", StringComparison.OrdinalIgnoreCase) ||
        uri.StartsWith("data:", StringComparison.OrdinalIgnoreCase) ||
        uri.StartsWith("blob:", StringComparison.OrdinalIgnoreCase);

    static bool IsExternal(string uri) =>
        uri.StartsWith("https://", StringComparison.OrdinalIgnoreCase) || uri.StartsWith("mailto:", StringComparison.OrdinalIgnoreCase);

    void OnNavigationStarting(object? sender, CoreWebView2NavigationStartingEventArgs e)
    {
        if (IsInternal(e.Uri)) return;
        e.Cancel = true;
        if (IsExternal(e.Uri)) OpenExternally(e.Uri);
    }

    static void OpenExternally(string uri)
    {
        try { Process.Start(new ProcessStartInfo(uri) { UseShellExecute = true }); } catch { /* no browser */ }
    }

    /// <summary>Never leave a blank window: say what went wrong and offer to try again.</summary>
    void ShowLoadError(string what)
    {
        Report("LOAD-ERROR " + what);
        var html = "<!doctype html><meta charset=\"utf-8\"><body style=\"font:15px 'Segoe UI',sans-serif;padding:40px;color:#222;background:#f4f5f7\">" +
                   "<h2>Technical Officials Scheduler could not start</h2>" +
                   $"<p>The planner page did not load ({System.Net.WebUtility.HtmlEncode(what)}).</p>" +
                   $"<p><a href=\"{StartUrl}\">Try again</a></p></body>";
        try { web.CoreWebView2.NavigateToString(html); } catch { /* ignore */ }
    }

    void OnProcessFailed(object? sender, CoreWebView2ProcessFailedEventArgs e)
    {
        Report("PROCESS-FAILED " + e.ProcessFailedKind);
        if (e.ProcessFailedKind == CoreWebView2ProcessFailedKind.BrowserProcessExited)
        {
            // not from inside the WebView2 event (re-entrancy)
            BeginInvoke(() =>
            {
                MessageBox.Show(this, "The app's display stopped unexpectedly. Your events are saved – please start the app again.",
                    Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
                mayClose = true; Close();
            });
            return;
        }
        if (e.ProcessFailedKind != CoreWebView2ProcessFailedKind.RenderProcessExited &&
            e.ProcessFailedKind != CoreWebView2ProcessFailedKind.RenderProcessUnresponsive) return;
        pageReady = false;
        contentCrashes++;
        // try again twice, then stop (an error page needs the same process, so it would loop)
        if (contentCrashes <= 2) web.CoreWebView2.Navigate(StartUrl);
    }

    /// <summary>Keep the editing items (cut, copy, paste…) and drop the browser ones (back, reload, print…).</summary>
    void OnContextMenu(object? sender, CoreWebView2ContextMenuRequestedEventArgs e)
    {
        var drop = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "back", "forward", "reload", "saveAs", "print", "createQrCode", "inspectElement", "webCapture", "share",
            "openLinkInNewWindow", "saveLinkAs", "saveImageAs", "saveFrameAs", "sendTabToSelf", "readAloud", "translate",
            "openLinkInNewTab", "copyLinkToHighlight"
        };
        var items = e.MenuItems;
        for (int i = items.Count - 1; i >= 0; i--)
            if (drop.Contains(items[i].Name)) items.RemoveAt(i);
        // tidy separators left at the ends or next to each other
        for (int i = items.Count - 1; i >= 0; i--)
        {
            bool sep = items[i].Kind == CoreWebView2ContextMenuItemKind.Separator;
            bool prevSep = i == 0 || items[i - 1].Kind == CoreWebView2ContextMenuItemKind.Separator;
            if (sep && (prevSep || i == items.Count - 1)) items.RemoveAt(i);
        }
        if (items.Count == 0) e.Handled = true;
    }

    // ------------------------------------------------------------------ closing: save first, remember the window

    async void OnFormClosing(object? sender, FormClosingEventArgs e)
    {
        SaveWindowPlace();
        if (mayClose || web.CoreWebView2 == null || !pageReady) return;
        e.Cancel = true;
        mayClose = true;
        try
        {
            await web.CoreWebView2.ExecuteScriptAsync("WTP.App.flush && WTP.App.flush(); 1");
            await Task.Delay(400);   // lets the save message arrive and be written
        }
        catch { /* close anyway */ }
        Close();
    }

    sealed record Place(int X, int Y, int W, int H, bool Max);

    string PlacePath => Path.Combine(AppData, "window.json");

    void PlaceWindow()
    {
        var area = Screen.PrimaryScreen?.WorkingArea ?? new Rectangle(0, 0, 1366, 768);
        float scale = DeviceDpi / 96f;
        MinimumSize = new Size((int)(760 * scale), (int)(520 * scale));
        int w = Math.Min((int)(1320 * scale), (int)(area.Width * 0.92)), h = Math.Min((int)(880 * scale), (int)(area.Height * 0.92));
        StartPosition = FormStartPosition.Manual;
        Bounds = new Rectangle(area.X + (area.Width - w) / 2, area.Y + (area.Height - h) / 2, w, h);
        try
        {
            var p = JsonSerializer.Deserialize<Place>(File.ReadAllText(PlacePath));
            if (p == null) return;
            var r = new Rectangle(p.X, p.Y, Math.Max(p.W, MinimumSize.Width), Math.Max(p.H, MinimumSize.Height));
            if (Screen.AllScreens.Any(s => s.WorkingArea.IntersectsWith(new Rectangle(r.X + 40, r.Y + 10, 120, 40)))) Bounds = r;
            if (p.Max) WindowState = FormWindowState.Maximized;
        }
        catch { /* first start */ }
    }

    void SaveWindowPlace()
    {
        try
        {
            var r = WindowState == FormWindowState.Normal ? Bounds : RestoreBounds;
            Directory.CreateDirectory(AppData);
            File.WriteAllText(PlacePath, JsonSerializer.Serialize(new Place(r.X, r.Y, r.Width, r.Height, WindowState == FormWindowState.Maximized)));
        }
        catch { /* ignore */ }
    }
}
