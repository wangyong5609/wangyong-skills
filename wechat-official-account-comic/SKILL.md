---
name: wechat-official-account-comic
description: Generate original Chinese WeChat Official Account comic long images, including guided topic selection, first-use persistent image-provider selection, title metadata, copy, storyboards, panel prompts, image generation, panel QA, deterministic layout, style training, and final mobile QA. Use for 公众号漫画、漫画长图、漫画脚本、漫画风格训练，以及暖白手绘漫画、蓝栏柔彩漫画、绿底粗线漫画、小林诗意治愈、小林生活讽刺、小林奇想涂鸦；支持 Codex 内置 imagegen、Agnes、火山方舟 Seedream 或破局问问 GPT Image。
---

# WeChat Official Account Comic

Create one publishable vertical comic image. Treat workflow order as a production contract, not a suggestion.

## Non-Negotiable Rules

- Create original work. Keep only broad format traits from references; never copy a named living artist, account identity, fixed character, signature, QR code, logo, or branded phrase.
- Keep the WeChat article title outside generated panels and outside `article.json`. Never use a normal-production `title` block.
- Use the selected `styles/<style-id>.json` profile as the only visual-style source during normal production. Use reference screenshots only for training, explicit comparison, or requested image continuity.
- Write reader-facing copy before prompts. Create prompts before images. Pass panel QA before layout. Inspect the final long image before completion.
- Never replace failed API-generated panels with SVG, PIL, canvas, vector, or placeholder art unless the user explicitly requests a layout-only mockup.
- Never ask the user to paste an API key into chat or persist a pasted key. Use an environment variable, external `.env`, or hidden `--api-key-stdin` input.
- Before the first image job, detect the runtime, read the saved provider preference, and require a user choice when none exists. Persist only the provider id, never an API key.

## Required Reading Router

Read only the files required for the current request:

- **Any comic production**: read `docs/comic-creator-workflow.md` before drafting copy, prompts, or images.
- **Style choice or panel QA**: read `docs/style-guide.md`, then load the selected `styles/*.json` profile.
- **Prompt writing**: read `docs/prompt-guide.md` after the storyboard is complete.
- **Any image generation**: read `docs/image-generation-guide.md` before the first image call. In Codex, also load the available `imagegen` skill and follow its built-in-tool workflow.
- **Layout or reference matching**: read `docs/layout-guide.md` before creating `article.json`.
- **Training, analyzing, or adding a style**: read `docs/style-training-guide.md`; do not run the normal production workflow first.

Do not read provider, prompt, layout, or training details when the user only asks what styles are supported.

## Request Router

Classify the request before acting:

1. **List/explain styles**: answer from `docs/style-guide.md`; do not draft or generate.
2. **Vague comic request or broad seed**: recommend 3-5 concrete topics with matching styles, then stop and wait for the user to choose.
3. **Topic and style specified, with direct-generation intent**: treat the brief as confirmed and run the production gates below. Do not skip copy, storyboard, or prompt preparation.
4. **小林-family request**: use the mandatory interactive branch below even when the user says “直接生成”.
5. **Train/add/revise a style**: route to `docs/style-training-guide.md`.
6. **Resume or repair a failed job**: inspect existing prompts, panels, pending responses, manifest, and `article.json`; resume from the first incomplete gate instead of restarting.

## Runtime And Provider Routing

Choose the provider from actual runtime capabilities and the saved user preference, then record it in `BRIEF`:

1. Run `scripts/provider_preference.py --runtime <codex|workbuddy|generic> get` before the first image-generation decision.
2. If a saved provider exists and is available, use it without asking again.
3. If no preference exists, present the available provider choices, mark the environment-recommended choice, and **STOP**. Do not generate prompts or images in the same turn.
4. If the user already explicitly named a provider and no preference exists, treat it as the first choice and save it; no duplicate question is needed.
5. Save the confirmed provider with `scripts/provider_preference.py --runtime <runtime> set <provider>`.
6. If the user says “这次用 X”, override only the current job. If the user says “以后默认 X / 更换默认生图方式”, update the saved preference.
7. If the saved provider is unavailable in the current environment, explain why, present valid replacements, and **STOP**. Never silently switch providers after a failure.

Offer these choices when available:

- `codex-imagegen`: Codex built-in imagegen; recommend in Codex; no API key; one tool call per panel.
- `agnes`: Agnes Image HTTP API; recommend outside Codex when no preference exists; requires an Agnes key.
- `pojuwenwen`: 破局问问 GPT Image; requires `BREAKOUT_API_KEY`; defaults to two concurrent panels.
- `seedream`: Volcengine Ark/Doubao Seedream; requires a Doubao/Ark key.

For Codex built-in generation, issue one `image_gen` call per panel. Do not use the third-party batch Python script, do not request `OPENAI_API_KEY`, and do not switch to the imagegen CLI fallback unless the user explicitly requests or confirms it.

## Mandatory Production Gates

Track these states in order: `BRIEF -> COPY -> STORYBOARD -> PROMPTS -> PANELS -> LAYOUT -> FINAL_QA`.

A later state may begin only after the previous state is `PASS`. If a state says **STOP**, end the turn after presenting it. Never call image generation in the same turn as a pending user confirmation.

| Gate | Required output and pass condition | Stop condition |
| --- | --- | --- |
| `BRIEF` | Topic, one-sentence thesis, reader, emotion, style, and provider are known; provider came from an explicit request or saved preference. | If topic/style is vague or no provider preference exists, present choices and **STOP**. |
| `COPY` | Title candidates are metadata only; opening, exact beat text, in/out-of-image text, and ending are stable. | For 小林-family, present the numbered beat table and **STOP** for approval. |
| `STORYBOARD` | One row per image: purpose, scene, composition, exact required text, prompt seed, and failure gate. | Do not draft prompts before every image has a row. |
| `PROMPTS` | `panel-prompts.json` exists; every prompt follows the selected profile and text policy. | For 小林-family, present prompts and **STOP** for approval. |
| `PANELS` | Real panels exist and each passes style, anatomy, text, brand, and script QA. | On API failure, report it and stop. For 小林-family, show/report the batch and **STOP** for image acceptance. |
| `LAYOUT` | Create `article.json` only from accepted panels; build one vertical image without an article-title block. | Do not layout while any panel is pending or rejected. |
| `FINAL_QA` | Open the final image; verify readability, clipping, order, consistency, exact text, and forbidden artifacts. | Regenerate or rebuild the failed component; do not claim completion. |

For non-小林 styles, explicit “直接生成/生图” authorizes continuing across internal gates without extra confirmation, but every gate artifact and QA still must exist.

## 小林-Family Interactive Branch

Apply to `小林诗意治愈` / `小林风格1`, `小林生活讽刺` / `小林风格2`, and `小林奇想涂鸦` / `小林风格3`.

These are independent numbered quote-and-metaphor images, not continuous stories. Follow this exact user-confirmation sequence:

1. Confirm topic and which 小林 style.
2. Present a beat table with `编号`, `caption 行`, `核心意思`, `视觉隐喻`, `画面方向`; wait.
3. Present one complete prompt per approved beat, including quoted `Text to render exactly`; wait.
4. Generate one image or a small batch, report/show each image, and wait for acceptance. Regenerate only rejected numbers.
5. After every image is accepted, create the `badge` + `image` layout in the approved order.

Do not combine two confirmation gates in one turn. Do not generate prompts, images, or layout while the preceding confirmation is pending.

## Supported Style Routing

- `暖白手绘漫画` (default): educational, everyday knowledge, self-care; `wordless` panels.
- `蓝栏柔彩漫画`: psychology and relationship healing; `wordless` panels with deterministic blue-bar text.
- `绿底粗线漫画`: workplace comparison and punchy scenes; model-rendered quoted Chinese.
- `小林诗意治愈` / `小林风格1`: poetic watercolor affirmations; model-rendered handwritten captions.
- `小林生活讽刺` / `小林风格2`: everyday pressure and satire; model-rendered handwritten captions.
- `小林奇想涂鸦` / `小林风格3`: cute object/animal metaphors and light philosophy; model-rendered handwritten captions.

Resolve Chinese names, aliases, style ids, or `--style-profile` through `docs/style-guide.md` and `styles/*.json`. If no style is specified after topic selection, recommend one; do not silently choose for a vague request.

## Image and Text Policy

- For `wordless`, generated panels must contain no written language, numbers, labels, speech text, UI text, watermark, logo, or signature. Put exact Chinese in deterministic layout blocks.
- For `model-rendered`, wrap every intended in-image string in double quotes, specify its location, and forbid all unquoted text. Manually compare generated Chinese against the approved copy.
- In Codex, use the built-in `image_gen` tool according to the `imagegen` skill, then copy or move each selected output into the project panel folder. Do not rely on a destination-path argument to the tool.
- Use `scripts/generate_panels_seedream.py` only for Agnes, Seedream, or 破局问问 HTTP APIs outside the Codex built-in path.
- Save generated panels as `panels/panel-01.png`, `panel-02.png`, and so on. Preserve approved numbering through prompts, files, badges, and layout.

## Layout and Completion

Build with the nearest template and `scripts/build_long_comic.py`. Start from the first body beat, section label, badge, or panel. Use relative image paths in `article.json`.

Before finishing, verify that the result:

- is one openable vertical image readable at mobile width;
- contains no WeChat article title, clipping, garbled text, unapproved text, QR code, signature, watermark, copied identity, or malformed people;
- uses real accepted panels from the selected provider;
- keeps the approved copy, panel order, and selected style consistent from top to bottom.
