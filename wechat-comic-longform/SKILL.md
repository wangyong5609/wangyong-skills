---
name: wechat-comic-longform
description: Generate original WeChat public-account longform comic articles as one publishable vertical image. Use when the user wants a Chinese 公众号漫画文章, 科普漫画长图, multi-panel educational comic, image-generation prompts plus stitching, or a reusable workflow that turns a topic or draft copy into a WeChat-ready comic image. Supports Volcengine Ark Seedream scripts or an available Agent image-generation tool for raster panel art, then uses bundled layout scripts for deterministic Chinese text composition.
---

# WeChat Comic Longform

Create an original Chinese public-account comic article as a single vertical image by combining generated panel art with deterministic text layout.

Do not imitate a named living artist, copy a branded comic identity, or make the output appear to be authored by someone else. If the user asks for exact impersonation, keep only high-level format traits such as mobile canvas, text rhythm, color hierarchy, panel density, and broad illustration language.

## Style Entry

The user can request styles by Chinese name:

- `风格一`: white-background educational comic style with clean text rhythm and publication-quality panel illustrations. Characters must be anatomically coherent, emotionally readable, and consistently drawn; do not allow broken faces, extra heads, missing parts, sketchy storyboard panels, or low-quality rough drafts.
- `风格二`: emotional/psychology longform, soft full-color illustration, blue text bars, occasional yellow-highlight words and red emphasis paragraphs.
- `风格三`: workplace comparison comic, green textured background, black rounded panel frames, AI-rendered speech bubbles/text, section-by-section "first year vs fifth year" contrast.

If the user does not specify a style, use `风格一`.

## Workflow

1. Read any provided reference image only for high-level layout traits. If a reference is a long screenshot, inspect its dimensions and optionally crop representative slices.
2. Choose or confirm a topic. If the user did not provide one, pick a safe popular-science or everyday-knowledge topic.
3. Choose the requested style from `docs/style-guide.md`.
4. Draft the article structure that matches the style:
   - `风格一`: 5-8 short sections: hook, setup dialogue, headings, explanatory beats, recap.
   - `风格二`: 1 narrator/consultant opening, blue-bar paragraph rhythm, 3-5 emotional beats, 2-4 soft full-color panels, red thesis emphasis.
   - `风格三`: 3-5 numbered workplace themes, each with "上班第一年/上班第五年" framed comparison panels and a concise takeaway.
5. Generate panel images with either `scripts/generate_panels_seedream.py` or the current Agent's available image-generation tool. For `风格一` and `风格二`, prefer no embedded text in generated panels. For `风格三`, all in-panel text must be generated directly by the chosen image model from quoted text in the prompt.
6. Save generated panel images into a project folder such as `output/comics/<中文标题>/panels/`.
7. Create a JSON spec for `scripts/build_long_comic.py` using the closest template in `templates/`.
8. Run the layout script to produce a single PNG or JPEG suitable for upload to WeChat.
9. Inspect the final long image for mobile readability, text overflow, repeated rhythm, and image/text balance. Revise prompts or spec and rerun if needed.

## Image Provider Choice

Use one of two panel-generation paths:

- **Seedream/Doubao batch path**: use `scripts/generate_panels_seedream.py` when the user has a Volcengine Ark/Doubao image API key and wants repeatable batch generation from a prompts file.
- **Agent imagegen path**: use the current Agent's image-generation capability when the user wants to generate panels interactively without running the Seedream script. Save each generated panel as `panels/panel-01.png`, `panels/panel-02.png`, etc., then run `scripts/build_long_comic.py`.

Do not claim that the Python script can directly call the Agent's image-generation tool. Interactive image generation is an agent/tool workflow, while `generate_panels_seedream.py` is only for the Seedream/Doubao HTTP API.

## API Failure Handling

If Seedream/即梦 image generation fails while using the Seedream path, stop that workflow and report the real API problem to the user. Do not silently switch to local vector drawings, SVG, PIL placeholder panels, canvas mockups, or another provider for a deliverable long image unless the user explicitly chooses a different provider such as an Agent image-generation tool.

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

Use this pattern for Seedream prompts:

```text
Use case: illustration-story
Asset type: WeChat public-account educational comic panel
Primary request: <specific panel action>
Style for `风格一`: WORDLESS IMAGE ONLY, standalone warm children's book style illustration, clean white or soft pastel background, polished hand-drawn ink linework, restrained warm colors, gentle expressive characters, finished illustration quality, mobile-readable composition
Composition: one clear scene with a strong central subject, generous padding, simple readable background, no clutter, no tiny details, no watermark, no logo
Human quality: if people appear, they must be anatomically coherent complete human figures with one head per person, clear face, neck, torso, arms, hands, legs, feet, natural joints, natural posture, correct scale relationships, and emotionally readable expressions.
Text rule for `风格一`: absolutely no written language inside generated images. No Chinese characters, English letters, numbers, captions, speech bubbles, comic sound effects, title text, handwriting, labels, poster text, or UI text. Any screens, books, clocks, papers, signs, whiteboards, posters, and product surfaces must be blank or abstract.
Quality constraints: finished polished illustration only; no rough storyboard, no messy pencil draft, no dirty gray shading, no distorted faces, no duplicate heads, no floating facial parts, no detached hair, no extra limbs, no missing limbs, no fused bodies, no broken hands, no backward joints, no ambiguous body parts.
Style constraints: no stick figures, no bean/blob bodies, no mascot-like nonhuman people, no pictogram icons, no semi-realistic grim manga, no horror mood, no cramped composition, no uncanny or malformed characters; do not copy any existing comic character, mascot, author signature, title banner, or brand identity.
```

Use colored full panels for places, objects, and scenes; use black-and-white line panels for jokes, metaphors, and historical or explanatory beats.

For `风格一`, illustration quality matters more than merely matching the white page layout. Use simple readable scenes, but every panel must look like a finished public-account illustration. Prefer metaphorical scenes with clear emotional intent. Reject and regenerate any panel with strange anatomy, duplicated heads, detached hair, fused people, broken hands, rough draft texture, dirty gray sketching, inconsistent visual style, or any text inside the generated image.

For `风格二`, match the reference psychological WeChat longform look: white page, stacked deep-blue narration bars, occasional yellow emphasized words, red thesis lines, soft golden counseling-room scenes, warm sofa/window/plants/books/cup details, and image edges fading into white. Generated images should use clean but not glossy hand-drawn manga line art, slightly thicker black outlines, simple adult facial features, restrained proportions, flat warm colors with a light watercolor wash, and quiet relationship-healing emotion. Use two recurring character types when the scene needs people: a calm young Chinese female psychological consultant with straight black shoulder-length hair and a mustard cardigan or light blazer over a cream turtleneck; and a young Chinese female client with long black hair, a white shirt, and a muted green vest or green dress. For metaphor panels, simple faceless cream-colored mascot figures and symbolic objects are allowed, and recurring women should not be forced into every scene. Generated images must contain no written text and no blue text bars; all narration bars, yellow emphasis, red thesis lines, and article text are added by the layout script. Speech or thought bubbles may appear only when visually useful, and should remain blank by default. Avoid glossy high-detail anime rendering, cinematic photorealism, childlike cute style, copied faces, clothing sets, logos, or account titles.

For `风格三`, generated panel art should match the reference screenshot's broad WeChat workplace-comic language: rough thick black hand-drawn outlines, lightly wobbly ink edges, flat color blocks with subtle paper-grain texture, simplified expressive Chinese office workers, dense but readable office scenes, and a recurring young Chinese woman employee with light-brown shoulder-length hair, green clothing, white striped sleeves or a brown jacket, blue pants, and a work badge. Use muted grass green, sky blue, mustard yellow, warm brown, orange, gray purple, and off-white. Do not make it polished anime, photorealistic, watercolor-soft, 3D, or glossy.

For `风格三`, all text inside panel images must be rendered directly by Seedream, including black header-bar text, speech bubbles, thought bubbles, phone/chat messages, timestamps, sound effects, and small emphasized words. Every exact text string that should appear in the image must be wrapped in quotation marks in the panel prompt, for example `"上班第一年"` or `"好想走......可是大家都不走"`. Use short lines and specify where each quoted text belongs: black top title bar, white speech bubble, white chat/message box, time tag, or large white text with black outline. Ask Seedream to copy quoted Chinese exactly without rewriting, shortening, replacing synonyms, or dropping characters; long text may wrap to multiple lines but must keep the original order. The layout script should only stack finished panels and apply outer article background/spacing for `风格三`; it should not add extra in-panel bubbles or dialogue text.

For `风格三`, do not use quoted text for non-rendered instructions. Any quoted text is treated as text Seedream should draw. Ask Seedream to render only the quoted strings and forbid extra text, English, pinyin, random labels, UI text, wall text, watermarks, logos, signatures, and garbled characters.

## Layout Rules

Read `docs/layout-guide.md` when matching a provided reference or planning a new article. Default canvas:

- Width: `600px`
- Background: white
- Body text: centered, 24-28px Chinese font, 1.65 line height
- Headings: bold, 34-42px
- Accent: warm orange speech/callout blocks
- Rhythm: text block -> image -> text block -> image, with generous vertical whitespace
- Chinese copy cleanup: when writing short centered lines, remove sentence-ending punctuation at the end of each displayed line, especially `，` `。` `；` `：`. Keep punctuation only when it is semantically necessary, such as `？` in a question title.

## Script

Generate panels with `scripts/generate_panels_seedream.py` only when using the Seedream/Doubao batch path. The API key must come from an environment variable or an external `.env` file, and must never be written into tracked repo files.

Install the local layout dependency before running `scripts/build_long_comic.py`:

```bash
python3 -m pip install -r wechat-comic-longform/requirements.txt
```

The script resolves API settings with this priority:

1. An explicit `--env-file /path/to/.env`
2. Already exported shell environment variables.
3. The current working directory's `.env`

Use `DOUBAO_API_KEY` by default. `ARK_API_KEY` is still accepted as a fallback.

```bash
export DOUBAO_API_KEY="your-api-key"
python3 wechat-comic-longform/scripts/generate_panels_seedream.py \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style 风格一 \
  --model doubao-seedream-4-5-251128 \
  --size 2304x1728
```

For Agent imagegen, create the same `panel-prompts.json`, generate each prompt as a separate panel image through the available image-generation tool, and save the files using the same names expected by the layout spec:

```text
output/comics/文章标题/panels/panel-01.png
output/comics/文章标题/panels/panel-02.png
output/comics/文章标题/panels/panel-03.png
```

For `风格一`, prefer landscape or moderate-height panels so one image does not fill an entire phone screen. Recommended panel source size is `2304x1728` (4:3, valid for Seedream 4.5 minimum pixel requirements). In the final long image, place panels at about `520-540px` wide, producing roughly `390-405px` height per panel. Avoid tall source sizes such as `1536x2560` unless a deliberately vertical scene is needed.

Then use `scripts/build_long_comic.py`:

```bash
python3 wechat-comic-longform/scripts/build_long_comic.py \
  --spec output/comics/文章标题/article.json \
  --out output/comics/文章标题/文章标题-公众号漫画长图.png
```

For `风格一` and `风格二`, the script embeds article copy into the final image. For `风格三`, in-panel copy should already be inside the generated panel images; the script should only stack panels and add outer article text/spacing when needed. Images in the spec are resolved relative to the spec file unless absolute.

## Spec Blocks

Minimal spec:

```json
{
  "canvas_width": 600,
  "blocks": [
    {"type": "title", "text": "为什么下午三点最容易困？"},
    {"type": "paragraph", "text": "明明午饭也吃了，咖啡也喝了，怎么一到下午三点就开始断电？"},
    {"type": "image", "path": "panels/panel-01.png", "width": 540},
    {"type": "heading", "text": "首先，是身体在结账"},
    {"type": "callout", "text": "这不是你懒，是节律、血糖和睡眠债一起找上门。"},
    {"type": "paragraph", "text": "上午硬撑过去的疲劳，并不会消失。它只是换了个时间点，回来提醒你。"}
  ]
}
```

Supported block types: `title`, `subtitle`, `paragraph`, `heading`, `image`, `callout`, `spacer`, `rule`.

Additional style blocks supported by the layout script: `text_bars`, `emphasis`, `section_label`, `framed_image`. Image blocks and framed images can also include `speech_bubbles`; avoid these overlays for normal `风格三` output because panel dialogue should be generated by Seedream from quoted prompt text.

## Quality Gate

Before finishing, verify:

- The output is one vertical image and opens successfully.
- The output must use real generated panel images from the selected provider unless the user explicitly requested a layout-only mockup.
- If Seedream/即梦 generation failed because of API key, quota, billing, account overdue, or network errors, stop and explain the error instead of substituting vector or placeholder panels.
- Chinese text is embedded in the image, readable at mobile width, and not clipped.
- Centered Chinese lines should not end with decorative punctuation such as `，` `。` `；` `：`; clean these before stitching.
- Generated panels do not contain garbled text, watermarks, copied logos, or copied characters.
- For `风格一`, every panel must pass image-quality review: no generated text of any kind, distorted faces, duplicate heads, detached hair, fused bodies, extra/missing limbs, broken hands, rough storyboard texture, dirty sketch shading, or visibly inconsistent style. Regenerate failed panels before stitching.
- The article has a clear topic, hook, section rhythm, and ending.
- The result is an original public-account comic longform, not a deceptive imitation of a named author.
