---
name: generate-image
description: Generate images using Google Gemini API via omelet CLI. Use when the user asks to create, generate, or make an image, illustration, diagram, or featured image for a blog post.
argument-hint: <prompt or --blog "topic">
allowed-tools: Bash(omelet generate-image *), Bash(omelet genimg *)
---

# Generate Image with Omelet CLI

Generate images using Google Gemini API. Supports free-form prompts and blog-specific featured images with style presets.

## Prerequisites

- `omelet` CLI installed (`pip install omelet`)
- Google API key configured in `~/.omelet.json` or `GOOGLE_API_KEY` env var (if not set, the CLI will prompt interactively)

## Usage

### Blog featured image (most common)

Generate a styled featured image for a blog post:

```bash
omelet generate-image --blog "Topic Name" --style academic -o path/to/featured.png
```

### Free-form image generation

Generate an image from any text prompt:

```bash
omelet generate-image "Your detailed prompt here" output.png
```

### Available styles for blog images

| Style | Description |
|-------|-------------|
| `academic` | Black & white line art, textbook figure style (default) |
| `tech` | Dark blue/purple gradient, glowing geometric elements |
| `minimal` | Clean white background, simple line art |
| `colorful` | Vibrant gradients, bold colors, eye-catching |

## When generating images

1. **Determine the type**: Is this a blog featured image or a custom illustration?
2. **Choose the right style**: Match the style to the blog's tone
3. **Write a descriptive prompt**: For custom images, be specific about layout, elements, and style
4. **Place the output**: Save to the blog's directory (e.g., `./blog-name/featured.png`)

### Prompt tips for custom images

- Describe the layout explicitly (left/right, top/bottom, flowchart)
- List all elements and labels needed
- Specify the visual style
- For academic diagrams, include "Figure X:" caption requests

### Example: Blog featured image

```bash
omelet generate-image --blog "Docker Security" --style academic -o docker-security/featured.png
```

### Example: Custom diagram

```bash
omelet generate-image "Academic textbook diagram showing microservice architecture: API Gateway on the left connecting to 3 services (Auth, Users, Orders) on the right, each with its own database below. Style: Black and white line art, clean white background. Include 'Figure 1: Microservice Architecture' caption at bottom." microservices/architecture.png
```

After generating, add to the markdown file:

```markdown
![Descriptive alt text](./featured.png)
```
