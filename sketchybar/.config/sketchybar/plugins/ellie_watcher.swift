// Wait for macOS app lifecycle events instead of polling for Ellie.
import AppKit
import Darwin
import Foundation

guard CommandLine.arguments.count == 5,
      let barPID = Int32(CommandLine.arguments[2]) else {
    fputs("Usage: ellie-watcher STATE_FILE BAR_PID SKETCHYBAR BUNDLE_ID\n", stderr)
    exit(1)
}
let stateURL = URL(fileURLWithPath: CommandLine.arguments[1])
let barExecutable = CommandLine.arguments[3]
let bundleID = CommandLine.arguments[4]
let notificationName = Notification.Name("local.sketchybar.ellie.reconcile.\(getuid()).\(bundleID)")
let lockFD = open(stateURL.path + ".lock", O_CREAT | O_RDWR | O_NOFOLLOW, S_IRUSR | S_IWUSR)
guard lockFD >= 0 else { exit(1) }

func readState() -> [String: Any] {
    guard let data = try? Data(contentsOf: stateURL),
          let state = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
    return state
}

if flock(lockFD, LOCK_EX | LOCK_NB) != 0 {
    // Reuse the existing observer after a config reload. If the service itself
    // restarted, wait for the old observer's process-exit notification instead.
    let deadline = Date().addingTimeInterval(2)
    while true {
        if (readState()["bar_pid"] as? Int32) == barPID {
            DistributedNotificationCenter.default().postNotificationName(
                notificationName, object: nil, userInfo: nil, deliverImmediately: true)
            exit(0)
        }
        if flock(lockFD, LOCK_EX | LOCK_NB) == 0 { break }
        if Date() >= deadline {
            fputs("Ellie watcher: previous observer did not exit\n", stderr)
            exit(1)
        }
        usleep(50_000) // Bounded startup handoff only; no recurring polling.
    }
}

@Sendable func writeState(running: Bool) {
    let state: [String: Any] = ["running": running, "watcher_pid": getpid(), "bar_pid": barPID]
    do {
        let data = try JSONSerialization.data(withJSONObject: state)
        try data.write(to: stateURL, options: .atomic)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: stateURL.path)
    } catch {
        fputs("Ellie watcher: could not save application state\n", stderr)
        exit(1)
    }
}

var lastRunning: Bool?
let tickURL = stateURL.deletingLastPathComponent().appendingPathComponent("tick.json")
struct TickSample: Decodable, Equatable {
    let running: Bool
    let seconds: Int
    let direction: Int
    let symbol: String
    let referenceTime: Double
    let sampledAt: Double
}
var tickSample: TickSample?
var ticker: DispatchSourceTimer?
var lastTickText: String?

@Sendable func sendToBar(_ arguments: [String]) {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: barExecutable)
    process.arguments = arguments
    process.standardOutput = FileHandle.nullDevice
    process.standardError = FileHandle.nullDevice
    do {
        try process.run()
        process.waitUntilExit()
    } catch {
        fputs("Ellie watcher: could not update SketchyBar\n", stderr)
    }
}

@Sendable func stopTicker() {
    ticker?.cancel()
    ticker = nil
    tickSample = nil
    lastTickText = nil
}

func tick() {
    guard lastRunning == true, let sample = tickSample else { return }
    let now = Date().timeIntervalSince1970
    guard now - sample.sampledAt < 15 else { stopTicker(); return }
    let elapsed = max(0, Int(floor(now - sample.referenceTime)))
    let value = max(0, sample.seconds + sample.direction * elapsed)
    let clock = value >= 3600
        ? String(format: "%d:%02d:%02d", value / 3600, value / 60 % 60, value % 60)
        : String(format: "%02d:%02d", value / 60, value % 60)
    let text = "\(sample.symbol) \(clock)"
    guard text != lastTickText else { return }
    sendToBar(["--set", "weather", "icon=\(text)", "--set", "weather.notch", "icon=\(text)"])
    lastTickText = text
}

func loadTickSample() {
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    guard lastRunning == true,
          let data = try? Data(contentsOf: tickURL),
          let sample = try? decoder.decode(TickSample.self, from: data),
          sample.running, sample.seconds >= 0, abs(sample.direction) == 1,
          sample.referenceTime.isFinite, sample.sampledAt.isFinite,
          Date().timeIntervalSince1970 - sample.sampledAt < 15 else {
        stopTicker()
        return
    }
    guard sample != tickSample else { return }
    stopTicker()
    tickSample = sample
    // Align native ticks to the original timer's second boundaries. No Python
    // process, database read, or file polling is needed for these ticks.
    let age = max(0, Date().timeIntervalSince1970 - sample.referenceTime)
    let delay = 1 - age.truncatingRemainder(dividingBy: 1)
    let source = DispatchSource.makeTimerSource(queue: .main)
    source.schedule(deadline: .now() + delay, repeating: 1, leeway: .milliseconds(10))
    source.setEventHandler { tick() }
    ticker = source
    source.resume()
}

func reconcile(force: Bool = false) {
    let running = NSWorkspace.shared.runningApplications.contains {
        $0.bundleIdentifier == bundleID && !$0.isTerminated
    }
    if !force && lastRunning == running { return }
    writeState(running: running)
    lastRunning = running
    stopTicker()
    try? FileManager.default.removeItem(at: tickURL)
    sendToBar(["--set", "ellie_timer", "update_freq=\(running ? 5 : 0)",
               "--trigger", "ellie_app_changed"])
}

// Publish identity immediately so a concurrent reload can find this observer.
writeState(running: false)
let workspaceCenter = NSWorkspace.shared.notificationCenter
// KVO also includes accessory/background apps, which the workspace's standard
// launch/terminate notifications explicitly exclude. This is event-driven.
let appObserver = NSWorkspace.shared.observe(\.runningApplications, options: [.new]) { _, _ in
    DispatchQueue.main.async { reconcile() }
}
let wakeObserver = workspaceCenter.addObserver(forName: NSWorkspace.didWakeNotification, object: nil, queue: .main) { _ in
    reconcile(force: true)
}
let reloadObserver = DistributedNotificationCenter.default().addObserver(
    forName: notificationName, object: nil, queue: .main) { _ in reconcile(force: true) }

// Python atomically replaces tick.json after a five-second state refresh.
// Watching the directory survives file replacement and avoids file polling.
let directoryFD = open(stateURL.deletingLastPathComponent().path, O_EVTONLY)
guard directoryFD >= 0 else { exit(1) }
let tickFileChanges = DispatchSource.makeFileSystemObjectSource(
    fileDescriptor: directoryFD, eventMask: .write, queue: .main)
tickFileChanges.setEventHandler { loadTickSample() }
tickFileChanges.setCancelHandler { close(directoryFD) }
tickFileChanges.resume()

// A kernel process-exit event ties the watcher to SketchyBar's lifetime.
let barExit = DispatchSource.makeProcessSource(identifier: barPID, eventMask: .exit, queue: .main)
barExit.setEventHandler {
    writeState(running: false)
    exit(0)
}
barExit.resume()
guard kill(barPID, 0) == 0 else { exit(0) }
reconcile()
RunLoop.main.run()
