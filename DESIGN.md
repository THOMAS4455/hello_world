---
version: alpha
name: AlphaScope
description: "A stock research and forecasting workspace inspired by the calm institutional confidence of Coinbase and the dark product-first precision of Linear. The app uses a deep graphite shell, bright neutral content surfaces, a restrained cobalt primary accent, and dense but readable panels designed for repeated analytical work rather than marketing drama."

colors:
  primary: "#3b82f6"
  primary-hover: "#2563eb"
  primary-soft: "#dbeafe"
  accent: "#22c55e"
  accent-soft: "#dcfce7"
  danger: "#dc2626"
  danger-soft: "#fee2e2"
  ink: "#0f172a"
  ink-muted: "#475569"
  ink-soft: "#64748b"
  canvas: "#f3f6fb"
  shell: "#06090f"
  shell-soft: "#0f172a"
  shell-elevated: "#111827"
  surface: "#ffffff"
  surface-soft: "#f8fafc"
  hairline: "#dbe3ee"
  hairline-strong: "#cbd5e1"
  on-dark: "#f8fafc"

typography:
  display-lg:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 56px
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: 0
  display-md:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 40px
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: 0
  title-lg:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 28px
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: 0
  title-md:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: 0
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0
  body-sm:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  button:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0
  mono:
    fontFamily: "JetBrains Mono, Consolas, monospace"
    fontSize: 13px
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: 0

rounded:
  sm: 8px
  md: 12px
  lg: 16px
  xl: 20px
  pill: 9999px

spacing:
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 88px

components:
  top-nav:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.md}"
    height: 64px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: 10px 16px
  button-secondary:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 10px 16px
  hero-dark:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.xl}"
    padding: 32px
  panel-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 20px
  metric-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 18px
  text-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 10px 14px

---

## Overview

AlphaScope should feel like a serious financial workstation, not a generic SaaS dashboard and not a marketing landing page. The visual baseline comes from two references:

- Coinbase: restrained trust, bright surfaces, sparse use of blue, clear semantic gain/loss colors
- Linear: dark framing chrome, precise panel structure, product-first composition, low-noise interaction styling

This combination yields a dark shell around lighter data surfaces. The navigation, hero bands, and app framing can be dark and compact. The actual working surfaces should remain bright, dense, and easy to scan.

## Design Intent

- Use blue sparingly for the most important actions and selection states
- Keep green and red semantic-only for market movement
- Prefer framed panels over decorative gradients
- Use dark backgrounds to create focus, then present tables, charts, and controls on light cards
- Keep buttons and inputs compact and operational
- Favor readable density over oversized display moments once inside app workflows

## Do

- Use a dark shell with light analytical surfaces
- Keep card radius between 12px and 20px
- Use mono for codes, symbols, and numeric emphasis when helpful
- Make table, filter, and chart layouts stable and scan-friendly
- Reserve vivid blue for the primary CTA and active states

## Do Not

- Do not turn the dashboard into a marketing hero page
- Do not flood the interface with gradients or multiple accent hues
- Do not use large soft cards inside other cards
- Do not use semantic red/green for anything other than performance meaning
- Do not over-round controls into playful pills unless it is a badge or chip
