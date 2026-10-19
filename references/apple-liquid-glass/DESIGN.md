# Apple app UI / Liquid Glass

## Scope

A reusable interpretation of Apple HIG material roles and semantic color, checked against an authored AppKit probe on macOS 26.6.2. The browser preview is a Fieldnotes library. Preferences is a second, newly authored screen. Neither is an extracted Apple product screen.

## Rules to transfer

- Keep the content readable and visually stable. Glass belongs to floating controls and navigation. Do not put glass on every content card. [Materials](https://developer.apple.com/design/human-interface-guidelines/materials)
- Use system text roles and semantic colors in native implementations. The `source.light` and `source.dark` tokens are frozen runtime samples for study, not replacements for dynamic AppKit/UIKit colors. [Color](https://developer.apple.com/design/human-interface-guidelines/color)
- Prefer regular glass when labels and controls need dependable contrast. Clear glass needs a suitable visual background; the preview does not make it the default. The native specimen shows both.
- A sidebar, toolbar and content view have distinct jobs. Keep hierarchy, alignment, keyboard order and selected-state feedback explicit. Source photos, logos and copy do not transfer with these rules.

## Tokens and geometry

`tokens.json` owns all exported values. `source.*` records native NSColor samples with alpha intact. `web.*` records proposed CSS geometry, blur, opacity, accessible text colors and feedback duration. `font` delegates to the installed system font. `web.body` maps the measured logical system font size to a CSS study value; this does not equate physical pixels to native points.

The example uses `web.sidebar`, `web.radius`, `web.radius-lg`, `web.control` and `web.touch-control`. These are authored layout decisions. Apple does not publish a universal CSS Liquid Glass blur, border or shadow recipe. Do not promote these preview values to private shader measurements.

## Components and state

Library: selected sidebar link, segmented navigation, primary action, search, content groups, note rows and modal detail. Search filters synthetic notes. New note adds a temporary item. The state selector exposes empty/loading/error; retry returns to ready. The disabled sync action has a visible explanation.

Preferences: labeled fields, grouped settings, switch, unavailable connection, save success/error. All data lasts only for the current page. No network or storage integration is claimed. Hover, visible focus, disabled controls and keyboard modal dismissal are part of the web preview.

## Material and accessibility

The material specimen places authored color swatches behind a control so the compositing can be seen without a decorative wallpaper. CSS uses a translucent fill and backdrop blur. Reduce transparency replaces glass with an opaque surface. Reduced motion removes transitions. Increased contrast removes transparency and strengthens text. Focus has an explicit outline; state does not depend on color alone.

Light and dark use the measured semantic color families. `web.muted` and `web.accent` are contrast-oriented web adaptations. Native high-contrast appearance names returned identical sampled values in this probe; that result does not prove the operating system's full accessibility rendering or user settings were exercised.

## Platform differences

Native iOS/iPadOS should use system text styles, Dynamic Type, safe areas and adaptive containers. Native macOS should use NSFont roles and window/layout conventions. Do not describe the browser's mobile layout or text zoom as an iOS device test. The web preview changes the sidebar to a navigation strip at its authored breakpoint and increases interactive areas. That breakpoint is proposed.

`prototype/NativeProbe.swift` uses NSGlassEffectView with its contentView contract. The native class is available from macOS 26; the later effectIsInteractive property is deliberately not used. See [NSGlassEffectView](https://developer.apple.com/documentation/appkit/nsglasseffectview).

## Tools and design decisions

Official HIG research, explicit NSAppearance/NSColor runtime samples and an AppKit specimen supply the evidence. REA native UI observation is recorded separately in the verification evidence, including any failed attempts. Browser computed styles and screenshots verify this preview, not native optical equality.

Matt Pocock prototype's comparison question: can navigation retain a perceptible material while the content stays quiet, and can the same hierarchy support Preferences? Light/dark/solid controls compare the same content. No additional layout variants were needed for this extraction. Taste's marketing art-direction rules were not invoked: changing the source style or adding image/motion quotas would defeat this study.

## Reuse and limits

Use the material roles, semantic colors, type hierarchy and component relationships in another product. Keep that product's content and platform APIs. The static HTML/CSS/JS stack exists to publish an inspectable gallery preview; it is not a stack recommendation for native products.

Build from the gallery checkout with `uv --no-config run --locked --script scripts/gallery.py build --output <empty-directory>`, then serve the output. Native probe: `swiftc prototype/NativeProbe.swift -o <temporary-executable>`; run without flags for JSON samples, or with `--show` for a specimen. Do not distribute the compiled binary or Apple's framework/font assets.

Actual checks and remaining limits are in [verification](evidence/verification.md) and `reference.json`. Private optical shaders, system morphing, VoiceOver, physical iOS devices and full native accessibility settings are not verified by the web study.

The CSS adapter preserves generic font-family keywords. Native guidance keeps its original logical point unit in `$extensions["io.github.seungwonme.reference-ui"].nativeUnit`; generic token consumers still see a number and need a native adapter. The package uses the documented DTCG subset, while this DESIGN document is a prose usage contract. See [token validation evidence](evidence/token-contract-checks.json) for the metadata repair and font/layout regression scope.
