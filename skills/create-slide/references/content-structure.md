# Content structure reference

A content file default-exports one `ContentModule`. The CLI loads it via `jiti` for `.ts` files (no build step) or `require()` for `.js`.

## ContentModule

```ts
interface ContentModule {
  slides: SlideData[];                // required — the deck

  meta?: {                            // becomes .pptx document properties
    title?: string;
    author?: string;
    subject?: string;
  };

  // Top-level shortcuts (used only when meta.* is missing)
  title?: string;
  author?: string;
  subject?: string;

  courseLabel?: string;               // footer text on every non-title slide
  notes?: Record<string, string>;     // unused by current CLI; reserved
}
```

## SlideData

The full `SlideData` is a discriminated bag — every layout reads a subset of these fields.

```ts
interface SlideData {
  layout: LayoutName;                 // required
  title?: string;
  subtitle?: string;
  notes?: string;                     // PowerPoint speaker notes

  // title slide
  author?: string;
  date?: string;

  // bullet-style layouts
  items?: (string | IconGridItem | NumberedCardItem | TimelineItem | StatItem | AgendaItem)[];

  // multi-column layouts
  columns?: (ComparisonColumn | { heading: string; items: string[] })[];
  columnCount?: number;
  leftTitle?: string;
  rightTitle?: string;
  leftItems?: string[];
  rightItems?: string[];

  // sectionDivider
  sectionNumber?: number;

  // process flows
  steps?: (string | ProcessStep)[];
  flows?: { label: string; steps: ProcessStep[] }[];

  // tables
  headers?: string[];
  rows?: string[][];

  // codeBlock
  code?: string;
  language?: string;
  description?: string;

  // math
  formulas?: { label?: string; latex: string }[];
  variables?: string[];

  // highlight
  highlight?: string;
  details?: string[];

  // image-bearing layouts
  imagePath?: string;
  imagePosition?: 'left' | 'right';
  caption?: string;

  // quote
  quote?: string;
  attribution?: string;

  // typed slides
  type?: 'qna' | 'break' | 'discussion';

  // labExercise
  duration?: string;
  verify?: string[];
}
```

Item types referenced above:

```ts
interface IconGridItem    { icon?: string; label: string; desc?: string }
interface ProcessStep     { title: string; desc?: string }
interface NumberedCardItem{ title: string; desc?: string }
interface TimelineItem    { label: string; desc?: string }
interface StatItem        { value: string; label: string }
interface AgendaItem      { time: string; label: string; type?: 'lecture' | 'demo' | 'lab' | 'break' | 'discussion' }
interface ComparisonColumn{ heading: string; items: string[]; color?: string }
```

## Multi-file decks

Long decks become unmaintainable in a single file. Split by section:

```
slides/
├── index.ts          # ContentModule wrapper
├── intro.ts          # SlideData[]
├── 01-counting.ts    # SlideData[]
├── 02-radix.ts       # SlideData[]
└── outro.ts          # SlideData[]
```

```ts
// slides/index.ts
import type { ContentModule } from 'omelet-slide-generator';
import intro from './intro';
import counting from './01-counting';
import radix from './02-radix';
import outro from './outro';

const content: ContentModule = {
  courseLabel: 'CS101 — Algorithms',
  meta: { title: 'Lecture 7 — Linear Sorts', author: 'Jane Doe' },
  slides: [...intro, ...counting, ...radix, ...outro],
};

export default content;
```

```ts
// slides/01-counting.ts
import type { SlideData } from 'omelet-slide-generator';

const slides: SlideData[] = [
  { layout: 'sectionDivider', title: 'Counting Sort', sectionNumber: 1 },
  { layout: 'objectives', title: 'In this section', items: [...] },
  // ...
];

export default slides;
```

## Speaker notes

Each `SlideData` has an optional `notes: string`. Notes appear in PowerPoint's speaker-notes pane. Build the student variant with `--no-notes` to drop them entirely.

For longer notes, use a template literal — newlines are preserved:

```ts
{
  layout: 'codeBlock',
  title: 'Counting sort',
  code: '...',
  notes: `Walk through prefix sum step.

Stress that placing from the right preserves stability — placing from the left does not.

Common pitfall: forgetting to subtract 1 before placing.`,
}
```

The `math` layout *also* writes the LaTeX source into the speaker notes (so it is recoverable if PowerPoint mangles the OMML), regardless of `--no-notes`.

## Image paths

The CLI sets `process.env.CONTENT_DIR = dirname(contentPath)` before loading the module. `ImageResolver` resolves `imagePath` relative to that directory (and walks up a couple of fallback locations for `theme.logo.paths`).

A typical layout:

```
my-deck/
├── slides/
│   ├── index.ts
│   ├── 01-counting.ts
│   └── assets/
│       ├── counting-array.png
│       └── memory-layout.png
└── package.json
```

Then in a slide:

```ts
{ layout: 'image', imagePath: 'assets/counting-array.png' }
```

Avoid absolute paths — they break when the deck is shared.
