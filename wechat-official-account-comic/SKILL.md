---
name: wechat-official-account-comic
description: Generate WeChat Official Account comic long images as one publishable vertical image. Use when the user wants Chinese 公众号漫画, beginner guided topic selection, reusable comic style profiles, trained or distilled comic styles such as 小林风格, creator-style workflow planning, title formulas, comic scripting, image prompts, panel QA, deterministic layout, and Agnes Image, Volcengine Ark Seedream, or Agent image generation.
---

# WeChat Official Account Comic

Create an original Chinese public-account comic article as a single vertical image by combining generated panels with either deterministic text layout or model-rendered in-image text, according to the selected style profile.

Do not imitate a named living artist, copy a branded comic identity, or make the output appear to be authored by someone else. If the user asks for exact impersonation, keep only high-level format traits such as mobile canvas, text rhythm, color hierarchy, panel density, and broad illustration language.

## Style Entry

The user can request styles by Chinese name:

- `暖白手绘漫画`: warm white-space hand-drawn comic style with clean text rhythm and publication-quality panel illustrations. Characters must be anatomically coherent, emotionally readable, and consistently drawn; do not allow broken faces, extra heads, missing parts, sketchy storyboard panels, or low-quality rough drafts.
- `蓝栏柔彩漫画`: soft full-color comic style with stacked deep-blue narration bars, occasional yellow-highlight words, red emphasis paragraphs, and warm low-contrast illustrations.
- `绿底粗线漫画`: green textured comic style with rough thick black outlines, black rounded panel frames, paper-grain flat colors, and AI-rendered speech bubbles/text.
- `小林诗意治愈` / `小林风格1`: poetic watercolor longform with large white space, centered numbered red badges, and complete source images that contain a soft hand-drawn watercolor nature/metaphor scene above plus large black handwritten brush-calligraphy Chinese captions below inside the same generated image.
- `小林生活讽刺` / `小林风格2`: white-space watercolor caricature longform for everyday life observations, family/workplace pressure, and satirical punchlines. Each complete source image contains a rough hand-drawn people scene above or in the middle plus large black handwritten Chinese captions below.
- `小林奇想涂鸦` / `小林风格3`: white-space whimsical doodle longform for cute animals, odd little monsters, personified objects, and gentle philosophical or humorous one-liners. Each complete source image contains a small playful watercolor doodle plus large black handwritten Chinese captions below.

For all `小林`-family styles, use only broad format traits; do not copy the reference account identity, QR code, signature, exact phrases, or fixed character identity.

If the user does not specify a style, use `暖白手绘漫画`.

All named styles are managed through reusable profiles in `styles/*.json`. Resolve the requested style by Chinese name, alias, style id, or an explicitly provided `--style-profile`; then use that profile as the only visual style source for panel generation. Do not reuse training screenshots as generation references by default after a profile exists. Read `docs/style-training-guide.md` when the user asks to train, analyze, or add a new comic style into this skill.
Read `docs/comic-creator-workflow.md` when planning a comic from a topic, especially for trained styles. It defines the production sequence from theme, WeChat title metadata, body copy, storyboard, panel count, prompts, image QA, layout, and final long-image validation.

## Beginner Topic Selection

When the user is new, vague, exploratory, says only that they want to make/generate a comic, or gives a broad seed without a style, start with guided topic selection instead of production.

First tell the user what themes this skill currently supports, recommend 3-5 concrete topics or angles, name the best-fit style for each, and ask the user to choose or revise one. Supported theme families include:

- 情绪疗愈 / 自我关怀: anxiety, guilt, burnout, slowing down, loving yourself.
- 日常生活 / 关系观察: family, friendship, middle-age pressure, everyday choices.
- 职场成长 / 效率习惯: workplace contrast, career fatigue, communication, time management.
- 知识科普 / 健康常识: practical explanations, food/sleep/body rhythms, life science.
- 亲子家庭 / 成长教育: parent-child communication, family roles, learning habits.
- 奇想哲思 / 轻幽默: animals, objects, tiny absurd metaphors, soft punchlines.

Map recommendations to styles: `暖白手绘漫画` for broad educational or self-care topics, `蓝栏柔彩漫画` for psychology and relationship healing, `绿底粗线漫画` for workplace comparison, `小林诗意治愈` for poetic affirmations, `小林生活讽刺` for everyday satire, and `小林奇想涂鸦` for cute philosophical one-liners.

For a broad seed such as "好好过日子，好好爱自己", recommend several angles before drafting. For a fully specified topic and style, briefly confirm the thesis and proceed only if the user asked for direct generation. In all beginner or broad-topic cases, do not draft copy, storyboard, prompts, images, or article.json before the user chooses or confirms a theme.

## Title Boundary

The WeChat article title is metadata outside the long image. Generate title candidates for the article title field, output folder, and internal planning, but do not place the selected title in generated panel images or in `article.json`.

Do not use `type: "title"` for normal production. The layout script rejects title blocks. The final long image should start from the first body beat, numbered badge, opening scene, or section text.

## 小林-Family Mandatory Interactive Flow

For `小林诗意治愈`, `小林生活讽刺`, and `小林奇想涂鸦`, follow this mandatory interactive flow. These styles are independent quote-and-metaphor comics, not continuous story comics. Each numbered source image must stand alone as one complete idea under the same topic.

Do not skip confirmation gates for speed. Do not generate prompts, images, or the final long image before the matching user confirmation has happened.

1. **主题/风格确认**: require a user-provided comic topic before creative drafting. If the user asks for a `小林`-family comic but does not specify `小林风格1/2/3`, recommend one style from the topic and confirm it with the user before drafting the beat set.
2. **金句组确认**: draft the independent beat set first. Output a table with `编号`, `caption 行`, `核心意思`, `视觉隐喻`, and `画面方向`. Each beat must be self-contained and should not depend on the previous or next image for meaning. Wait for user confirmation before writing any image prompt.
3. **prompt 确认**: after the beat set is approved, create the complete single-image prompt for every beat. Each prompt must include a `Text to render exactly` block with the approved caption lines in double quotation marks. Wait for user confirmation before generating any image.
4. **图片验收**: generate images one by one or in a small batch, then show or report each generated image for user acceptance. If one image fails expectations, regenerate only that numbered image and keep the approved beats and prompts stable unless the user requests copy changes. Do not create `article.json`, sort panels, or stitch the final long image until every generated image has passed user acceptance.

After all images pass, use the approved beat order as the default final order. Reorder only if the user explicitly asks. Then create the `badge` + `image` layout and stitch the long image.

## Workflow

1. Use reference images only when training or revising a style profile. For normal production with an existing style profile, generate panels from pure text prompts; do not attach or rely on reference screenshots unless the user explicitly asks for re-training or comparison.
2. Run Beginner Topic Selection when the user is new, vague, exploratory, or gives only a broad seed. Wait for the user to choose or confirm a theme and style before drafting.
3. Choose or confirm a topic and one-sentence thesis. If the user did not provide one after the beginner menu, pick a safe popular-science, everyday-knowledge, emotion, or workplace topic and ask for confirmation before production.
4. Choose the requested style from `docs/style-guide.md`. For a trained style, load the matching `styles/<style-id>.json` profile and use its layout, copy, text policy, prompt, and quality gate.
5. Draft 5-10 WeChat article title candidates using `docs/comic-creator-workflow.md`. Select one title for metadata only; do not include it in panel prompts or `article.json`.
6. Write the reader-facing comic copy before image generation: opening body text, each beat's exact text, every `小林` caption line, any outside-layout text, and the ending line. Do not generate images until the copy is stable.
7. Decide the exact image count and make a storyboard table. For each image, define the copy beat it supports, scene, composition, required in-image text if any, prompt seed, and failure gate.
8. Draft the article structure that matches the style:
   - `暖白手绘漫画`: 5-8 short sections: hook, setup dialogue, headings, explanatory beats, recap.
   - `蓝栏柔彩漫画`: 1 narrator/consultant opening, blue-bar paragraph rhythm, 3-5 emotional beats, 2-4 soft full-color panels, red thesis emphasis.
   - `绿底粗线漫画`: 3-5 numbered workplace themes, each with "上班第一年/上班第五年" framed comparison panels and a concise takeaway.
   - `小林诗意治愈`: 3-6 numbered poetic beats, each with one complete source image: quiet watercolor scene above plus a 2-4 line black handwritten caption inside the same image. Keep every beat self-contained and emotionally affirmative.
   - `小林生活讽刺`: 5-8 numbered life-observation beats, each with one complete source image: rough watercolor caricature people scene plus a 2-5 line black handwritten caption inside the same image. Keep every beat self-contained, slightly ironic, and easy to understand.
   - `小林奇想涂鸦`: 6-10 numbered whimsical philosophy beats, each with one complete source image: small cute animal, odd creature, or personified-object doodle plus a 2-5 line black handwritten caption inside the same image. Keep each beat light, surprising, and not too realistic.
9. Generate panel images with either `scripts/generate_panels_seedream.py` or the current Agent's available image-generation tool. The script defaults to Agnes Image and can explicitly use Seedream with `--provider seedream`. For `暖白手绘漫画` and `蓝栏柔彩漫画`, prefer no embedded text in generated panels. For `绿底粗线漫画` and `小林`-family styles, required in-image text must be generated directly by the chosen image model from quoted text in the prompt. For `小林`-family styles, quote each caption line and place it in the lower handwritten caption area of the same source image. Never include the WeChat article title in `Text to render exactly`.
10. For `小林`-family styles, run one prompt-only smoke test before a full article whenever the topic, text rhythm, or prompt recipe changes. Do not attach the training/reference screenshot for this smoke test. It passes only when the source image contains the watercolor scene and exact quoted handwritten caption in one bitmap, with no QR code, signature, account name, or extra text.
11. Validate each generated image against the style's quality gate. Regenerate failed panels before layout instead of hiding problems in final composition.
12. Save generated panel images into a project folder such as `output/comics/<中文标题>/panels/`.
13. Create a JSON spec for `scripts/build_long_comic.py` using the closest template in `templates/`, or create a new template when a trained style needs a materially different layout. Start the spec with the first body beat, not the WeChat article title.
14. Run the layout script to produce a single PNG or JPEG suitable for upload to WeChat.
15. Inspect the final long image for mobile readability, text overflow, repeated rhythm, image/text balance, and absence of the article title. Revise prompts or spec and rerun if needed.

## Image Provider Choice

Use one of three panel-generation paths:

- **Agnes API path (default)**: for WorkBuddy or other non-Codex runtimes, use `scripts/generate_panels_seedream.py` without a provider flag. It calls Agnes Image 2.0 Flash through `https://apihub.agnes-ai.com/v1/images/generations`, reads `AGNES_API_KEY` by default, and accepts `GNES_API_KEY` or `AGNESAI_API_KEY` as aliases.
- **Volcengine Ark/Doubao Seedream API path**: use the same script with `--provider seedream` when the user explicitly chooses Seedream or already has a Doubao/Ark key. It reads `DOUBAO_API_KEY` by default and accepts `ARK_API_KEY` as a fallback.
- **Codex / Agent imagegen path**: if the current runtime is Codex and image generation is available, use Codex's image-generation capability to create panels from the selected profile. For `小林`-family styles, use prompt-only generation from the matching profile, such as `styles/xiaolin-healing.json` or `styles/xiaolin-life-satire.json`; do not use the user's screenshot as a reference unless explicitly re-training. Save each generated panel as `panels/panel-01.png`, `panels/panel-02.png`, etc., then run `scripts/build_long_comic.py`.

Do not claim that the Python script can directly call Codex imagegen or another Agent's image-generation tool. Interactive image generation is an agent/tool workflow, while `generate_panels_seedream.py` is only for supported third-party HTTP APIs: Agnes by default, or Seedream when selected.

## Training New Comic Styles

Use `docs/style-training-guide.md` when the user provides reference screenshots or asks to add more comic styles. Treat "training" as skill-level distillation, not model fine-tuning.

The expected output of style training is:

1. A reusable style profile saved as `styles/<style-id>.json`, based on `templates/style-profile-template.json`.
2. A short entry in `docs/style-guide.md` describing the new style's use case, layout, art direction, text policy, and quality gate.
3. A new `templates/article-template-<style-id>.json` only when the layout cannot reuse an existing template.
4. A tested panel prompt set, reusable prompt recipe, and validation notes. When API or Agent imagegen access is available, include a small prompt-only smoke-test result before using the style for production.

Style profiles must include `name`, `style_prompt`, and `text_policy`. Use `text_policy: "wordless"` when the layout script should render all Chinese text. Use `text_policy: "model-rendered"` only when the image model must draw quoted Chinese inside panels. For styles like the `小林` family, also keep a `prompt_recipe` and `validated_test` note in the style profile so future runs know which prompt structure already worked.

Do not copy a reference account's fixed characters, title banner, logo, author signature, or recurring branded phrases. Keep high-level production traits only: mobile canvas, rhythm, panel density, palette, broad line language, and content structure.

## API Failure Handling

If image generation fails while using Agnes or Seedream, stop that workflow and report the real API problem to the user. Do not silently switch to local vector drawings, SVG, PIL placeholder panels, canvas mockups, or another provider for a deliverable long image unless the user explicitly chooses a different provider such as Seedream or an Agent image-generation tool.

For Agnes failures, first check `AGNES_API_KEY` or the accepted aliases, then the Agnes account state, token plan, model name, network access, and request parameters. Keep drafted `panel-prompts.json` and `article.json` files so the same job can be rerun after the account/key issue is fixed.

When the API returns `AccountOverdueError`, `InsufficientBalance`, balance shortage, arrears, quota exhaustion, or a similar billing error:

1. Tell the user that the Volcengine Ark/Doubao account tied to the current API key cannot call the Seedream/即梦 model because the account is overdue or lacks available balance.
2. Guide the user to log in to the same Volcengine account used by the API key, open the billing/recharge page, and recharge or clear overdue bills before retrying.
3. Keep any drafted `panel-prompts.json` and `article.json` files so the same job can be rerun after recharge.
4. Do not produce a "final" comic long image from local vector or placeholder panels unless the user explicitly asks for a layout-only mockup. If making a mockup, label it clearly as a mockup and not as a valid generated-panel result.

Suggested user-facing message:

```text
Seedream/即梦 面板生成已停止：火山方舟返回账号欠费/余额不足错误。
请登录与当前 API Key 对应的火山引擎账号，进入「费用中心」或充值页，给火山方舟/即梦模型调用账户充值或结清欠费后再重试。
我已保留 prompts 和 article.json，充值完成后可以直接重新运行生成命令。也可以明确改用 Agent imagegen 路径重新生成 panels。
```

## Panel Prompt Pattern

Use this pattern for third-party image prompts:

```text
Use case: illustration-story
Asset type: WeChat public-account educational comic panel
Primary request: <specific panel action>
Style for `暖白手绘漫画`: WORDLESS IMAGE ONLY, standalone warm children's book style illustration, clean white or soft pastel background, polished hand-drawn ink linework, restrained warm colors, gentle expressive characters, finished illustration quality, mobile-readable composition
Composition: one clear scene with a strong central subject, generous padding, simple readable background, no clutter, no tiny details, no watermark, no logo
Human quality: if people appear, they must be anatomically coherent complete human figures with one head per person, clear face, neck, torso, arms, hands, legs, feet, natural joints, natural posture, correct scale relationships, and emotionally readable expressions.
Text rule for `暖白手绘漫画`: absolutely no written language inside generated images. No Chinese characters, English letters, numbers, captions, speech bubbles, comic sound effects, title text, handwriting, labels, poster text, or UI text. Any screens, books, clocks, papers, signs, whiteboards, posters, and product surfaces must be blank or abstract.
Quality constraints: finished polished illustration only; no rough storyboard, no messy pencil draft, no dirty gray shading, no distorted faces, no duplicate heads, no floating facial parts, no detached hair, no extra limbs, no missing limbs, no fused bodies, no broken hands, no backward joints, no ambiguous body parts.
Style constraints: no stick figures, no bean/blob bodies, no mascot-like nonhuman people, no pictogram icons, no semi-realistic grim manga, no horror mood, no cramped composition, no uncanny or malformed characters; do not copy any existing comic character, mascot, author signature, title banner, or brand identity.
```

Use colored full panels for places, objects, and scenes; use black-and-white line panels for jokes, metaphors, and historical or explanatory beats.

For `暖白手绘漫画`, illustration quality matters more than merely matching the white page layout. Use simple readable scenes, but every panel must look like a finished public-account illustration. Prefer metaphorical scenes with clear emotional intent. Reject and regenerate any panel with strange anatomy, duplicated heads, detached hair, fused people, broken hands, rough draft texture, dirty gray sketching, inconsistent visual style, or any text inside the generated image.

For `蓝栏柔彩漫画`, match the reference psychological WeChat longform look: white page, stacked deep-blue narration bars, occasional yellow emphasized words, red thesis lines, soft golden counseling-room scenes, warm sofa/window/plants/books/cup details, and image edges fading into white. Generated images should use clean but not glossy hand-drawn manga line art, slightly thicker black outlines, simple adult facial features, restrained proportions, flat warm colors with a light watercolor wash, and quiet relationship-healing emotion. Use two recurring character types when the scene needs people: a calm young Chinese female psychological consultant with straight black shoulder-length hair and a mustard cardigan or light blazer over a cream turtleneck; and a young Chinese female client with long black hair, a white shirt, and a muted green vest or green dress. For metaphor panels, simple faceless cream-colored mascot figures and symbolic objects are allowed, and recurring women should not be forced into every scene. Generated images must contain no written text and no blue text bars; all narration bars, yellow emphasis, red thesis lines, and article text are added by the layout script. Speech or thought bubbles may appear only when visually useful, and should remain blank by default. Avoid glossy high-detail anime rendering, cinematic photorealism, childlike cute style, copied faces, clothing sets, logos, or account titles.

For `绿底粗线漫画`, generated panel art should match the reference screenshot's broad WeChat workplace-comic language: rough thick black hand-drawn outlines, lightly wobbly ink edges, flat color blocks with subtle paper-grain texture, simplified expressive Chinese office workers, dense but readable office scenes, and a recurring young Chinese woman employee with light-brown shoulder-length hair, green clothing, white striped sleeves or a brown jacket, blue pants, and a work badge. Use muted grass green, sky blue, mustard yellow, warm brown, orange, gray purple, and off-white. Do not make it polished anime, photorealistic, watercolor-soft, 3D, or glossy.

For `绿底粗线漫画`, all text inside panel images must be rendered directly by the selected image model, including black header-bar text, speech bubbles, thought bubbles, phone/chat messages, timestamps, sound effects, and small emphasized words. Every exact text string that should appear in the image must be wrapped in quotation marks in the panel prompt, for example `"上班第一年"` or `"好想走......可是大家都不走"`. Use short lines and specify where each quoted text belongs: black top title bar, white speech bubble, white chat/message box, time tag, or large white text with black outline. Ask the image model to copy quoted Chinese exactly without rewriting, shortening, replacing synonyms, or dropping characters; long text may wrap to multiple lines but must keep the original order. The layout script should only stack finished panels and apply outer article background/spacing for `绿底粗线漫画`; it should not add extra in-panel bubbles or dialogue text.

For `绿底粗线漫画`, do not use quoted text for non-rendered instructions. Any quoted text is treated as text the selected image model should draw. Ask the selected image model to render only the quoted strings and forbid extra text, English, pinyin, random labels, UI text, wall text, watermarks, logos, signatures, and garbled characters.

For `小林`-family styles, generate each source panel as one finished source image, not as illustration-only art. The prompt must include both the watercolor scene and the exact caption text. Wrap each caption line in double quotation marks, for example `"人这一生"`, `"自私很容易"`, `"爱自己却很难"`. The model must render only those quoted Chinese strings in the lower caption area.

For `小林`-family styles, the quoted caption lines are the beat copy, not the WeChat article title. Never put the article title into the generated source image.

For `小林`-family styles, describe the caption lettering as large black handwritten Chinese brush lettering: dense black ink, uneven thick-and-thin strokes, rough dry-brush edges, organic imperfect character shapes, slightly relaxed hand spacing, centered 2-5 lines, generous line gap. It should not look like Songti, Heiti, Kaiti, PingFang, a digital system font, clean vector calligraphy, subtitle text, or typed typography.

For `小林`-family styles, forbid every unquoted or branded text element: no extra Chinese, no English, no numbers except outer badges added by layout, no QR code, no watermark, no logo, no signature, no account name, no copied author identity. The layout script should stack only the red `badge` blocks and the complete generated `image` blocks; it should not add `brush_text` captions for normal 小林 production.

For `小林`-family styles, the practical prompt recipe is: call it a "complete source image as one bitmap"; state upper or middle illustration and lower caption areas; put a `Text to render exactly` block with every Chinese line in double quotation marks; describe the lower text as black handwritten brush lettering; and repeat the negative rule `no QR code, no signature, no account name, no extra text`. If the watercolor scene becomes too polished or fills too much space, add constraints for smaller watercolor mass, more white margins, looser uneven washes, and rougher hand-painted texture. For `小林奇想涂鸦`, also ask for small illustration mass, cute animal or personified object metaphors, a light absurd twist, and avoid adult-pressure realism.

## Layout Rules

Read `docs/layout-guide.md` when matching a provided reference or planning a new article. Default canvas:

- Width: `600px`
- Background: white
- Body text: centered, 24-28px Chinese font, 1.65 line height
- Headings: bold, 34-42px
- Accent: warm orange callout blocks outside generated panel art
- Rhythm: text block -> image -> text block -> image, with generous vertical whitespace
- Chinese copy cleanup: when writing short centered lines, remove sentence-ending punctuation at the end of each displayed line, especially `，` `。` `；` `：`. Keep punctuation only when it is semantically necessary, such as `？` in a question title.

## Script

Generate panels with `scripts/generate_panels_seedream.py` only when using the Agnes or Seedream batch API path. The API key must come from an environment variable or an external `.env` file, and must never be written into tracked repo files.

Install the local layout dependency before running `scripts/build_long_comic.py`:

```bash
python3 -m pip install -r wechat-official-account-comic/requirements.txt
```

The script resolves API settings with this priority:

1. An explicit `--env-file /path/to/.env`
2. Already exported shell environment variables.
3. The current working directory's `.env`

Use Agnes by default. Store the key as `AGNES_API_KEY`; `GNES_API_KEY` and `AGNESAI_API_KEY` are accepted as aliases.

```bash
export AGNES_API_KEY="your-api-key"
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style 暖白手绘漫画
```

To use Volcengine Ark/Doubao Seedream instead, pass `--provider seedream` and use `DOUBAO_API_KEY`; `ARK_API_KEY` is still accepted as a fallback.

```bash
export DOUBAO_API_KEY="your-api-key"
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --provider seedream \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style 暖白手绘漫画 \
  --size 2304x1728
```

For any style saved as `wechat-official-account-comic/styles/<style-id>.json`, use either:

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style <style-id>
```

or:

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style-profile wechat-official-account-comic/styles/<style-id>.json
```

For Agent imagegen, create the same `panel-prompts.json`, generate each prompt as a separate panel image through the available image-generation tool, and save the files using the same names expected by the layout spec:

```text
output/comics/文章标题/panels/panel-01.png
output/comics/文章标题/panels/panel-02.png
output/comics/文章标题/panels/panel-03.png
```

For `暖白手绘漫画`, prefer landscape or moderate-height panels so one image does not fill an entire phone screen. Agnes defaults to `1024x768`; Seedream can use `2304x1728` (4:3, valid for Seedream 4.5 minimum pixel requirements). In the final long image, place panels at about `520-540px` wide, producing roughly `390-405px` height per panel. Avoid tall source sizes such as `1536x2560` unless a deliberately vertical scene is needed.

Then use `scripts/build_long_comic.py`:

```bash
python3 wechat-official-account-comic/scripts/build_long_comic.py \
  --spec output/comics/文章标题/article.json \
  --out output/comics/文章标题/文章标题-公众号漫画长图.png
```

For `暖白手绘漫画` and `蓝栏柔彩漫画`, the script embeds article copy into the final image. For `绿底粗线漫画`, in-panel copy should already be inside the generated panel images; the script should only stack panels and add outer article text/spacing when needed. Images in the spec are resolved relative to the spec file unless absolute.

## Spec Blocks

Minimal spec:

```json
{
  "canvas_width": 600,
  "blocks": [
    {"type": "paragraph", "text": "明明午饭也吃了，咖啡也喝了，怎么一到下午三点就开始断电？"},
    {"type": "image", "path": "panels/panel-01.png", "width": 540},
    {"type": "heading", "text": "首先，是身体在结账"},
    {"type": "callout", "text": "这不是你懒，是节律、血糖和睡眠债一起找上门。"},
    {"type": "paragraph", "text": "上午硬撑过去的疲劳，并不会消失。它只是换了个时间点，回来提醒你。"}
  ]
}
```

Supported normal-production block types: `paragraph`, `heading`, `image`, `callout`, `spacer`, `rule`, `badge`, `brush_text`.

Additional style blocks supported by the layout script: `text_bars`, `emphasis`, `section_label`, `framed_image`. Do not include `speech_bubbles` on image blocks or `header` on `framed_image` blocks. Panel titles, dialogue, bubbles, chat boxes, caption text, labels, and sound effects must either be rendered directly inside the generated panel image for `model-rendered` styles, or kept as separate outside-layout text blocks for `wordless` styles.

Do not include a `title` block. The WeChat article title belongs in the platform title field and the project file name, not inside the long image.

## Quality Gate

Before finishing, verify:

- The output is one vertical image and opens successfully.
- The WeChat article title is not inside the final long image.
- The output must use real generated panel images from the selected provider unless the user explicitly requested a layout-only mockup.
- If Agnes or Seedream generation failed because of API key, quota, billing, account status, or network errors, stop and explain the error instead of substituting vector or placeholder panels.
- Chinese text is embedded in the image, readable at mobile width, and not clipped.
- Centered Chinese lines should not end with decorative punctuation such as `，` `。` `；` `：`; clean these before stitching.
- Generated panels do not contain garbled text, watermarks, copied logos, copied characters, QR codes, signatures, or account names. For `小林`-family styles, manually compare every caption character against the quoted prompt text; if a character is wrong, missing, or replaced, regenerate the panel instead of accepting the long image.
- For `暖白手绘漫画`, every panel must pass image-quality review: no generated text of any kind, distorted faces, duplicate heads, detached hair, fused bodies, extra/missing limbs, broken hands, rough storyboard texture, dirty sketch shading, or visibly inconsistent style. Regenerate failed panels before stitching.
- The article has a clear topic, hook, section rhythm, and ending.
- The result is an original public-account comic longform, not a deceptive imitation of a named author.
