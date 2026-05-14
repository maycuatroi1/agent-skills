# Programmatic API reference

Skip the CLI when embedding `omelet-slide-generator` into a build script, a CI pipeline, or a service. The package exports the building blocks the CLI uses internally.

## Exports

```ts
// from 'omelet-slide-generator'
export { PresentationBuilder, BuildOptions };
export { getTheme, registerTheme, n8nTheme, minimalismTheme, midnightTheme };
export { LayoutRegistry, BaseLayout };
export { CodeHighlighter, ImageResolver };
export * from './types'; // ContentModule, SlideData, ThemeConfig, Colors, Fonts, ...
```

## Minimal build

```ts
import { PresentationBuilder, getTheme } from 'omelet-slide-generator';
import content from './slides';

const builder = new PresentationBuilder(getTheme('minimalism'), __dirname);
const pptx = await builder.build(content, { noNotes: false, contentDir: __dirname });
await pptx.writeFile({ fileName: 'out.pptx' });
```

Important: the CLI also runs a **math post-processing pass** after writing the file. Skipping it leaves the `math` layout showing placeholders instead of native OMML.

## Build with native math (full pipeline)

```ts
import * as path from 'path';
import { PresentationBuilder, getTheme } from 'omelet-slide-generator';
import { MathService } from 'omelet-slide-generator/dist/services/MathService';
import { MathPostProcessor } from 'omelet-slide-generator/dist/services/MathPostProcessor';
import content from './slides';

async function build() {
  const contentDir = __dirname;
  process.env.CONTENT_DIR = contentDir;

  // Reset cross-build state — required when building multiple decks in one process
  MathService.reset();

  const theme = getTheme('minimalism');
  const builder = new PresentationBuilder(theme, contentDir);
  const pptx = await builder.build(content, { noNotes: false, contentDir });

  const outputPath = path.resolve(__dirname, 'out.pptx');
  await pptx.writeFile({ fileName: outputPath });

  const injected = await MathPostProcessor.process(outputPath);
  console.log(`Injected ${injected} OMML formula(s)`);
}

build().catch(err => { console.error(err); process.exit(1); });
```

`MathService.reset()` is critical when building many decks in the same process — it clears the placeholder counter so formula IDs do not collide across builds.

## Programmatic theme registration

`registerTheme()` mutates the package's internal theme map. Anything calling `getTheme(name)` afterwards will resolve the new theme — including the CLI, *if* the registration runs before `getTheme` is called. In practice, that means programmatic builds only:

```ts
import { registerTheme, getTheme, PresentationBuilder } from 'omelet-slide-generator';
import type { ThemeConfig } from 'omelet-slide-generator';

const corporate: ThemeConfig = { /* see references/themes.md */ };
registerTheme(corporate);

const builder = new PresentationBuilder(getTheme('corporate'), __dirname);
```

For CLI use (`--theme=corporate`), the only path is to upstream the theme — see `contributing.md`.

## Pair build (instructor + student)

```ts
async function pairBuild(content, theme, basePath) {
  const builder = new PresentationBuilder(theme, basePath);

  MathService.reset();
  const instructor = await builder.build(content, { noNotes: false, contentDir: basePath });
  await instructor.writeFile({ fileName: `${basePath}/lecture.pptx` });
  await MathPostProcessor.process(`${basePath}/lecture.pptx`);

  MathService.reset();
  const student = await builder.build(content, { noNotes: true, contentDir: basePath });
  await student.writeFile({ fileName: `${basePath}/lecture-student.pptx` });
  await MathPostProcessor.process(`${basePath}/lecture-student.pptx`);
}
```

## Returned object

`builder.build()` returns a `PptxGenJS` instance. Beyond `writeFile`, anything from the [pptxgenjs API](https://gitbrent.github.io/PptxGenJS/) is fair game — adding extra slides, tweaking master slides, etc. — but the result is no longer round-trippable through the content-module format.

## Layout extensibility (advanced)

`BaseLayout` is exported, so a downstream project can subclass it and register the new layout into a fresh `LayoutRegistry`. The library does not expose a public hook to inject custom layouts into `PresentationBuilder` without subclassing it. For most cases, the right move is to add the layout upstream — see `contributing.md`.
