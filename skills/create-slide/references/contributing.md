# Contributing to omelet-slide-generator

`omelet-slide-generator` is **MIT-licensed and open source**: https://github.com/maycuatroi1/omelet-slide-generator. Local hacks become the next maintainer's problem — upstream them.

This guide lists the exact files to touch for the three most common contributions.

## Add a new layout

Goal: support `layout: 'cardCarousel'` (or whatever).

1. **Type** — extend `LayoutName` in `src/types/slide.ts`:
   ```ts
   export type LayoutName = | 'title' | /* ... */ | 'cardCarousel';
   ```
2. **Fields** — if the layout reads new fields, add optional properties to `SlideData` in the same file. Reuse existing item interfaces when possible (`IconGridItem`, `ProcessStep`, ...). Add new item interfaces alongside the existing ones.
3. **Layout class** — create `src/layouts/CardCarouselLayout.ts`:
   ```ts
   import PptxGenJS from 'pptxgenjs';
   import { SlideData } from '../types';
   import { BaseLayout } from './BaseLayout';

   export class CardCarouselLayout extends BaseLayout {
     protected renderContent(slide: PptxGenJS.Slide, data: SlideData, _slideNum: number): void {
       // use this.C (colors), this.F (fonts), this.W / this.H (slide dims)
       // call this.addBox(slide, x, y, w, h) for themed boxes
     }
   }
   ```
   Override `addHeader`, `showFooter`, or `protected addFooter` only when needed (see `TitleLayout.ts` for an example of suppressing both).
4. **Registry** — register in `src/layouts/index.ts`:
   - Import the class
   - Add it to `LAYOUT_MAP`
   - Re-export it
5. **README** — add a row to the layouts table.
6. **Self-test** — write a small content file using the new layout and run `npm run dev -- test/example.ts /tmp/out.pptx`. Open in PowerPoint to verify.

## Add a new theme

Goal: support `--theme=corporate`.

1. **File** — copy `src/themes/minimalism.ts` → `src/themes/corporate.ts`. Tune `colors`, `fonts`, `header`, `footer`, `boxStyle`. Set `name: 'corporate'`.
2. **Registry** — register in `src/themes/index.ts`:
   ```ts
   import { corporateTheme } from './corporate';
   const themes: Record<string, ThemeConfig> = {
     n8n: n8nTheme,
     minimalism: minimalismTheme,
     midnight: midnightTheme,
     corporate: corporateTheme,
   };
   export { /* ... */ corporateTheme };
   ```
3. **README** — list the theme in the Themes section.

Most layouts pull from `primary`, `primaryDark`, `secondary`, `accent`, `dark`, `medium`, `light`, `white`, `border`. Optional accents (`purple`, `orange`, `cyan`, etc.) are used by `iconGrid`, `comparison`, and `stats` to pick categorical colors — fill them when the theme should look polished on those layouts.

## Add a new field to an existing layout

Goal: let `codeBlock` accept `lineHighlight: number[]`.

1. **Field** — add `lineHighlight?: number[]` to `SlideData` in `src/types/slide.ts`.
2. **Consume it** — read `data.lineHighlight` in `src/layouts/CodeBlockLayout.ts`. Be defensive about missing values (existing decks must keep working).
3. **README** — note the field on the layout's row.

## Repository conventions

- **TypeScript first.** `npm run build` runs `tsc`. The CLI's `npm run dev` uses `ts-node` for a quick edit-run loop.
- **No external test framework yet.** Smoke-test new layouts by building a sample deck and opening it in PowerPoint.
- **Keep `dist/` out of git.** It is built from `prepare` on install; tagged releases ship `dist/` automatically because of the `files` field in `package.json`.
- **Cut a release** by bumping `version` in `package.json` and tagging — `git tag v0.2.0 && git push --tags`. Pinned consumers use `github:maycuatroi1/omelet-slide-generator#v0.2.0`.

## PR checklist

- [ ] Layout / theme registered in the index
- [ ] `LayoutName` (and `SlideData`) extended in `src/types/slide.ts`
- [ ] README updated (layouts table or themes section)
- [ ] Built locally (`npm run build`)
- [ ] Tested by generating a `.pptx` and opening it in PowerPoint
- [ ] Backwards compatible — no required fields added to existing layouts
