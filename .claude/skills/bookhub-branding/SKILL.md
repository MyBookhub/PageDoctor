---
name: bookhub-branding
description: Apply Bookhub brand identity (mybookhub.de) to any HTML, CSS, or frontend output. Covers colors, typography, spacing, components, tone, and visual patterns. Use whenever building UI, creating pages, designing emails, or generating any visual asset for Bookhub.
argument-hint: "[build|review|tokens] [component or page]"
metadata:
  author: bookhub
  version: "3.0.0"
---

# Bookhub Brand Identity Skill v3.0

Enforce the Bookhub brand system (mybookhub.de) on every frontend or visual output. This skill is the single source of truth — derived from the live website and the Brand Identity Guide v3.

## When to activate

- Building any Bookhub HTML page, component, or email
- Creating landing pages, dashboards, or tools for Bookhub
- Reviewing existing UI for brand compliance
- Generating mockups, slides, or visual assets
- Any CSS/Tailwind/inline styling for a Bookhub context

---

## 1 — Design Tokens (CSS Custom Properties)

Copy this `:root` block verbatim into every Bookhub project:

```css
:root {
  /* ── Colors ── */
  --coral: #E8725A;
  --deep-coral: #C95A44;
  --soft-peach: #FDEAE6;
  --sage: #7FB685;
  --mint: #E8F5E9;
  --black: #1A1A2E;
  --charcoal: #3D3D56;
  --grey: #9E9EB0;
  --warm-white: #FAF8F6;
  --cream: #FFF9F5;
  --gold: #F5B041;
  --lavender: #B8A9C9;
  --white: #FFFFFF;

  /* ── Typography ── */
  --font-display: 'Cabinet Grotesk', sans-serif;
  --font-body: 'DM Sans', sans-serif;
  --font-serif: 'Lora', serif;
  --font-hand: 'Caveat', cursive;

  /* ── Borders & Radius ── */
  --border: rgba(30, 30, 46, 0.08);
  --radius-sm: 12px;
  --radius-md: 16px;
  --radius-lg: 24px;
  --radius-pill: 999px;

  /* ── Shadows ── */
  --shadow-soft: 0 4px 24px rgba(26, 26, 46, 0.06);
  --shadow-card: 0 8px 32px rgba(26, 26, 46, 0.08);
  --shadow-sticker: 0 4px 16px rgba(26, 26, 46, 0.1);
  --shadow-nav: 0 4px 32px rgba(26, 26, 46, 0.08);

  /* ── Motion ── */
  --ease: cubic-bezier(0.25, 0.46, 0.45, 0.94);
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --transition: 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);

  /* ── Gradients ── */
  --gradient-sunset: linear-gradient(135deg, #E8725A, #F5B041);
  --gradient-fresh: linear-gradient(135deg, #7FB685, #E8F5E9);
  --gradient-dreamy: linear-gradient(135deg, #B8A9C9, #FDEAE6);
}
```

### Font Loading

Always include these in `<head>`:

```html
<!-- Cabinet Grotesk via Fontshare -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;500;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600;1,700&display=swap" rel="stylesheet">
```

Cabinet Grotesk must be loaded separately via `@font-face` from Fontshare (weights 400, 500, 700, 800).

---

## 2 — Color System

### Primary Palette
| Name | Hex | Role |
|------|-----|------|
| Coral | `#E8725A` | Primary brand, CTAs, links, active states |
| Deep Coral | `#C95A44` | Hover states, dark coral accents |
| Soft Peach | `#FDEAE6` | Light coral backgrounds, tags, hover fills |

### Secondary Palette
| Name | Hex | Role |
|------|-----|------|
| Sage | `#7FB685` | Success, positive, nature accents |
| Mint | `#E8F5E9` | Light green backgrounds |
| Gold | `#F5B041` | Highlights, badges, premium accents |
| Lavender | `#B8A9C9` | Soft accent, decorative, stories |

### Neutrals
| Name | Hex | Role |
|------|-----|------|
| Black | `#1A1A2E` | Primary text, dark backgrounds |
| Charcoal | `#3D3D56` | Secondary text, body copy |
| Grey | `#9E9EB0` | Muted text, placeholders, meta |
| Warm White | `#FAF8F6` | Page background |
| Cream | `#FFF9F5` | Section background (warmer) |
| White | `#FFFFFF` | Cards, inputs, overlays |

### Section Backgrounds (mybookhub.de pattern)
- Hero: `--cream`
- Stories: `--white`
- Features: `--cream`
- Steps: `--mint`
- Infra: `--warm-white`
- Compare: `--soft-peach`
- Contact: `--black` (dark section)
- CTA Banner: `--coral`

### Color Rules
- **Never** use pure black `#000000` — always `--black` (#1A1A2E)
- **Never** use generic blue, red, or green — stay in palette
- Dark sections use `--black` background with `--white` text
- Text on coral: always `--white`
- Text on cream/peach: always `--black` or `--charcoal`
- Accessible combos: Coral on White (4.5:1), Black on White (16:1), White on Black (16:1)

---

## 3 — Typography

### Font Roles
| Font | Variable | Role | Weights |
|------|----------|------|---------|
| Cabinet Grotesk | `--font-display` | H1–H3 headlines, hero text | 400, 500, 700, 800 |
| DM Sans | `--font-body` | Body text, H4–H6, UI, buttons, labels | 300–700 |
| Lora | `--font-serif` | Quotes, emotional accents, italic highlights | 400, 500, 600, 700 + italic |
| Caveat | `--font-hand` | Sticker badges, handwritten accents only | 400–700 |

### Type Scale
| Level | Font | Size | Weight | Letter-spacing |
|-------|------|------|--------|----------------|
| Display | Cabinet Grotesk | clamp(44px, 8vw, 96px) | 800 | -0.04em |
| H1 | Cabinet Grotesk | clamp(36px, 5vw, 64px) | 800 | -0.03em |
| H2 | Cabinet Grotesk | clamp(28px, 4vw, 48px) | 700 | -0.02em |
| H3 | Cabinet Grotesk | 28px | 700 | -0.01em |
| H4 | DM Sans | 20px | 700 | — |
| Body | DM Sans | 17px / 1.7 line-height | 400 | — |
| Small | DM Sans | 14–15px | 400–500 | — |
| Caption | DM Sans | 12–13px | 500–600 | 0.5–3px, uppercase |
| Sticker | Caveat | 18px | 600 | — |

### Typography Rules
- Headlines: `font-family: var(--font-display)` — never DM Sans for H1–H3
- Body: `font-family: var(--font-body)` at 17px, line-height 1.7
- Quotes/accents: `font-family: var(--font-serif)`, usually italic
- Stickers only: `font-family: var(--font-hand)` — **never** for body, headlines, or labels
- Section labels: DM Sans 12px, weight 600, uppercase, letter-spacing 3px, color `--coral`
- Negative letter-spacing on headlines (-0.02em to -0.04em)

---

## 4 — Components

### Buttons
```css
.btn {
  padding: 14px 28px;          /* --lg: 18px 42px */
  border-radius: var(--radius-pill);
  font-family: var(--font-body);
  font-size: 15px;             /* --lg: 1.05rem */
  font-weight: 600;
  border: 2px solid transparent;
  transition: all 0.3s var(--ease);
}
```

| Variant | Background | Text | Border | Hover |
|---------|-----------|------|--------|-------|
| Primary (`.btn--coral`) | `--coral` | white | coral | `--deep-coral`, translateY(-2px), coral shadow |
| Outline (`.btn--outline`) | transparent | `--charcoal` | `--charcoal` | — |
| Ghost | transparent | `--charcoal` | none | `--warm-white` bg |
| White | white | `--coral` | white | — |
| Dark | `--black` | white | black | — |

### Cards
```css
.card {
  border-radius: var(--radius-lg);   /* 24px */
  padding: 32px;
  background: var(--white);
  border: 1px solid var(--border);
  transition: all 0.4s var(--ease);
}
.card:hover {
  box-shadow: var(--shadow-card);
  transform: translateY(-4px);
}
```

### Tags / Pills
```css
.tag {
  padding: 6px 16px;
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 500;
}
```
Variants: `--soft-peach` bg + `--deep-coral` text, `--mint` bg + sage text, gold bg, lavender bg, neutral with border.

### Form Inputs
```css
.form-input {
  padding: 14px 18px;
  border-radius: var(--radius-md);   /* 16px */
  border: 1.5px solid rgba(30, 30, 46, 0.15);
  font-family: var(--font-body);
  font-size: 15px;
}
.form-input:focus {
  border-color: var(--coral);
  box-shadow: 0 0 0 3px rgba(232, 114, 90, 0.12);
}
```

### Navigation
- Fixed top, `backdrop-filter: blur(16px)`
- Pill-shaped CTA button (coral)
- Scrolled state adds `--shadow-nav`

---

## 5 — Website Patterns (mybookhub.de)

### Sticker Badges
Handwritten accent labels in Caveat with ✦ separator:
```css
.sticker-badge {
  padding: 8px 20px;
  border-radius: var(--radius-pill);
  font-family: var(--font-hand);
  font-size: 18px;
  font-weight: 600;
  box-shadow: var(--shadow-sticker);
  transform: rotate(-2deg);
}
```
Colors: coral, lavender, sage, gold backgrounds. Always end text with ` ✦`.

### Decorative Stars
The `✦` symbol as scattered decorative elements in accent colors (coral, gold, lavender, sage), absolutely positioned, various sizes (1rem–2rem), low opacity for subtle variants.

### Deco Dots
Small dot clusters (6px circles) in one accent color, grouped in 2–3 dots, absolutely positioned as background texture.

### Wave Dividers
Organic SVG waves between sections:
```html
<div style="position: absolute; bottom: -2px; left: 0; width: 100%;">
  <svg viewBox="0 0 1440 80" preserveAspectRatio="none" style="display:block; width:100%; height:60px;">
    <path d="M0,50 C240,10 480,70 720,30 C960,0 1200,60 1440,30 L1440,80 L0,80 Z" fill="NEXT_SECTION_BG_COLOR"></path>
  </svg>
</div>
```
Fill color = background of the following section.

### Marquee Banner
Scrolling text on coral background, Cabinet Grotesk bold, ✦ as separators:
```
Smells like fresh print. ✦ Slightly obsessed. ✦
```

### Highlight Underline
For emphasis words in headlines:
```css
.highlight {
  background: linear-gradient(to top, rgba(232,114,90,0.2) 40%, transparent 40%);
  padding: 0 4px;
}
```
Sage variant: `rgba(127,182,133,0.2)`, Gold variant: `rgba(245,176,65,0.2)`.

### Scroll Reveal
Elements enter with `opacity: 0 → 1` and `translateY(32px → 0)`, 0.7s easing, staggered delays (0.1s increments).

---

## 6 — Motion Design

| Action | Duration | Easing | Transform |
|--------|----------|--------|-----------|
| Button hover | 0.3s | `--ease` | translateY(-2px), coral shadow |
| Card hover | 0.4s | `--ease` | translateY(-4px), `--shadow-card` |
| Scroll reveal | 0.7s | `--ease` | translateY(32px → 0), opacity 0 → 1 |
| Sticker hover | 0.3s | `--ease` | rotate(0deg), scale(1.05) |
| Focus ring | 0.25s | `--ease` | 3px coral ring |

### Duration Scale
- Micro: 150ms (toggles, focus)
- Fast: 250ms (buttons, hovers)
- Normal: 400ms (cards, panels)
- Slow: 700ms (reveals, transitions)

### Rules
- Never use `ease` or `linear` — always `var(--ease)` or `var(--ease-bounce)`
- Never exceed 700ms for UI interactions
- Always use `transform` for motion (GPU-accelerated)

---

## 7 — Spacing & Layout

### Container
```css
.container { max-width: 1120px; margin: 0 auto; padding: 0 48px; }
.container--wide { max-width: 1320px; }
```

### Section Padding
- Desktop: 120px vertical
- Tablet (≤1024px): 80px
- Mobile (≤600px): 60px

### Grid Gaps
- Cards: 24px
- Large sections: 32px–48px
- Tight: 16px

### Border Radius
- Small elements (inputs, code): `--radius-sm` (12px)
- Medium cards, tooltips: `--radius-md` (16px)
- Large cards, sections: `--radius-lg` (24px)
- Buttons, pills, tags: `--radius-pill` (999px)

---

## 8 — Tone of Voice (for text content)

### Principles
| Trait | Description |
|-------|-------------|
| Nahbar | Du-Form, keine Floskeln, kein Corporate-Speak |
| Klar | Kurze Sätze, aktive Sprache, keine Füllwörter |
| Kompetent | Fachlich stark, ohne belehrend zu sein |
| Warm | Ermutigendes Wording, nie aggressiv oder drängend |

### Do's
- "Dein Buch, deine Marke"
- "Wir begleiten dich"
- "Fair beteiligt, volle Kontrolle"
- Konkret über abstrakt

### Don'ts
- Keine Superlative ("das beste", "einzigartig")
- Keine Follower-Zahlen des Creators nennen (Ausnahme: @nicolnic 2 Mio.+)
- Kein "wir sind anders als andere Verlage" — zeigen statt sagen
- Kein Feature-Dump

---

## 9 — Logo

### Canonical hosted assets

**Always link to the S3-hosted assets** — they are the single source of truth and are kept up to date. Do **not** inline the SVG path unless there is a hard reason (e.g. offline print export).

Base URL: `https://bookhub-assets.s3.eu-central-1.amazonaws.com/public-assets/`

| Asset | URL | Use case |
|---|---|---|
| Emblem (B-Bookmark) | `.../bookhub_emblem.svg` | Small brand mark, favicon-like spots, headers, standalone symbol |
| Logo (wordmark) | `.../bookhub_logo.png` | Wide contexts, footer signatures, email templates |

**Default usage:**
```html
<img src="https://bookhub-assets.s3.eu-central-1.amazonaws.com/public-assets/bookhub_emblem.svg"
     alt="Bookhub" width="72" height="72">
```

### Inline fallback

Only inline this SVG path when the asset URL is unreachable (e.g. fully offline documents):
```html
<svg viewBox="0 0 602.19 602.3" fill="currentColor">
  <path d="m602.1,457.2c-2.89,81.6-72.43,145.11-154.08,145.11H87.25c-48.19,0-87.25-39.06-87.25-87.25V87.25C0,39.06,39.06,0,87.25,0h27.12v252.55l114.48-114.48,114.37,114.48V0h91.2c81.65,0,151.19,63.5,154.08,145.11,3.03,85.66-65.49,156.04-150.48,156.04h13.59c84.99,0,153.51,70.38,150.48,156.05Z"/>
</svg>
```

### Usage Rules
- Minimum digital size: 32px
- Minimum print size: 12mm
- Clear space: 1x (bookmark width) on all sides
- Allowed backgrounds: white, black, coral, soft-peach
- Never: stretch, rotate, add shadows/glow, place on busy backgrounds
- Color: use the asset as-is. If a recolored variant is needed, upload it to the bucket (e.g. `bookhub_emblem_coral.svg`) rather than applying CSS filters.

---

## 10 — Grain Overlay

Subtle noise texture over the entire page for tactile warmth:
```css
body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.035;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 200px 200px;
}
```

---

## Quick Checklist

Before shipping any Bookhub UI:

- [ ] Colors from palette only (no #000, no random blues)
- [ ] Cabinet Grotesk for H1–H3, DM Sans for body, Lora for quotes, Caveat for stickers only
- [ ] Buttons are pill-shaped (`--radius-pill`)
- [ ] Cards use `--radius-lg` with `--border` and hover lift
- [ ] Coral is primary CTA color
- [ ] Body text 17px, line-height 1.7
- [ ] Section labels: uppercase, 12px, letter-spacing 3px, coral
- [ ] Motion uses `var(--ease)`, max 700ms
- [ ] Grain overlay present on full pages
- [ ] Dark sections use `--black` not `#000`
- [ ] Wave dividers between major sections
- [ ] ✦ decorative stars scattered where appropriate
