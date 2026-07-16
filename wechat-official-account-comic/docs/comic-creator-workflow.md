# Comic Creator Workflow

Read this file for every comic production request before writing copy, prompts, images, or layout. Run the stages in order. A later stage cannot repair a skipped earlier stage.

## Contents

1. Workflow state and stop rules
2. Beginner topic selection
3. Topic and thesis
4. Article title metadata
5. 小林 interactive branch
6. Copy draft
7. Panel count and storyboard
8. Prompt generation
9. Image QA
10. Layout and final QA

## 1. Workflow State And Stop Rules

Track `BRIEF -> COPY -> STORYBOARD -> PROMPTS -> PANELS -> LAYOUT -> FINAL_QA`.

- Mark a state `PASS` only when its required artifact exists and has been checked.
- Resume from the first incomplete state when files from an earlier run already exist.
- If a state requires user confirmation, present that state and end the turn. Do not call image generation while confirmation is pending.
- For non-小林 styles, an explicit request to directly generate authorizes uninterrupted execution, but does not authorize skipping stage artifacts or QA.
- For 小林-family styles, the confirmation sequence is mandatory even when the user requests direct generation.

## 2. Beginner Topic Selection

When the user is new, vague, or only says they want a comic, start with a guided topic menu. Do not draft final copy, storyboard, image prompts, images, or `article.json` yet.

First explain the supported theme families:

- 情绪疗愈 / 自我关怀: anxiety, guilt, burnout, slowing down, loving yourself.
- 日常生活 / 关系观察: family, friendship, middle-age pressure, everyday choices.
- 职场成长 / 效率习惯: workplace contrast, career fatigue, communication, time management.
- 知识科普 / 健康常识: practical explanations, food/sleep/body rhythms, life science.
- 亲子家庭 / 成长教育: parent-child communication, family roles, learning habits.
- 奇想哲思 / 轻幽默: animals, objects, tiny absurd metaphors, soft punchlines.

Then recommend 3-5 concrete topics or angles. Each recommendation should include:

- A short topic name.
- The reader it fits.
- The recommended style.
- Why it fits the user's seed.

Style matching:

- `暖白手绘漫画`: broad educational, everyday knowledge, gentle self-care.
- `蓝栏柔彩漫画`: psychology, relationship repair, emotional explanation.
- `绿底粗线漫画`: workplace comparison and punchy career scenes.
- `小林诗意治愈`: poetic affirmation and quiet emotional healing.
- `小林生活讽刺`: everyday pressure, family/workplace satire, ordinary people.
- `小林奇想涂鸦`: cute object/animal metaphors and light philosophical one-liners.

For a broad seed such as `好好过日子，好好爱自己`, recommend angles like self-care, slowing down, emotional boundaries, ordinary daily rituals, and quiet confidence. Ask the user to choose one, combine several, or provide their own. Continue only after the user confirms the theme and style.

## 3. Topic And Thesis

Define the editorial brief before writing:

- Topic: what the comic is about.
- Thesis: the one sentence the reader should remember.
- Reader: who should feel seen.
- Emotion: comfort, surprise, clarity, motivation, humor, or release.
- Ending: what the reader should believe, feel, or do after reading.

Do not start from image prompts. Start from what the comic wants to say.

## 4. Article Title Metadata

Generate 5-10 title candidates for the WeChat article title field only. The selected title is metadata, not image content.

Rules:

- Do not put the article title into generated panel images.
- Do not put the article title into `article.json`.
- Do not create a `title` block for normal production.
- Do not include the article title in `Text to render exactly`.
- Use the title only for the WeChat title field, output folder/file names, and internal planning notes.

Useful title formulas:

- `状态 + 判断`: 平和的你，才最美丽
- `痛点 + 真相`: 你不是不努力，你只是太紧了
- `反差 + 答案`: 越想赢的人，越需要先慢下来
- `人群 + 场景`: 给总是自责的你
- `问题 + 反常识`: 为什么你越懂事，越容易委屈
- `对比结构`: 上班第一年 vs 上班第五年
- `温柔承诺`: 你一定会慢慢好起来

Choose the title that matches the topic and style, then keep it outside the long image.

## 5. 小林独立金句式漫画流程

Use this branch for `小林诗意治愈`, `小林生活讽刺`, and `小林奇想涂鸦`.

These styles are not continuous story comics. A finished article is a set of independent numbered image-caption units around one topic. Each unit must be understandable on its own: one approved caption, one visual metaphor, one complete generated source image.

Mandatory confirmation gates; never combine two gates into one turn:

- **主题/风格确认**: require the user's comic topic. If the user asks for a `小林` comic but does not specify style 1, 2, or 3, recommend the closest style and wait for confirmation.
- **金句组确认**: before image prompts, draft a beat table with `编号`, `caption 行`, `核心意思`, `视觉隐喻`, and `画面方向`. The caption lines are the final reader-facing handwritten text. Wait for user confirmation before writing prompts.
- **prompt 确认**: after the beat table is approved, write one complete prompt per beat. Include `Text to render exactly` with every approved caption line in double quotation marks. Wait for user confirmation before generating images.
- **图片验收**: after generation, review each numbered image with the user. Regenerate only failed image numbers. Do not create `article.json`, reorder panels, or stitch the long image until all images pass.

After all images are accepted, keep the approved beat order as the default order. Reorder only when the user explicitly requests it. Then build a `badge` + `image` layout from the accepted panels.

## 6. Copy Draft

Write the comic copy before deciding prompts. The copy draft should include:

- Opening hook: the first sentence or two shown inside the long image.
- Beat copy: the exact text for each numbered beat or section.
- Caption lines: for `小林`-family styles, the exact handwritten caption lines that each source image must contain.
- Outside text: text rendered by the layout script outside panels.
- In-image text: text that the image model must draw inside the generated panel, only when the selected `text_policy` requires it.
- Ending line: the final emotional or practical takeaway.

At this stage, do not generate images. First decide what every reader-facing line says.

## 7. Panel Count And Storyboard

After the copy is approved, decide how many images the comic needs. Each image must have a reason to exist.

Create a storyboard table with one row per image:

- Image number.
- Copy beat: which paragraph, caption, or section this image supports.
- Purpose: setup, contrast, metaphor, punchline, proof, transition, or ending.
- Scene: what the reader sees.
- Composition: subject size, camera distance, background density, white-space needs.
- Required text: exact quoted strings for `model-rendered` styles; empty for `wordless` styles.
- Prompt seed: visual nouns, character action, props, mood, and style-specific constraints.
- Failure gate: what would make this image unacceptable.

Only after the storyboard is complete should the Agent generate image prompts.

## 8. Prompt Generation

Turn each storyboard row into one image prompt:

- Keep one clear subject per image.
- State scene, composition, palette, line quality, character posture, and mood.
- Add the style profile's `style_prompt`.
- Add negative constraints from the style profile.
- For `wordless` styles, forbid all text, symbols, watermarks, logos, signatures, QR codes, UI labels, and random marks.
- For `model-rendered` styles, wrap every required Chinese string in quotation marks and forbid unquoted text.
- For `小林`-family styles, include only the beat caption lines in the prompt as quoted text, specify `complete source image as one bitmap`, and describe the upper or middle watercolor scene plus lower handwritten caption area.
- Never include the WeChat article title in a panel prompt unless the user explicitly asks for a poster-style title image.

Read `prompt-guide.md` for exact text-policy and style-specific prompt construction. Save the completed set as `panel-prompts.json` before any image call.

## 9. Image QA

Review every generated image before layout:

- Style match: first glance should match the chosen style.
- Script match: image expresses the intended beat.
- Text policy: wordless images contain no text; model-rendered images copy quoted text correctly.
- For `小林`-family styles, manually compare every generated caption character with the quoted script lines.
- Human quality: no broken faces, duplicated heads, malformed hands, missing limbs, fused bodies, or uncanny posture.
- Brand safety: no copied account title, QR code, signature, logo, watermark, or fixed character identity.
- Composition: simple enough for mobile reading.

If a panel fails, regenerate it before stitching. Do not fix a failed panel by hiding it in layout.

## 10. Layout And Final QA

Create `article.json` after panel QA:

- Start the long image from the first body beat, not from the WeChat article title.
- Choose the closest template.
- Put outside text into deterministic text blocks.
- For `小林`-family styles, do not put the caption into `brush_text`; it should already be inside the generated source image.
- For `小林`-family styles, layout can start only after 图片验收 has passed for every numbered image.
- Do not use `type: "title"`; the layout script rejects title blocks.
- Keep text blocks short enough for mobile reading.
- Use style-specific blocks such as `badge`, `text_bars`, `section_label`, or `framed_image`.
- Keep image paths relative to `article.json`.

Open the built long image and verify:

- It is one vertical image.
- The WeChat article title is not inside the long image.
- Sections, captions, and images are not clipped.
- The rhythm is stable from top to bottom.
- Text is readable at phone width.
- Image panels are consistent in style.
- There are no accidental QR codes, signatures, watermarks, copied names, or garbled Chinese.
- For `小林`-family styles, the lower handwritten caption must match the quoted prompt text exactly.
- The final piece expresses the original thesis.
