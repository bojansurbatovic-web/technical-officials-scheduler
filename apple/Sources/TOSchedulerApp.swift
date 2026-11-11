// Technical Officials Scheduler – native shell for iPhone, iPad and Mac.
// The planner itself is the web app in the bundled "web" folder (shared with the web and Ubuntu versions);
// this shell hosts it in a WKWebView and adds files, sharing and menus.
import SwiftUI

@main
struct TOSchedulerApp: App {
    @StateObject private var model = WebModel()

    var body: some Scene {
        #if os(macOS)
        Window("Technical Officials Scheduler", id: "main") {
            WebContainer(model: model)
                .frame(minWidth: 760, minHeight: 520)
                .onOpenURL { model.open(url: $0) }
        }
        .defaultSize(width: 1320, height: 880)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Event…") { model.command("new") }.keyboardShortcut("n")
                Button("Open Plan File…") { model.command("open") }.keyboardShortcut("o")
            }
            CommandGroup(after: .saveItem) {
                Button("Export & Share…") { model.command("export") }.keyboardShortcut("e")
            }
            CommandMenu("Plan") {
                Button("Auto-assign") { model.command("replan") }.keyboardShortcut("r")
                Divider()
                Button("Undo Plan Change") { model.command("undo") }.keyboardShortcut("z", modifiers: [.command, .option])
                Button("Redo Plan Change") { model.command("redo") }.keyboardShortcut("z", modifiers: [.command, .option, .shift])
            }
        }
        #else
        WindowGroup {
            WebContainer(model: model)
                .ignoresSafeArea()
                .onOpenURL { model.open(url: $0) }
        }
        #endif
    }
}
