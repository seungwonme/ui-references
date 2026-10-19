# Apple web / Product storytelling

## Scope and source

This package studies the live [MacBook Pro product page](https://www.apple.com/macbook-pro/) at desktop and mobile sizes. It captures a selected page's typography, controls and section rhythm, not every apple.com property. The new Folio product and its Getting started screen test whether the rules transfer to another subject.

## Transferable rules

Use a small product identity, a large concise headline, supporting copy and one clear primary action. Let the product demonstration carry the main visual story. Give each section one argument and enough separation to read it. Group secondary detail lower in the hierarchy. Navigation remains compact while display typography changes with available width.

Color is restrained: dark field, near-white primary text, quieter supporting text and a blue action. A light section can mark a different part of the story. The original product photograph, wordmark, exact composition and marketing sentences are not part of this system.

## Numeric source of truth

`tokens.json` owns the values. `source.hero`, `source.hero-line`, `source.hero-small`, `source.hero-small-line`, `source.section`, `source.eyebrow`, `source.body`, `source.pill` and `source.action` come from computed source styles. `evidence/web-measurements.json` preserves selectors, widths, viewport conditions and the relevant raw samples.

`source.section-gap` is a sampled subsection spacing, not a universal Apple spacing scale. `proposed.content`, `proposed.radius`, `proposed.gutter` and preview colors are authored. The original page uses SF web fonts; the preview delegates to the OS system font and does not redistribute Apple's font files. Metrics can therefore differ on non-Apple systems.

## Composition and responsive behavior

The Folio preview centers its opening argument above an authored interface illustration. Later sections explain features, then provide an actionable next step. This differs from the source's product reveal while preserving its typography hierarchy and restrained action grammar.

The source was measured at the viewport sizes in the evidence. The preview's breakpoint is an authored adaptation, not a recovered CSS media query. At narrow widths, columns stack, headings use the sampled small scale, navigation becomes a disclosure and controls keep usable targets. Content does not depend on scrolling animations.

## Components and states

Global reference bar, sticky product navigation, primary pill/link pair, finish selector, product illustration, feature sections, disclosure rows and a sign-up preview form. Finish buttons update the original CSS illustration and announce the chosen finish. The new Getting started screen reuses the same navigation, type, spacing and action tokens.

The form is deliberately local. Empty required input uses native browser validation; submit shows a loading state, then a local success/error message. The simulate-error control supports retry. No email is sent or persisted. The compact menu has an expanded state, Escape close and keyboard focus restoration.

## Material, motion and accessibility

Glass is limited to the sticky navigation. It is CSS backdrop blur, not Apple's native Liquid Glass. Reduced transparency makes it opaque. Reduced motion disables smooth scrolling and transitions. Primary text, secondary text and actions use explicit roles; keyboard focus stays visible. The product illustration has a text alternative and all controls have names.

## Analysis and design decisions

Chrome computed styles and DOM bounds were captured in an isolated browser context. The first attempted small desktop window was clamped by Chrome; it was discarded in favor of explicit device emulation. Original screenshots remain local review evidence; the published package contains measured facts and authored artwork.

The prototype question was whether product-story hierarchy transfers to a non-Apple service and its Getting started screen. The two pages answer that question without copying Apple layout or scenery. Taste was not executed because a source design was already selected; its font bans, decorative-image minimums and motion counts were not applied.

The gallery's existing static HTML/CSS/JS stack keeps this package inspectable without dependencies. It does not prescribe a stack for future services. Build with the gallery wrapper and serve the resulting output. Tokens are transformed into `assets/tokens.css` by the builder; do not hand-edit that generated file.

## Verification and limits

See [verification](evidence/verification.md) and `reference.json`. This is a rule-level transfer, not a pixel-identical recreation. Source scrolling video, checkout, internationalization, Apple APIs, native Safari devices and the entire source site's component library are outside the verified scope.

The web CSS puts the `system-ui` generic before the exported named fallback list because the current gallery serializer quotes font-family entries. This preserves the OS font choice without changing the generated runtime.
