# Layout Guide

Use this guide to create an original Chinese public-account comic long image with a familiar educational-comic reading rhythm.

## High-Level Traits

- Narrow vertical canvas around 600px wide.
- White background with generous top, side, and vertical whitespace.
- The WeChat article title is not part of the long image; start from the first body beat, section label, badge, or opening panel.
- Short Chinese paragraphs centered on the page; avoid dense prose.
- Explanatory sequence alternates between text and large illustrations.
- Section headings are bold, direct, and conversational.
- Orange callout blocks provide jokes, objections, or narrator comments outside panel art.
- Some panels are colored scenes; some are black-and-white line cartoons.
- Use simple recurring narrator/reader characters, but create original characters for each project.

For multi-style work, read `style-guide.md` first and then apply this document only for shared mobile-readability rules.

## Article Structure

1. Hook: 1-2 short paragraphs naming the reader's problem.
2. Setup panel: one relatable scene or dialogue.
3. Main heading: "首先/其次/最后，你会..."
4. Explanation beat: paragraph plus metaphor panel.
5. Counterintuitive beat: a short callout or joke.
6. Summary diagram: simple flow, timeline, or checklist.
7. Ending: practical takeaway or punchline.

## Copy Style

- Conversational, lightly funny, but not slang-heavy.
- Prefer concrete everyday scenes over abstract claims.
- Keep most text blocks under 45 Chinese characters per visual line.
- Use bold headings sparingly; one heading per major beat.
- Avoid copying catchphrases, character names, brand marks, and signatures from any reference.

## Style-Specific Layout Blocks

- `text_bars`: stacked colored narration bars, best for `蓝栏柔彩漫画`.
- `emphasis`: large centered thesis text, usually red in `蓝栏柔彩漫画`.
- `section_label`: outlined section titles or takeaways, best for `绿底粗线漫画`.
- `framed_image`: black rounded comic panels, best for `绿底粗线漫画`.

## Prompt Notes

Follow the selected style profile's `text_policy`.

- For `wordless` styles, ask the image model for no text in panel art. Chinese article body text, section labels, and dialogue should be placed in separate outside-layout text blocks for reliable rendering.
- For `model-rendered` styles, every in-panel label, dialogue, bubble, chat message, caption, or sound effect must be quoted in the prompt and rendered directly by the image model. The WeChat article title is never in-panel text. Do not add deterministic `speech_bubbles` or `framed_image.header` overlays afterward; the layout script rejects those fields.

When a chart, family tree, or timeline is needed in a `wordless` style, generate only the illustration background or icons, then place exact labels as separate layout blocks or use a dedicated deterministic chart renderer outside the comic panel image.
