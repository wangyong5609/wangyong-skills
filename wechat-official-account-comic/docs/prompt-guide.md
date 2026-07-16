# Panel Prompt Guide

Read this file only after copy and storyboard are complete. Load the selected `styles/<style-id>.json` profile before writing prompts.

## Contents

1. Prompt construction
2. Wordless policy
3. Model-rendered policy
4. Style-specific rules
5. Prompt QA

## 1. Prompt Construction

Create one prompt per storyboard row. Include:

- use case and asset type;
- one specific scene and action;
- composition, subject scale, background density, and mobile readability;
- selected profile's `style_prompt`;
- people/anatomy requirements when applicable;
- exact quoted text and placement only for `model-rendered` profiles;
- negative constraints and the row's failure gate.

Prefer one clear central subject, generous padding, a readable background, and no tiny critical details. Do not put the WeChat article title into a panel prompt.

## 2. Wordless Policy

For `暖白手绘漫画`, `蓝栏柔彩漫画`, or any `text_policy: wordless` profile, include an explicit rule equivalent to:

```text
WORDLESS IMAGE ONLY. No Chinese, English, letters, numbers, captions, speech text, sound effects, labels, poster text, UI text, watermark, logo, signature, or QR code. Screens, papers, signs, books, clocks, whiteboards, and product surfaces must be blank or abstract.
```

Keep all exact reader-facing Chinese in deterministic layout blocks. A wordless panel fails if any accidental written mark appears.

For people, require complete coherent figures: one head per person, readable face, neck, torso, arms, hands, legs, feet, natural joints, posture, and scale. Reject duplicate heads, floating facial parts, detached hair, fused bodies, extra/missing limbs, broken hands, or rough storyboard texture.

## 3. Model-Rendered Policy

For `绿底粗线漫画`, 小林-family styles, or any `text_policy: model-rendered` profile:

- Wrap every intended string in double quotation marks.
- Name the location of each string: title bar, bubble, chat box, time tag, sound effect, or lower caption area.
- Ask the model to copy quoted Chinese exactly without rewriting, shortening, synonyms, dropped characters, English, pinyin, or extra labels.
- State that only quoted strings may appear.
- Keep lines short; manually compare every generated character to the approved copy.

Do not put non-rendered instructions in quotation marks. Any quoted string is treated as text that must appear in the image.

## 4. Style-Specific Rules

### 暖白手绘漫画

Use polished original educational illustration, clean hand-drawn ink, restrained warm colors, white or soft pastel space, simple readable scenes, and emotionally clear expressions. Prefer landscape or moderate-height 4:3 panels; avoid a single panel filling an entire phone screen.

Reject text, malformed people, dirty gray sketching, low-quality drafts, inconsistent style, mascot/blob people, horror mood, cramped scenes, or copied identities.

### 蓝栏柔彩漫画

Use soft psychological longform illustration: warm counseling rooms or outdoor metaphors, clean thicker hand-drawn lines, restrained warm flat color with a light watercolor wash, and quiet relationship-healing emotion. Panels are wordless. Blue narration bars, yellow emphasis, and red thesis lines belong to layout, not generated images.

Avoid glossy anime, photorealism, 3D, copied faces/clothing, account titles, or forced recurring characters in every metaphor.

### 绿底粗线漫画

Use rough thick black outlines, lightly wobbly ink, paper-grain flat colors, expressive Chinese office workers, dense but readable workplace scenes, and a muted grass-green/blue/mustard/brown/orange palette.

Render all in-panel title bars, bubbles, chats, timestamps, sound effects, and emphasized words directly in the image. Quote each exact string and specify its location. Layout should stack finished panels; do not add replacement in-panel dialogue overlays.

Forbid unquoted text, random UI labels, English, pinyin, wall text, watermarks, logos, signatures, and garbled characters.

### 小林-Family Styles

Each prompt must create one complete source image as one bitmap: a small upper/middle watercolor or doodle scene plus a lower handwritten Chinese caption area.

Include a block like:

```text
Text to render exactly:
"第一行"
"第二行"
"第三行"
```

Describe lettering as large black handwritten Chinese brush/marker lettering with dense ink, uneven thick-and-thin strokes, rough dry-brush edges, organic imperfect shapes, centered 2-5 lines, and generous line spacing. It must not look like Songti, Heiti, Kaiti, PingFang, a system font, subtitles, or clean vector calligraphy.

Forbid QR codes, signatures, account names, logos, watermarks, English, random numbers, badges, and all unquoted text. Number badges are added by layout.

- `小林诗意治愈`: quiet nature/metaphor watercolor, sparse scene, gentle affirmation, 3-6 beats.
- `小林生活讽刺`: ordinary people, daily props, awkward posture, rough black-brown lines, low-saturation dirty watercolor, understated punchline, 5-8 beats.
- `小林奇想涂鸦`: small cute animals, odd creatures, personified objects, colored wash squares, white space, light absurd twist, 6-10 beats.

If a 小林 result is too polished or full, request a smaller illustration mass, more white paper margin, looser uneven washes, rougher texture, and less polished rendering. If Chinese is wrong, shorten lines and regenerate only that panel.

## 5. Prompt QA

Before saving `panel-prompts.json`, verify:

- prompt count equals storyboard row count;
- numbering and approved copy match exactly;
- each prompt uses only the selected style profile;
- the article title appears nowhere in panel prompts;
- `wordless` prompts forbid all text;
- `model-rendered` prompts quote every required string and forbid unquoted text;
- each prompt contains a concrete failure gate;
- references are omitted unless training, comparison, editing, or continuity explicitly requires them.
