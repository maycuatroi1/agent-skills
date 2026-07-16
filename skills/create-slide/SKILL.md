---
name: create-slide
description: This skill should be used when the user asks to "create a slide", "make a deck", "tạo slide", "tạo presentation", "build pptx", "generate PowerPoint", "make a lecture deck", or mentions building a `.pptx` from TypeScript content, lecture slides, or instructor decks. Wraps the open-source `omelet-slide-generator` CLI (28 layouts, 3 themes, native OMML math, Shiki code highlighting) so a content file can be authored and rendered to `.pptx` in one shot.
version: 0.1.0
---

# create-slide

Generate `.pptx` slide decks from a TypeScript content file using [`omelet-slide-generator`](https://github.com/maycuatroi1/omelet-slide-generator) — an MIT-licensed open-source CLI built around `pptxgenjs`. If a needed layout or theme is missing, contribute it upstream rather than forking locally.

## When to use

Trigger on any of:
- A user asks to build a slide deck, lecture deck, or instructor/student PowerPoint.
- A `.pptx` output is required from structured content (course outline, agenda, code walkthroughs, math).
- An existing TypeScript content module needs to be re-rendered with a different theme or as a no-notes student variant.

Skip when:
- Output must be Google Slides, Keynote, PDF, or HTML — this skill only emits `.pptx`.
- The user wants raw `pptxgenjs` control over every shape — use `pptxgenjs` directly instead.

## Quick start

Run from the directory holding the content file. No install step is needed; `npx` builds the CLI on first use (~30s).

```bash
npx github:maycuatroi1/omelet-slide-generator slides/index.ts deck.pptx --theme=minimalism
```

Pin to a release tag for reproducible builds: `npx github:maycuatroi1/omelet-slide-generator#v0.1.0 ...`.

Bootstrap a fresh deck from scratch with the bundled helper:

```bash
bash scripts/init-deck.sh ./my-lecture
```

This drops a working `slides/index.ts`, a `package.json` with `omelet-slide-generator` pinned, and an `npm run build` shortcut into `./my-lecture`.

## Content file shape

A content file is a `.ts` (or `.js`) module that default-exports one `ContentModule`:

```ts
import type { ContentModule } from 'omelet-slide-generator';

const content: ContentModule = {
  courseLabel: 'CS101 — Algorithms',
  meta: { title: 'Sorting in Linear Time', author: 'Jane Doe', subject: 'Lecture 7' },
  slides: [
    { layout: 'title', title: 'Sorting in Linear Time', subtitle: 'Counting, Radix, Bucket', author: 'Jane Doe', date: '2026-05-14' },
    { layout: 'objectives', title: 'Today', items: ['Counting sort', 'Radix sort', 'Bucket sort'] },
  ],
};

export default content;
```

Required: `slides[]`. Optional: `meta` (becomes `.pptx` document properties), `courseLabel` (footer text on every non-title slide).

Split a long deck across files by importing arrays of `SlideData` from sibling modules — see `references/content-structure.md`.

## CLI

```
omelet-slide <content-file> <output.pptx> [options]

Options:
  --theme=<name>     n8n | minimalism | midnight   (default: n8n)
  --no-notes         Build student variant (omits speaker notes)
  -h, --help
```

Conventional pair-build for instructor + student:

```bash
npx omelet-slide slides/index.ts lecture7.pptx --theme=minimalism
npx omelet-slide slides/index.ts lecture7-student.pptx --theme=minimalism --no-notes
```

The CLI sets `CONTENT_DIR` to the content file's directory, so any `imagePath` in slides resolves relative to the content file (not the current working directory).

## Layouts at a glance

Set `layout: '<name>'` on each slide. All 28 layouts accept `title`, `subtitle`, and `notes`.

| Layout | Required fields | Use for |
|---|---|---|
| `title` | `title` | Cover slide (`subtitle`, `author`, `date` optional) |
| `sectionDivider` | `title` | Section break (`sectionNumber` optional) |
| `objectives` | `items: string[]` | Lecture goals |
| `agenda` | `items: AgendaItem[]` | Time-stamped schedule |
| `bullets` | `items: string[]` | Plain bullet list |
| `twoColumn` | `leftItems`, `rightItems` | Parallel bullet lists (`leftTitle`, `rightTitle` optional) |
| `threeColumn` | `columns: {heading,items}[]` | Three parallel lists |
| `comparison` | `columns: ComparisonColumn[]` | Pros/cons style |
| `iconGrid` | `items: IconGridItem[]` | Icon + label tiles (lucide icons) |
| `numberedCards` | `items: NumberedCardItem[]` | Numbered card grid |
| `processFlow` | `steps: (string\|ProcessStep)[]` | Sequential steps |
| `imageProcessFlow` | `flows: {label, steps}[]`, `imagePath` | Steps next to image |
| `timeline` | `items: TimelineItem[]` | Horizontal timeline |
| `stats` | `items: StatItem[]` | Big-number statistics |
| `table` | `headers`, `rows` | Plain table |
| `imageTable` | `headers`, `rows`, `imagePath` | Table beside image |
| `codeBlock` | `code`, `language` | Shiki-highlighted code |
| `math` | `formulas: {label?, latex}[]` | Native OMML math (editable in PowerPoint) |
| `image` | `imagePath` | Single image (`caption` optional) |
| `imageText` | `imagePath`, `items` | Image + bullet text (`imagePosition: 'left'\|'right'`) |
| `quote` | `quote` | Pull quote (`attribution` optional) |
| `highlight` | `highlight` | Big callout (`details: string[]` optional) |
| `summary` / `recap` | `items` | End-of-section recap |
| `labExercise` | `steps`, `verify` | Lab brief (`duration` optional) |
| `demo` | `items: string[]` | Live demo placeholder |
| `qna` | — | Q&A close |

For a worked example of every layout, including all field shapes (`AgendaItem`, `IconGridItem`, `ComparisonColumn`, etc.), see **`references/layouts.md`**.

## Themes

Three built-in themes — pick with `--theme=<name>`:

- **`n8n`** — vibrant orange/purple, banner header (default)
- **`minimalism`** — light, neutral, lots of whitespace, minimal header
- **`midnight`** — dark mode

A theme governs colors, fonts, header/footer style, slide dimensions, and box style. Themes are registered via `registerTheme()` from the package's main entry — see **`references/themes.md`** for the full `ThemeConfig` interface and a copy-paste template for a new theme.

## Math (native OMML)

The `math` layout renders LaTeX as **native PowerPoint OMML** (editable in PowerPoint, not an image). Provide an array of `formulas`:

```ts
{
  layout: 'math',
  title: 'Master theorem',
  formulas: [
    { label: 'Recurrence', latex: 'T(n) = aT(n/b) + f(n)' },
    { label: 'Case 1', latex: 'T(n) = \\Theta(n^{\\log_b a})' },
  ],
  variables: ['a \\geq 1: branching factor', 'b > 1: input shrink ratio'],
  description: 'Holds when f(n) = O(n^{\\log_b a - \\epsilon})',
}
```

The CLI runs a post-processing pass after writing the `.pptx` to inject OMML XML — that's why the build prints `Injected N native OMML formula(s)`.

## Code highlighting

`codeBlock` uses [Shiki](https://shiki.style/) with VS Code-grade themes. Pass `language` as a Shiki id (`ts`, `js`, `py`, `rust`, `go`, `bash`, `json`, ...). An optional `description` renders above the code block.

## Images

Place image files alongside the content file (or in subfolders). Reference by path **relative to the content file**:

```ts
{ layout: 'image', title: 'Architecture', imagePath: 'assets/arch.png', caption: 'Three-tier' }
```

The CLI exports `CONTENT_DIR=<dirname(contentPath)>` before loading, so paths resolve from there regardless of the shell's `cwd`.

## Programmatic API

Skip the CLI when embedding into a build script:

```ts
import { PresentationBuilder, getTheme } from 'omelet-slide-generator';
import content from './slides';

const builder = new PresentationBuilder(getTheme('minimalism'), __dirname);
const pptx = await builder.build(content, { noNotes: false, contentDir: __dirname });
await pptx.writeFile({ fileName: 'out.pptx' });
```

Caller-side OMML injection requires the same post-processing pass the CLI does — see **`references/programmatic-api.md`** for the full pattern (including math post-processing) and a registerable custom-theme example.

## Contributing back

`omelet-slide-generator` is **MIT-licensed and open source** (https://github.com/maycuatroi1/omelet-slide-generator). When a needed layout, theme, or feature is missing, prefer upstreaming over local hacks:

1. **Missing layout** — add `src/layouts/<Name>Layout.ts` extending `BaseLayout`, register it in `src/layouts/index.ts` (`LAYOUT_MAP`), extend `LayoutName` in `src/types/slide.ts`, and add fields to `SlideData`. Open a PR.
2. **Missing theme** — copy `src/themes/minimalism.ts`, tune colors/fonts, register in `src/themes/index.ts`. Open a PR.
3. **Missing field on a layout** — extend `SlideData` in `src/types/slide.ts` and consume it in the layout class. Open a PR.

Contribution checklist lives in **`references/contributing.md`** with the exact files to touch.

## Bundled resources

### Scripts

- **`scripts/init-deck.sh`** — Bootstrap a new deck directory with `package.json` (pinned to a release tag), a starter `slides/index.ts`, and an `npm run build:instructor` / `npm run build:student` pair. Usage: `bash scripts/init-deck.sh <target-dir> [theme]`.
- **`scripts/build-deck.sh`** — Convenience wrapper around `npx omelet-slide` that builds both instructor and student variants in one call. Usage: `bash scripts/build-deck.sh <content-file> <output-prefix> [theme]`.

### References

- **`references/layouts.md`** — Full catalog of all 28 layouts with field shapes and a copy-paste example for each.
- **`references/themes.md`** — `ThemeConfig` interface, the three built-in palettes, and a template for registering a custom theme.
- **`references/content-structure.md`** — `ContentModule` / `SlideData` interfaces, multi-file deck layout, speaker-notes conventions.
- **`references/programmatic-api.md`** — `PresentationBuilder` usage, math OMML post-processing, embedding into a build pipeline.
- **`references/contributing.md`** — Step-by-step for contributing a new layout, theme, or field upstream.

### Assets

- **`assets/starter-slides.ts`** — Minimal working content file copied by `init-deck.sh`.
- **`assets/package.template.json`** — Pinned `package.json` template copied by `init-deck.sh`.
