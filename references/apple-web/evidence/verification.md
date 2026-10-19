# Verification

Checked October 19, 2026 in Chrome 155 on macOS, isolated context.

## Source and transfer

The live MacBook Pro page was measured at 1440x1000 and explicitly emulated 390x844 CSS px. Raw component facts are in `web-measurements.json`. Original source screenshots were inspected locally. The package contains authored Folio artwork and text, so it transfers the type/spacing/control relationships without redistributing Apple product imagery.

Desktop and narrow product previews and the new Getting started page were rendered and visually inspected. Display hierarchy, primary pill, compact navigation, section rhythm and stacked mobile content remain legible. Folio's centered hero and paper interface are intentional changes; source pixel identity, source animation timing and every apple.com component are not claimed.

## Behavior

The browser report covers finish selection with pressed-state feedback, desktop/mobile menu, Escape close and focus restoration, FAQ expansion, empty email validation, transient loading/disabled state, local error, retry and success. No email is sent or persisted. The form is a state demonstration.

No horizontal overflow was found at 390, 768 and 1440 CSS px for the product page; the new guide was also checked at 390 CSS px. Guide screenshots include a scrolled form position to show the reuse flow.

## Accessibility scope

Controls have names; the menu supports keyboard Escape and focus restoration. The form has a persistent label, browser validation and a status region. `contrast.json` verifies selected stable text/action pairs. Reduced-motion/transparency media rules were source-reviewed, but OS preference toggles, screen readers and physical devices were not tested. This is a scoped browser review, not a full WCAG audit.

## Limits

The preview uses system-ui before the exported named fallback list, so exact Apple webfont metrics can differ on other systems. Checkout, network services, persistence and Apple's native material shader were not part of the experiment. A failed small-window resize sample was discarded; only explicit device emulation is labeled 390 px in the source evidence.
