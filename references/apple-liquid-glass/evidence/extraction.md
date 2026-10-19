# Extraction record

Checked 2026-10-19. Native measurements use macOS 26.6.2 (25G83) and SDK 27.0.

- HIG materials, typography, color, layout and accessibility were read as official guidance. Native default/minimum sizes remain logical points in the token metadata.
- NativeProbe.swift calls system APIs in-process. NSColor resolves under explicit appearance names and converts to sRGB. Values remain samples of this OS, not universal hex constants.
- The authored app was packaged and launched as a macOS application. A selected-window screenshot was visually inspected. Regular glass is lighter/more opaque than clear over the synthetic blocks. No private optical parameters were measured.
- REA open_binary bound the arm64 probe successfully. Its observe_native_ui first failed while compiling its helper, then rejected a command-line target without a launch time. The packaged target had a launch time but failed its AX-window identity check (no AX candidates). The native screenshot was obtained with the platform capture tool; no REA accessibility-tree success is claimed.
- The first native capture was blank because the authored window had alpha zero before app launch completed. After finishLaunching, setting the window visible and relaunching, a new selected-window capture showed the expected controls. The blank capture is excluded.
- The web specimen uses generated token CSS plus authored layering. Original source scenery, Apple font files, SF Symbol assets and framework code are not copied.

Sources: [Materials](https://developer.apple.com/design/human-interface-guidelines/materials), [Typography](https://developer.apple.com/design/human-interface-guidelines/typography), [Color](https://developer.apple.com/design/human-interface-guidelines/color), [Layout](https://developer.apple.com/design/human-interface-guidelines/layout), [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility), [NSGlassEffectView](https://developer.apple.com/documentation/appkit/nsglasseffectview).
