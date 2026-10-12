// NextUp: the next meeting in the Mac menu bar, read from macOS Calendar (EventKit).
// Build: ./build.sh   Config: ~/.config/nextup/config.json

import AppKit
import EventKit

// MARK: - Config

struct Config: Codable {
    var excludeCalendars: [String] = []   // calendar titles to ignore
    var excludeTitles: [String] = []      // event titles to ignore (exact match)
    var browserPath: String? = nil        // app that opens join links; nil = default browser
    var maxTitleLength: Int = 20          // characters of menu bar text
    var countdownMinutes: Int = 15        // switch to "Title in 8m" this close to the start
    var meetingPath: String? = nil        // the `meeting` command; nil = look in the usual places

    init() {}

    // Every key is optional: a missing one keeps its default rather than failing the whole file.
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let d = Config()
        excludeCalendars = try c.decodeIfPresent([String].self, forKey: .excludeCalendars) ?? d.excludeCalendars
        excludeTitles = try c.decodeIfPresent([String].self, forKey: .excludeTitles) ?? d.excludeTitles
        browserPath = try c.decodeIfPresent(String.self, forKey: .browserPath)
        maxTitleLength = try c.decodeIfPresent(Int.self, forKey: .maxTitleLength) ?? d.maxTitleLength
        countdownMinutes = try c.decodeIfPresent(Int.self, forKey: .countdownMinutes) ?? d.countdownMinutes
        meetingPath = try c.decodeIfPresent(String.self, forKey: .meetingPath)
    }
}

let configURL = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent(".config/nextup/config.json")

func loadConfig() -> Config {
    guard let d = try? Data(contentsOf: configURL),
          let c = try? JSONDecoder().decode(Config.self, from: d) else { return Config() }
    return c
}

// MARK: - Join links

let linkPatterns = [
    #"https://[\w.-]*zoom\.us/(j|my|w)/[^\s<>"']+"#,
    #"https://teams\.(microsoft|live)\.com/(l/meetup-join|meet)/[^\s<>"']+"#,
    #"https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}"#,
    #"https://[\w.-]*webex\.com/[^\s<>"']+"#,
]

func joinLink(_ e: EKEvent) -> URL? {
    let fields = [e.url?.absoluteString, e.location, e.notes].compactMap { $0 }
    for text in fields {
        for p in linkPatterns {
            if let r = text.range(of: p, options: [.regularExpression, .caseInsensitive]) {
                // Outlook wraps links in <...>; trim stray trailing punctuation.
                let s = String(text[r]).trimmingCharacters(in: CharacterSet(charactersIn: ">).,;"))
                if let u = URL(string: s) { return u }
            }
        }
    }
    return nil
}

// MARK: - Recording (the `meeting` command drives OBS)

/// The `meeting` command: "meetingPath" from the config, else the first of the usual
/// install locations that holds it.
let meetingCmd: String = {
    if let p = loadConfig().meetingPath { return (p as NSString).expandingTildeInPath }
    let home = NSHomeDirectory()
    for p in ["\(home)/.local/bin/meeting", "/opt/homebrew/bin/meeting", "/usr/local/bin/meeting"]
        where FileManager.default.isExecutableFile(atPath: p) {
        return p
    }
    return "\(home)/.local/bin/meeting"
}()

/// Runs `meeting <args>` and returns its exit code and combined output.
func runMeeting(_ args: [String]) -> (Int32, String) {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: meetingCmd)
    p.arguments = args
    var env = ProcessInfo.processInfo.environment
    env["PATH"] = "\(NSHomeDirectory())/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + (env["PATH"] ?? "")
    p.environment = env
    let pipe = Pipe()
    p.standardOutput = pipe
    p.standardError = pipe
    do { try p.run() } catch { return (-1, "Couldn't run \(meetingCmd)") }
    let out = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
    p.waitUntilExit()
    return (p.terminationStatus, out.trimmingCharacters(in: .whitespacesAndNewlines))
}

/// Names on the invitation other than me, for speaker labelling.
func attendeeNames(_ e: EKEvent) -> [String] {
    (e.attendees ?? []).filter { !$0.isCurrentUser && $0.participantType == .person }
        .compactMap { $0.name }.filter { !$0.isEmpty }
}

// MARK: - App

final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let store = EKEventStore()
    var config = loadConfig()
    var granted = false
    var recording = false
    var recordingBusy = false   // a start or stop is in flight

    func applicationDidFinishLaunching(_ n: Notification) {
        item.button?.font = NSFont.monospacedDigitSystemFont(ofSize: 13, weight: .medium)
        item.button?.title = "…"
        store.requestFullAccessToEvents { ok, _ in
            DispatchQueue.main.async {
                self.granted = ok
                self.render()
            }
        }
        NotificationCenter.default.addObserver(forName: .EKEventStoreChanged, object: store, queue: .main) {
            [weak self] _ in self?.render()
        }
        // Wake from sleep and the countdown both need a redraw.
        NSWorkspace.shared.notificationCenter.addObserver(forName: NSWorkspace.didWakeNotification,
                                                          object: nil, queue: .main) { [weak self] _ in self?.render() }
        Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            self?.pollRecording()
            self?.render()
        }
        pollRecording()
    }

    /// Asks OBS (through `meeting status`) whether it is recording, so the ● stays right
    /// however the recording was started or stopped.
    func pollRecording() {
        guard !recordingBusy else { return }
        DispatchQueue.global().async {
            let (_, out) = runMeeting(["status"])
            let on = out.contains("OBS recording: yes")
            DispatchQueue.main.async {
                if on != self.recording { self.recording = on; self.render() }
            }
        }
    }

    func startRecording(_ e: EKEvent) {
        var args = ["start"]
        let names = attendeeNames(e)
        if !names.isEmpty { args += ["--attendees", names.joined(separator: ", ")] }
        args += ["--", e.title ?? "Meeting"]  // after "--", a title starting with "-" is not read as an option
        recordingBusy = true
        render()
        DispatchQueue.global().async {
            let (rc, out) = runMeeting(args)
            DispatchQueue.main.async {
                self.recordingBusy = false
                if rc == 0 { self.recording = true } else { self.alert("Recording didn't start", out) }
                self.render()
            }
        }
    }

    @objc func stopRecording() {
        recordingBusy = true
        render()
        DispatchQueue.global().async {
            let (rc, out) = runMeeting(["stop"])
            DispatchQueue.main.async {
                self.recordingBusy = false
                if rc == 0 { self.recording = false } else { self.alert("Recording didn't stop", out) }
                self.render()
                self.pollRecording()
            }
        }
    }

    @objc func record(_ sender: NSMenuItem) {
        guard let e = sender.representedObject as? EKEvent else { return }
        startRecording(e)
    }

    @objc func joinAndRecord(_ sender: NSMenuItem) {
        guard let e = sender.representedObject as? EKEvent, let link = joinLink(e) else { return }
        open(link)
        startRecording(e)
    }

    func alert(_ title: String, _ text: String) {
        let a = NSAlert()
        a.messageText = title
        a.informativeText = text.isEmpty ? "No output from `meeting`." : text
        NSApp.activate(ignoringOtherApps: true)
        a.runModal()
    }

    /// Timed events between two dates, minus declined, excluded and cancelled ones.
    /// With hidePast, events that have already ended are dropped too.
    func events(from start: Date, to end: Date, hidePast: Bool) -> [EKEvent] {
        let now = Date()
        let cals = store.calendars(for: .event).filter { !config.excludeCalendars.contains($0.title) }
        let pred = store.predicateForEvents(withStart: start, end: end, calendars: cals)
        return store.events(matching: pred).filter { e in
            if e.isAllDay || e.status == .canceled { return false }
            if config.excludeTitles.contains(e.title ?? "") { return false }
            if let me = e.attendees?.first(where: { $0.isCurrentUser }), me.participantStatus == .declined {
                return false
            }
            return !hidePast || e.endDate > now
        }.sorted { $0.startDate < $1.startDate }
    }

    // MARK: Day browsing

    var dayOffset = 0             // 0 = today; the arrows in the menu move it
    var menuOpen = false
    var dayItems: [NSMenuItem] = []
    weak var dayLabel: NSButton?
    let mainMenu = NSMenu()

    func menuWillOpen(_ menu: NSMenu) { menuOpen = true }

    func menuDidClose(_ menu: NSMenu) {
        menuOpen = false
        dayOffset = 0
        render()
    }

    /// The "◀  Today, Monday 5 October  ▶" row. A view, so clicks don't close the menu.
    func dayNavItem() -> NSMenuItem {
        let v = NSView(frame: NSRect(x: 0, y: 0, width: 320, height: 26))
        func button(_ title: String, _ x: CGFloat, _ w: CGFloat, _ sel: Selector) -> NSButton {
            let b = NSButton(title: title, target: self, action: sel)
            b.frame = NSRect(x: x, y: 1, width: w, height: 24)
            b.bezelStyle = .recessed
            b.isBordered = false
            return b
        }
        v.addSubview(button("◀", 8, 32, #selector(prevDay)))
        let label = button("", 44, 232, #selector(today))
        label.font = NSFont.boldSystemFont(ofSize: 13)
        label.toolTip = "Back to today"
        v.addSubview(label)
        v.addSubview(button("▶", 280, 32, #selector(nextDay)))
        dayLabel = label
        let m = NSMenuItem()
        m.view = v
        return m
    }

    @objc func prevDay() { dayOffset -= 1; showDay() }
    @objc func nextDay() { dayOffset += 1; showDay() }
    @objc func today() { dayOffset = 0; showDay() }

    /// Replaces the meetings listed under the day row, in place, so it works with the menu open.
    func showDay() {
        let cal = Calendar.current
        let now = Date()
        let start = cal.date(byAdding: .day, value: dayOffset, to: cal.startOfDay(for: now))!
        let end = cal.date(byAdding: .day, value: 1, to: start)!
        let dayf = DateFormatter(); dayf.dateFormat = "EEEE d MMMM"
        let prefix = dayOffset == 0 ? "Today, " : dayOffset == 1 ? "Tomorrow, " : dayOffset == -1 ? "Yesterday, " : ""
        dayLabel?.title = prefix + dayf.string(from: start)

        for m in dayItems { mainMenu.removeItem(m) }
        dayItems = []
        guard let nav = mainMenu.items.firstIndex(where: { $0.view != nil }) else { return }
        let evs = events(from: dayOffset == 0 ? now : start, to: end, hidePast: dayOffset == 0)
        var new = evs.map { eventItem($0, now: now) }
        if evs.isEmpty { new = [disabled(dayOffset == 0 ? "   Nothing more today" : "   No meetings")] }
        for (i, m) in new.enumerated() { mainMenu.insertItem(m, at: nav + 1 + i) }
        dayItems = new
    }

    /// One meeting line, with Join / Record / Open in Calendar in its submenu.
    func eventItem(_ e: EKEvent, now: Date) -> NSMenuItem {
        let tf = DateFormatter(); tf.dateFormat = "HH:mm"
        let line = "\(tf.string(from: e.startDate))–\(tf.string(from: e.endDate))   \(short(e.title ?? "(no title)", 50))"
        let m = NSMenuItem(title: line, action: nil, keyEquivalent: "")
        let sub = NSMenu()
        if let link = joinLink(e) {
            let j = action("Join", #selector(join(_:)))
            j.representedObject = link
            sub.addItem(j)
        }
        if !recording && !recordingBusy {
            let r = action("Record", #selector(record(_:)))
            r.representedObject = e
            sub.addItem(r)
        }
        let o = action("Open in Calendar", #selector(openInCalendar(_:)))
        o.representedObject = e.startDate
        sub.addItem(o)
        if let loc = e.location, !loc.isEmpty, joinLink(e) == nil || !loc.contains("http") {
            sub.addItem(disabled(short(loc, 60)))
        }
        sub.addItem(disabled(e.calendar.title))
        m.submenu = sub
        if e.startDate <= now && e.endDate > now { m.state = .on }   // tick marks the meeting in progress
        if e.endDate <= now {   // past meetings, when browsing back, in grey
            m.attributedTitle = NSAttributedString(string: line, attributes: [.foregroundColor: NSColor.secondaryLabelColor])
        }
        return m
    }

    func short(_ s: String, _ n: Int) -> String {
        s.count <= n ? s : String(s.prefix(max(1, n - 1))).trimmingCharacters(in: .whitespaces) + "…"
    }

    func render() {
        config = loadConfig()
        let menu = mainMenu
        menu.delegate = self
        guard granted else {
            menu.removeAllItems()
            item.button?.title = "📅 ?"
            menu.addItem(disabled("NextUp has no access to your calendars."))
            menu.addItem(action("Open Privacy Settings…", #selector(openPrivacy)))
            finish(menu)
            return
        }

        let now = Date()
        let tf = DateFormatter(); tf.dateFormat = "HH:mm"
        let todayEnd = Calendar.current.date(byAdding: .day, value: 1, to: Calendar.current.startOfDay(for: now))!
        let evs = events(from: now, to: todayEnd, hidePast: true)

        // Menu bar title: the meeting in progress, else the next one today.
        let current = evs.first { $0.startDate <= now }
        let next = evs.first { $0.startDate > now && $0.startDate < todayEnd }
        let n = config.maxTitleLength
        var title: String
        if let c = current, next == nil || next!.startDate.timeIntervalSince(now) > Double(config.countdownMinutes) * 60 {
            title = short(c.title ?? "Meeting", n - 4) + " now"
        } else if let x = next {
            let mins = Int(ceil(x.startDate.timeIntervalSince(now) / 60))
            if mins <= config.countdownMinutes {
                let tail = " in \(mins)m"
                title = short(x.title ?? "Meeting", n - tail.count) + tail
            } else {
                let head = tf.string(from: x.startDate) + " "
                title = head + short(x.title ?? "Meeting", n - head.count)
            }
        } else {
            title = "📅"
        }
        if recording { title = "● " + title }
        item.button?.title = title

        // Don't rebuild under the user while they're browsing days; the title above still updates.
        if menuOpen { return }
        menu.removeAllItems()
        dayItems = []

        // Recording controls and quick join for the meeting that's on or about to start.
        let soon = current ?? next.flatMap { $0.startDate.timeIntervalSince(now) <= Double(config.countdownMinutes) * 60 ? $0 : nil }
        if recordingBusy {
            menu.addItem(disabled("Talking to OBS…"))
        } else if recording {
            menu.addItem(action("■ Stop recording", #selector(stopRecording), key: "s"))
            menu.addItem(disabled("Tell everyone on the call that you're recording."))
        }
        if let s = soon {
            let name = short(s.title ?? "meeting", 40)
            if let link = joinLink(s) {
                let m = action("Join “\(name)”", #selector(join(_:)), key: "j")
                m.representedObject = link
                menu.addItem(m)
                if !recording && !recordingBusy {
                    let jr = action("Join and record", #selector(joinAndRecord(_:)))
                    jr.representedObject = s
                    menu.addItem(jr)
                }
            }
            if !recording && !recordingBusy {
                let r = action("● Record “\(name)”", #selector(record(_:)), key: "r")
                r.representedObject = s
                menu.addItem(r)
            }
        }
        if menu.items.count > 0 { menu.addItem(.separator()) }

        menu.addItem(dayNavItem())
        menu.addItem(.separator())
        menu.addItem(action("Edit config…", #selector(openConfig), key: ","))
        menu.addItem(NSMenuItem(title: "Quit NextUp", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        finish(menu)
        showDay()
    }

    func finish(_ menu: NSMenu) { item.menu = menu }

    func action(_ title: String, _ sel: Selector, key: String = "") -> NSMenuItem {
        let m = NSMenuItem(title: title, action: sel, keyEquivalent: key)
        m.target = self
        return m
    }

    func disabled(_ s: String, bold: Bool = false) -> NSMenuItem {
        let m = NSMenuItem(title: s, action: nil, keyEquivalent: "")
        if bold { m.attributedTitle = NSAttributedString(string: s, attributes: [.font: NSFont.boldSystemFont(ofSize: 13)]) }
        m.isEnabled = false
        return m
    }

    @objc func join(_ sender: NSMenuItem) {
        guard let url = sender.representedObject as? URL else { return }
        open(url)
    }

    func open(_ url: URL) {
        if let p = config.browserPath, FileManager.default.fileExists(atPath: p) {
            NSWorkspace.shared.open([url], withApplicationAt: URL(fileURLWithPath: p),
                                    configuration: NSWorkspace.OpenConfiguration())
        } else {
            NSWorkspace.shared.open(url)
        }
    }

    @objc func openInCalendar(_ sender: NSMenuItem) {
        guard let d = sender.representedObject as? Date else { return }
        // Calendar.app accepts a date in this URL form (seconds since 2001).
        NSWorkspace.shared.open(URL(string: "ical://ekevent/?date=\(Int(d.timeIntervalSinceReferenceDate))")!)
    }

    @objc func openPrivacy() {
        NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Calendars")!)
    }

    @objc func openConfig() {
        if !FileManager.default.fileExists(atPath: configURL.path) {
            try? FileManager.default.createDirectory(at: configURL.deletingLastPathComponent(),
                                                     withIntermediateDirectories: true)
            let enc = JSONEncoder(); enc.outputFormatting = [.prettyPrinted, .sortedKeys]
            try? enc.encode(config).write(to: configURL)
        }
        NSWorkspace.shared.open(configURL)
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
