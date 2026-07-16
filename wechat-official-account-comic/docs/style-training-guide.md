# Style Training Guide

Use this guide when the user asks to train, analyze, or add a new WeChat comic style to this skill.

## Contents

1. Inputs
2. Analysis pass
3. Style profile
4. Integration
5. Iteration memory
6. API usage

In this skill, "training a style" means distilling reference examples into reusable layout rules, writing rhythm, panel prompt language, negative constraints, and JSON templates. It does not mean model fine-tuning.

For end-to-end comic production, read `comic-creator-workflow.md` before choosing title metadata, writing scripts, drafting prompts, generating panels, building layouts, or finalizing long images.

## Inputs

Ask for or collect:

- 3-8 reference screenshots or finished long images for the target style.
- The intended content niche, such as AI, workplace, psychology, parenting, finance, or health.
- Whether generated panel images should be wordless or should contain model-rendered Chinese text. If the reference style treats picture and caption as one source image, choose `model-rendered` and make the prompt include quoted caption text.
- One test topic for a dry run.

Use references only for high-level traits during training. After a reusable style profile is saved, normal comic generation should be prompt-only from that profile, without attaching the reference screenshots. Do not copy account names, fixed characters, author signatures, logos, branded titles, or a named living artist's style.

## Analysis Pass

Extract only reusable production rules:

- Page: canvas width, background color or texture, margins, section rhythm, first-screen signal.
- Typography: section-label size, body size, bar labels, stroke text, speech bubble style, punctuation habits. The WeChat article title is metadata and should not become a long-image block.
- Layout: block order, panel density, text-to-image ratio, recurring components.
- Art direction: line weight, color palette, character proportions, scene types, finish level.
- Character system: broad archetypes only, not copied identities.
- Text policy: `wordless` when the layout script renders Chinese text; `model-rendered` when the image model must draw quoted Chinese inside panels or source images, including handwritten caption areas.
- Prompt key: the positive prompt phrase that should be appended to every panel request.
- Prompt recipe: the reusable prompt structure that worked in testing, including where exact quoted text belongs.
- Negative constraints: text, anatomy, brand, watermark, copied-character, and quality failures to reject.
- Validation notes: prompt-only test mode, what passed, what drifted, and what to adjust on the next iteration.

## Style Profile

Create a profile from `templates/style-profile-template.json` and save it as:

```text
wechat-official-account-comic/styles/<style-id>.json
```

Use lowercase kebab-case for `<style-id>` when the style is not a simple Chinese alias, for example `soft-workplace-healing.json`.

Required script fields:

- `name`: user-facing style name.
- `style_prompt`: reusable prompt fragment appended to every panel prompt.
- `text_policy`: either `wordless` or `model-rendered`.

Recommended documentation fields:

- `aliases`: names users may request.
- `description`: one-line use case.
- `layout`: canvas, background, block rhythm, reusable block types.
- `copy`: writing rhythm and punctuation rules.
- `quality_gate`: concrete rejection rules.
- `prompt_recipe`: optional but recommended for model-rendered or layout-sensitive styles.
- `validated_test`: optional but recommended after a prompt-only smoke test.

## Integration

1. Add the new style profile under `styles/`.
2. Add a short entry to `docs/style-guide.md` with the style name, use case, layout, art direction, text policy, and template path.
3. Add a style entry to `SKILL.md` if the style should be directly discoverable by Chinese name.
4. Create a new `templates/article-template-<style-id>.json` only if the layout cannot reuse an existing template.
5. Run a dry prompt without API calls:

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py --help
```

6. If API or Agent imagegen access is available, run a 1-2 panel smoke test before producing a full long image. For prompt-only production, do not attach training screenshots to this smoke test.
7. Record the smoke-test result in the style profile or style guide: exact text accuracy, visual match, forbidden artifacts, and known drift.
8. Build one final long image with `scripts/build_long_comic.py` and inspect readability, clipping, panel consistency, and prompt drift.

## Iteration Memory

Every training or production test should leave reusable lessons in the skill, not only in the chat thread:

- Add style-specific drift fixes to the profile's `validated_test.known_drift_and_tuning` list.
- Add cross-style selection rules to `docs/style-guide.md` when a new reference could be confused with an existing style.
- Keep failed prompt patterns out of `style_prompt`; record them as warnings or negative constraints instead.
- If a generated source image copies the reference QR code, account name, signature, side mark, fixed phrase, or fixed character, reject it and add a stronger no-brand/no-copied-identity rule.
- If the model renders quoted Chinese incorrectly, do not accept the panel. Shorten the caption lines, avoid rare characters, repeat the `Text to render exactly` block, and regenerate.
- If a style requires model-rendered caption text, prefer 2-5 short lines. Long paragraphs increase garbling and make the source image feel unlike the reference.
- If a new style is only validated by reference analysis, say so in `validated_test.mode`. After the first prompt-only image or final long-image test, update the validation note with what actually passed and what drifted.

## API Usage

The batch script defaults to Agnes Image. Use a saved profile by style id:

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style soft-workplace-healing
```

Or pass a profile explicitly:

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style-profile wechat-official-account-comic/styles/soft-workplace-healing.json
```

Use `AGNES_API_KEY` for the default Agnes path. To use Volcengine Ark/Doubao Seedream instead, pass `--provider seedream` and provide `DOUBAO_API_KEY` or `ARK_API_KEY`. To use 破局问问 GPT Image, pass `--provider 破局问问` and provide `BREAKOUT_API_KEY`; the old `--provider breakout` id remains compatible. Use repeated `--reference-image` only when the smoke test intentionally needs image editing or character continuity.

For `model-rendered` profiles, wrap every intended in-panel Chinese string in quotation marks in the panel prompt. If the style combines illustration and caption into one source image, quote each caption line and describe its placement and lettering style. The first smoke test must verify that the model produced one source image, copied the quoted Chinese accurately, and did not add QR codes, account names, signatures, watermarks, English, or unquoted text. For `wordless` profiles, keep all Chinese article text in `article.json` and let the layout script render it.
