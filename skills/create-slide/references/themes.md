# Themes reference

A theme controls colors, fonts, slide dimensions, header/footer style, and box style. Switch with `--theme=<name>` on the CLI, or `getTheme(name)` in code.

## Built-in themes

| Theme | Header | Box style | Mood |
|---|---|---|---|
| `n8n` (default) | banner (colored bar) | `filled` | Vibrant blue/purple/orange — instructor-facing |
| `minimalism` | minimal (line) | `semi-transparent` | Light, neutral, lots of whitespace |
| `midnight` | banner (colored bar) | `filled` | Dark mode, navy + cyan accent |

All three use `slideWidth: 13.33`, `slideHeight: 7.5` (16:9 widescreen).

### Color palettes (hex, no `#`)

**n8n**

| Token | Value | Use |
|---|---|---|
| `primary` | `1E40AF` | Header banner, accents |
| `primaryDark` | `1E3A8A` | Title-slide lower band |
| `secondary` | `059669` | Success / second accent |
| `accent` | `DC2626` | Highlights, warnings |
| `purple` | `6D28D9` | Optional violet accent |
| `orange` | `EA580C` | Optional warm accent |

**minimalism**

| Token | Value | Use |
|---|---|---|
| `primary` | `156082` | Subdued teal-blue |
| `secondary` | `196B24` | Forest green accent |
| `accent` | `E97132` | Warm orange highlight |
| `cyan` / `purple` / `lightGreen` | `0F9ED5` / `A02B93` / `4EA72E` | Categorical accents |

**midnight**

| Token | Value | Use |
|---|---|---|
| `primary` | `1E2761` | Deep navy banner |
| `primaryDark` | `141B45` | Title-slide lower band |
| `secondary` | `CADCFC` | Pale text on dark |
| `accent` | `0891B2` | Cyan highlight |

## ThemeConfig interface

```ts
interface ThemeConfig {
  name: string;
  colors: Colors;            // see palette tables above
  fonts: { title: string; body: string; code: string };
  slideWidth: number;        // inches
  slideHeight: number;       // inches
  header: {
    style: 'banner' | 'minimal';
    titlePosition: { x: number; y: number; w: number; h: number };
    fontSize: number;
  };
  footer: {
    style: 'line' | 'text';
    courseLabel?: string;    // overridden at runtime by ContentModule.courseLabel
  };
  logo?: {
    paths: string[];         // resolved relative to CONTENT_DIR; first existing file wins
    small: { x: number; y: number; w: number; h: number };
    large: { x: number; y: number; w: number; h: number };
  };
  boxStyle: 'filled' | 'semi-transparent' | 'bordered';
}
```

`Colors` has many optional accent slots (`purple`, `orange`, `yellow`, `cyan`, `lightGreen`, `textGray`, `boxBorder`, ...). Layouts fall back to `medium` / `border` when an accent is missing, so a custom theme only needs to fill `primary`, `primaryDark`, `secondary`, `accent`, `dark`, `medium`, `light`, `white`, `border`.

## Registering a custom theme

```ts
import { registerTheme, getTheme, PresentationBuilder } from 'omelet-slide-generator';
import type { ThemeConfig } from 'omelet-slide-generator';

const corporate: ThemeConfig = {
  name: 'corporate',
  colors: {
    primary: '0F172A',
    primaryDark: '020617',
    primaryLight: 'E2E8F0',
    secondary: '0EA5E9',
    accent: 'F59E0B',
    dark: '1E293B',
    medium: '64748B',
    light: 'F8FAFC',
    white: 'FFFFFF',
    border: 'CBD5E1',
  },
  fonts: { title: 'Inter', body: 'Inter', code: 'JetBrains Mono' },
  slideWidth: 13.33,
  slideHeight: 7.5,
  header: {
    style: 'minimal',
    titlePosition: { x: 0.5, y: 0.2, w: 12.33, h: 0.6 },
    fontSize: 28,
  },
  footer: { style: 'line' },
  boxStyle: 'bordered',
};

registerTheme(corporate);

const builder = new PresentationBuilder(getTheme('corporate'), __dirname);
```

Once registered, the CLI accepts `--theme=corporate` *only* if the registration runs before the build — i.e., from inside the content file itself, not after the CLI starts. The cleanest path is to register from the programmatic API (see `programmatic-api.md`); for CLI use, register a theme by upstreaming it to `omelet-slide-generator` (see `contributing.md`).

## Logo handling

When `theme.logo` is set, `BaseLayout.preloadLogo()` walks `paths[]` (resolved against `CONTENT_DIR`) and uses the first existing file. The title slide gets the `large` placement; every other slide gets `small`. Drop `theme.logo` entirely to disable.

## Picking a theme

| Audience | Theme |
|---|---|
| University lectures (instructor copy) | `n8n` |
| Investor / client deck | `minimalism` |
| Conference talk in a dark room | `midnight` |
| Brand-controlled corporate deck | Custom — register via `registerTheme()` and contribute upstream |
