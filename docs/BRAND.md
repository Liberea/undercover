# Brand

## Principles

- Dark is the stage. Most of every screen stays violet-black and neutral.
- One brand gradient, terracotta to indigo. Every other accent comes from it.
- Color is rationed: for the main action and the one key figure in a section.
- Hierarchy comes from size and brightness, not weight. Headings use the regular weight.
- Outlines are white hairlines at low opacity, never a color of their own.
- Every text and background pair reaches at least 4.5:1 contrast.

## Fonts

- **Headings and body**: Geist, regular (400) for headings, 600 only for a key word
- **Code, numbers, money and identifiers**: Geist Mono
- Never let the browser fake a weight (`font-synthesis: none`)

Sizes are whole pixels on the scale 13 / 14 / 15 / 16 / 17 / 18 / 20 / 22 / 24 / 28. Body text is 16 px with line height 1.55.

## The brand gradient

```
linear-gradient(135deg in oklch, #af5c2c 0%, #3846e5 100%)
```

Use it for the primary button and the product name, with white text on it. Never put dark text on the gradient.

## Colors

Two sets of accents. They are not interchangeable.

| Role | On dark | On light |
|---|---|---|
| Accent warm | `#c9793f` | `#af5c2c` |
| Accent cool (links, status messages) | `#7d87f5` | `#3846e5` |
| Accent mid (the gradient's magenta) | `#d36aa8` | `#aa358d` |
| Information | `#5fb8d6` | `#1f6f8b` |
| Alert | `#ef6b7f` | `#c0304a` |

When three things sit side by side, such as a claim's states or chart series, use warm, mid and cool in that order. Add Information fourth and Alert fifth. Alert is only for things that need a handler's attention.

## Text

| Role | On dark | On light |
|---|---|---|
| Headings, key words | `#ffffff` | `#0e0918` |
| Body | `#d1cece` | `#0e0918` |
| Muted (labels, hints, placeholders) | `#9d9797` | `#5c5566` |

Never use pure white for body text on dark.

## Surfaces

- **Dark mode (default)**: page `#0e0918`, cards `rgba(14, 9, 24, 0.96)`, inputs `#1a1624`
- **Light mode**: page `#f4f2f7`, white cards and inputs
- Raise a surface with translucent white on top (3%, 6%, 10%), not with a lighter color
- Outlines: white at 15% on dark (20% for emphasis), `rgba(14, 9, 24, 0.12)` on light
- Card shadow on dark: `0 10px 24px rgba(0,0,0,0.23)` with an inner `0 1px 0 rgba(255,255,255,0.05)`
- Radius: 9 px for buttons and inputs, 18 px for cards, full round for pills and the top bar
- Secondary button: flat `#39373d` with white text; quiet button: white 3% fill with a hairline

Brand-colored text on light backgrounds sits on white cards, since the warm accent is below 4.5:1 on the light page.

## Avoid

- A second brand gradient or a second brand color
- Bold headings
- Borders in their own color, and borders on one edge of a panel
- Lightened accents on light backgrounds, or the gradient ends as text on dark
- Blur behind surfaces as a way to show depth
- Glow, star fields and heavy gradient fills on working screens such as the claims queue

## Tone

Plain business English in US spelling. Short labels, no jargon and no exclamation marks. Money is in US dollars, such as $1,250.00.
