// Authored framework probe, not extracted Apple application code.
// swiftc NativeProbe.swift -o NativeProbe && ./NativeProbe [--show] [--dark]
import AppKit
import CoreGraphics

let app = NSApplication.shared
let names: [String: NSColor] = ["label": .labelColor, "secondaryLabel": .secondaryLabelColor,
    "tertiaryLabel": .tertiaryLabelColor, "separator": .separatorColor,
    "windowBackground": .windowBackgroundColor, "controlBackground": .controlBackgroundColor,
    "textBackground": .textBackgroundColor, "systemBlue": .systemBlue,
    "selectedContentBackground": .selectedContentBackgroundColor]
var appearances: [String: Any] = [:]
for (name, appearance) in [("light", NSAppearance.Name.aqua), ("dark", .darkAqua),
                           ("lightHighContrast", .accessibilityHighContrastAqua),
                           ("darkHighContrast", .accessibilityHighContrastDarkAqua)] {
    NSAppearance(named: appearance)!.performAsCurrentDrawingAppearance {
        var values: [String: [Double]] = [:]
        for (key, color) in names {
            let c = color.usingColorSpace(.sRGB)!
            values[key] = [Double(c.redComponent), Double(c.greenComponent), Double(c.blueComponent), Double(c.alphaComponent)]
        }
        appearances[name] = values
    }
}
let result: [String: Any] = ["os": ProcessInfo.processInfo.operatingSystemVersionString,
    "method": "NSColor resolved using explicit NSAppearance and converted to sRGB; logical font sizes in points",
    "appearances": appearances, "fonts": ["system": NSFont.systemFontSize,
        "small": NSFont.smallSystemFontSize, "label": NSFont.labelFontSize,
        "menu": NSFont.menuFont(ofSize: 0).pointSize],
    "reduceTransparency": NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency,
    "increaseContrast": NSWorkspace.shared.accessibilityDisplayShouldIncreaseContrast]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
if !CommandLine.arguments.contains("--show") {
    print(String(data: data, encoding: .utf8)!)
    exit(0)
}

final class Canvas: NSView {
    override func draw(_ dirtyRect: NSRect) {
        NSColor.windowBackgroundColor.setFill(); bounds.fill()
        for (i, color) in [NSColor.systemBlue, .systemTeal, .systemOrange].enumerated() {
            color.withAlphaComponent(0.5).setFill()
            NSBezierPath(roundedRect: NSRect(x: 50 + i * 255, y: 90, width: 190, height: 290), xRadius: 28, yRadius: 28).fill()
        }
    }
}
let dark = CommandLine.arguments.contains("--dark")
app.setActivationPolicy(.regular)
app.finishLaunching()
app.appearance = NSAppearance(named: dark ? .darkAqua : .aqua)
let window = NSWindow(contentRect: NSRect(x: 150, y: 160, width: 850, height: 500), styleMask: [.titled, .closable], backing: .buffered, defer: false)
window.title = "Apple material framework probe"
window.contentView = Canvas(frame: NSRect(x: 0, y: 0, width: 850, height: 500))
let heading = NSTextField(labelWithString: "Native AppKit materials")
heading.font = .systemFont(ofSize: 26, weight: .semibold)
heading.frame = NSRect(x: 36, y: 436, width: 600, height: 38)
window.contentView!.addSubview(heading)
if #available(macOS 26.0, *) {
    for (i, style) in [NSGlassEffectView.Style.regular, .clear].enumerated() {
        let glass = NSGlassEffectView(frame: NSRect(x: 74 + i * 355, y: 190, width: 310, height: 100))
        glass.style = style; glass.cornerRadius = 24
        let content = NSView(frame: glass.bounds)
        let label = NSTextField(labelWithString: i == 0 ? "Regular glass" : "Clear glass")
        label.font = .systemFont(ofSize: 17, weight: .semibold)
        label.frame = NSRect(x: 20, y: 56, width: 250, height: 24)
        content.addSubview(label)
        let button = NSButton(title: "Open collection", target: nil, action: nil)
        button.bezelStyle = .rounded
        button.frame = NSRect(x: 16, y: 16, width: 150, height: 32)
        content.addSubview(button); glass.contentView = content
        window.contentView!.addSubview(glass)
    }
}
let foot = NSTextField(labelWithString: "Synthetic swatches behind system-rendered glass. No Apple app screen copied.")
foot.textColor = .secondaryLabelColor; foot.frame = NSRect(x: 36, y: 28, width: 780, height: 24)
window.contentView!.addSubview(foot)
window.alphaValue = 1
window.makeKeyAndOrderFront(nil)
app.activate(ignoringOtherApps: false)
print("PROBE_PID=\(ProcessInfo.processInfo.processIdentifier) WINDOW_ID=\(window.windowNumber)")
fflush(stdout)
app.run()
