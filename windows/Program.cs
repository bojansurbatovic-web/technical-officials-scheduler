// Technical Officials Scheduler – Windows app.
// The planner itself is the web app in the "web" folder (shared with the web, Apple and Ubuntu versions);
// this shell hosts it in a WebView2 window and adds event files, Save dialogs and links.
namespace TOScheduler;

static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new MainForm(args));
    }
}
