# Layouts reference

Every slide is a `SlideData` object with a `layout` field. All layouts accept these common fields:

```ts
{
  layout: LayoutName,
  title?: string,
  subtitle?: string,
  notes?: string,    // PowerPoint speaker notes (omitted with --no-notes)
}
```

Below is one copy-paste example per layout. Field types come from `src/types/slide.ts` in `omelet-slide-generator`.

---

## title

Cover slide. No header bar.

```ts
{
  layout: 'title',
  title: 'Sorting in Linear Time',
  subtitle: 'Counting, Radix, Bucket',
  author: 'Jane Doe',
  date: '2026-05-14',
}
```

## sectionDivider

Big colored break between sections.

```ts
{
  layout: 'sectionDivider',
  title: 'Part II — Radix Sort',
  sectionNumber: 2,
}
```

## objectives

Lecture goals. Optional `details` annotates each objective; optional `leftTitle` / `rightTitle` re-label the columns.

```ts
{
  layout: 'objectives',
  title: 'Today',
  items: [
    'Understand counting sort',
    'Analyze radix sort complexity',
    'Compare with comparison-based sorts',
  ],
  details: ['Stable, O(n+k)', 'Uses counting sort as subroutine', 'Lower bound revisited'],
}
```

## agenda

Time-stamped schedule. Items are `{ time, label, type? }`. `type` is `'lecture' | 'demo' | 'lab' | 'break' | 'discussion'`.

```ts
{
  layout: 'agenda',
  title: 'Agenda',
  items: [
    { time: '00:00', label: 'Intro',         type: 'lecture' },
    { time: '00:15', label: 'Counting sort', type: 'lecture' },
    { time: '00:45', label: 'Lab',           type: 'lab' },
    { time: '01:15', label: 'Break',         type: 'break' },
    { time: '01:30', label: 'Q&A',           type: 'discussion' },
  ],
}
```

## bullets

Plain bullet list.

```ts
{
  layout: 'bullets',
  title: 'Why linear sorts?',
  items: [
    'Bypass the Ω(n log n) comparison lower bound',
    'Require integer-keyed input',
    'Trade memory for time',
  ],
}
```

## twoColumn

Two parallel bullet lists.

```ts
{
  layout: 'twoColumn',
  title: 'Counting vs Radix',
  leftTitle: 'Counting sort',
  rightTitle: 'Radix sort',
  leftItems: ['Single pass over keys', 'O(n + k)', 'Stable'],
  rightItems: ['Multi-pass over digits', 'O(d · (n + b))', 'Stable when subroutine is'],
}
```

## threeColumn

Three parallel bullet lists. Columns are `{ heading, items: string[] }`.

```ts
{
  layout: 'threeColumn',
  title: 'Linear-time sorts',
  columns: [
    { heading: 'Counting',  items: ['O(n+k)', 'Integer keys', 'Stable'] },
    { heading: 'Radix',     items: ['O(d(n+b))', 'Fixed-width keys', 'Stable'] },
    { heading: 'Bucket',    items: ['O(n) avg', 'Uniform input', 'In-place possible'] },
  ],
}
```

## comparison

Side-by-side pros/cons style. `ComparisonColumn` is `{ heading, items, color? }` where `color` is a hex like `'10B981'`.

```ts
{
  layout: 'comparison',
  title: 'Comparison vs non-comparison sorts',
  columns: [
    { heading: 'Comparison', items: ['Ω(n log n) lower bound', 'Works on any orderable key'], color: 'EF4444' },
    { heading: 'Non-comparison', items: ['Can hit O(n)', 'Restricted key types'], color: '10B981' },
  ],
}
```

## iconGrid

Tile grid with optional [Lucide](https://lucide.dev/) icon names. `IconGridItem` is `{ icon?, label, desc? }`.

```ts
{
  layout: 'iconGrid',
  title: 'When to reach for which sort',
  items: [
    { icon: 'hash',      label: 'Counting', desc: 'Small integer range' },
    { icon: 'layers',    label: 'Radix',    desc: 'Fixed-width keys' },
    { icon: 'bucket',    label: 'Bucket',   desc: 'Uniform distribution' },
    { icon: 'gitBranch', label: 'Quick',    desc: 'General-purpose' },
  ],
}
```

## numberedCards

Numbered card grid. `NumberedCardItem` is `{ title, desc? }`.

```ts
{
  layout: 'numberedCards',
  title: 'Counting sort in 4 steps',
  items: [
    { title: 'Count occurrences', desc: 'count[x]++ for each x' },
    { title: 'Prefix sum',         desc: 'count[i] += count[i-1]' },
    { title: 'Place from right',   desc: 'Preserves stability' },
    { title: 'Copy back',          desc: 'O(n) final pass' },
  ],
}
```

## processFlow

Sequential steps. Each step is either a `string` or `{ title, desc? }`.

```ts
{
  layout: 'processFlow',
  title: 'Compile pipeline',
  steps: [
    { title: 'Lex',     desc: 'Source → tokens' },
    { title: 'Parse',   desc: 'Tokens → AST' },
    { title: 'Lower',   desc: 'AST → IR' },
    { title: 'Emit',    desc: 'IR → bytecode' },
  ],
}
```

## imageProcessFlow

Steps shown next to an image. `flows: { label, steps: ProcessStep[] }[]`.

```ts
{
  layout: 'imageProcessFlow',
  title: 'Counting sort on the array',
  imagePath: 'assets/counting-array.png',
  flows: [
    { label: 'Phase 1 — Count', steps: [{ title: 'Init count[]' }, { title: 'Tally values' }] },
    { label: 'Phase 2 — Place', steps: [{ title: 'Prefix sum' }, { title: 'Scatter from right' }] },
  ],
}
```

## timeline

Horizontal timeline. `TimelineItem` is `{ label, desc? }`.

```ts
{
  layout: 'timeline',
  title: 'History of sorting',
  items: [
    { label: '1945', desc: 'von Neumann — merge sort' },
    { label: '1959', desc: 'Shell sort' },
    { label: '1961', desc: 'Quicksort (Hoare)' },
    { label: '1964', desc: 'Heap sort (Williams)' },
  ],
}
```

## stats

Big-number tiles. `StatItem` is `{ value, label }`.

```ts
{
  layout: 'stats',
  title: 'Why we care',
  items: [
    { value: '40%',   label: 'of CPU in DB systems' },
    { value: 'O(n)',  label: 'best-case linear sort' },
    { value: '3.5×',  label: 'speedup vs quicksort on int keys' },
  ],
}
```

## table

Plain table.

```ts
{
  layout: 'table',
  title: 'Complexity table',
  headers: ['Algorithm', 'Best', 'Average', 'Worst', 'Stable'],
  rows: [
    ['Counting',  'O(n+k)',     'O(n+k)',     'O(n+k)',     'Yes'],
    ['Radix',     'O(d(n+b))',  'O(d(n+b))',  'O(d(n+b))',  'Yes'],
    ['Quick',     'O(n log n)', 'O(n log n)', 'O(n²)',      'No'],
  ],
}
```

## imageTable

Table with an image cell on the side.

```ts
{
  layout: 'imageTable',
  title: 'Sample distributions',
  imagePath: 'assets/distributions.png',
  headers: ['Input', 'Best sort'],
  rows: [
    ['Uniform',  'Bucket'],
    ['Skewed',   'Radix'],
    ['Few keys', 'Counting'],
  ],
}
```

## codeBlock

Shiki-highlighted code. `language` is a Shiki id (`ts`, `js`, `py`, `rust`, `go`, `bash`, `json`, `sql`, ...). Optional `description` renders above the code.

```ts
{
  layout: 'codeBlock',
  title: 'Counting sort',
  language: 'ts',
  description: 'Stable, O(n+k). Returns a new array.',
  code: `function countingSort(arr: number[], k: number): number[] {
  const count = new Array(k + 1).fill(0);
  for (const x of arr) count[x]++;
  for (let i = 1; i <= k; i++) count[i] += count[i - 1];
  const out = new Array(arr.length);
  for (let i = arr.length - 1; i >= 0; i--) {
    out[--count[arr[i]]] = arr[i];
  }
  return out;
}`,
  notes: 'Walk through prefix sum; stress stability comes from right-to-left placement.',
}
```

## math

Native PowerPoint OMML — fully editable in PowerPoint. Use `formulas` (an array), not a singular `formula`. Optional `variables` and `description`.

```ts
{
  layout: 'math',
  title: 'Master theorem',
  formulas: [
    { label: 'Recurrence', latex: 'T(n) = aT(n/b) + f(n)' },
    { label: 'Case 1',     latex: 'T(n) = \\Theta(n^{\\log_b a})' },
  ],
  variables: [
    'a \\geq 1: branching factor',
    'b > 1: input shrink ratio',
    'f(n): work outside recursive calls',
  ],
  description: 'Case 1 holds when f(n) = O(n^{\\log_b a - \\epsilon}) for some \\epsilon > 0.',
}
```

## image

Single full-bleed image with optional caption.

```ts
{
  layout: 'image',
  title: 'Memory layout',
  imagePath: 'assets/memory-layout.png',
  caption: 'Stack grows down; heap grows up.',
}
```

## imageText

Image plus a bullet list. `imagePosition` is `'left'` or `'right'` (default `'left'`).

```ts
{
  layout: 'imageText',
  title: 'Bucket sort idea',
  imagePath: 'assets/bucket.png',
  imagePosition: 'right',
  items: [
    'Partition input into k buckets',
    'Sort each bucket independently',
    'Concatenate buckets in order',
  ],
}
```

## quote

Pull quote.

```ts
{
  layout: 'quote',
  quote: 'Premature optimization is the root of all evil.',
  attribution: 'Donald Knuth',
}
```

## highlight

Big callout, optionally with bullets underneath.

```ts
{
  layout: 'highlight',
  title: 'Key takeaway',
  highlight: 'Comparison sorts cannot beat Ω(n log n).',
  details: [
    'Decision-tree argument',
    'Holds for any deterministic comparison sort',
  ],
}
```

## summary / recap

End-of-section summary. `summary` and `recap` are layout aliases — `recap` additionally accepts `description` and renders items as `IconGridItem[]`.

```ts
{
  layout: 'summary',
  title: 'Recap',
  items: [
    'Counting sort: O(n+k), stable, integer keys',
    'Radix sort: builds on counting; multi-digit keys',
    'Bucket sort: O(n) average on uniform inputs',
  ],
}

{
  layout: 'recap',
  title: 'Today in 4 ideas',
  description: 'Linear-time sorts swap key restrictions for the comparison lower bound.',
  items: [
    { icon: 'hash',   label: 'Counting',  desc: 'O(n+k)' },
    { icon: 'layers', label: 'Radix',     desc: 'd passes' },
    { icon: 'bucket', label: 'Bucket',    desc: 'Distribution' },
    { icon: 'lock',   label: 'Lower bnd', desc: 'Ω(n log n)' },
  ],
}
```

## labExercise

Lab brief: steps + verification + optional duration.

```ts
{
  layout: 'labExercise',
  title: 'Lab 7 — Implement counting sort',
  duration: '45 min',
  steps: [
    'Clone the lab starter repo',
    'Implement countingSort(arr, k) in src/sort.ts',
    'Run npm test',
  ],
  verify: [
    'All tests in test/sort.test.ts pass',
    'Sort is stable on equal keys',
  ],
}
```

## demo

Live demo placeholder.

```ts
{
  layout: 'demo',
  title: 'Demo — sorting 1M ints',
  items: [
    'Compare counting sort vs Array.prototype.sort',
    'Show 50× speedup on small key range',
  ],
}
```

## qna

Q&A close. No required fields.

```ts
{ layout: 'qna', title: 'Questions?' }
```
