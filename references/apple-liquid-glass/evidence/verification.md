# Verification

Checked October 19, 2026. Package status covers a reusable reference and its browser previews.

## Rendering and source comparison

- Native framework specimen: compiled and launched the authored Swift/AppKit window on macOS 26.6.2. The selected-window capture in `native-light.png` shows both regular and clear system glass. The specimen and `NativeProbe.swift` were inspected together.
- Chrome 155: light, dark and opaque-fallback library captures, desktop dark Preferences and narrow light Preferences were visually inspected. System color roles, text hierarchy, content/control separation and functional states transferred to the new screen.
- The web result intentionally differs in geometry, backdrop optics and content. It is not a screenshot replica or a recovery of Apple's private shader. The synthetic swatches make the compositing visible without a source wallpaper.

## Behavior

The browser report records search/no-result, explicit empty/loading/error, retry, new note and updated count, dialog open/Escape/focus restoration, theme propagation, solid-material fallback, named settings fields/toggle, disabled connection and save error/retry/success. All data is synthetic and page-local. No persistence or network integration is implied.

Viewport checks covered 390, 768 and 1440 CSS px for the library and a 390 CSS px Preferences view; desktop Preferences was visually inspected. No horizontal overflow appeared in these conditions. Screenshots preserve the tested visual state; emulation can reload a page, so temporary note counts may differ across captures.

## Accessibility scope

Named controls, visible keyboard focus, modal focus restoration, disabled state and live feedback were exercised. `contrast.json` checks selected stable text/action pairs. The manual transparency control was tested. Source CSS contains reduced-motion, reduced-transparency and increased-contrast fallbacks; OS media preference emulation and native preference changes were not tested. VoiceOver, physical iOS devices and a full WCAG audit were not run.

## Tool boundaries

REA binary binding succeeded. Its native observation failed to match an accessibility window, so no REA AX capture is claimed. Platform window capture supplied the native visual evidence. Aside initially opened the preview but its connection ended; the completed web checks use isolated Chrome, not the interrupted Aside run.

Two browser issues found during authoring were corrected before the passing run: the theme controller now sets the class expected by generated token CSS, and the new-note count updates with the list. The generic system font is selected explicitly before the serializer's named font fallback list.
