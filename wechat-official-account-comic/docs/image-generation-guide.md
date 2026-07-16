# Image Generation Guide

Read this file before any panel generation. Select the path from the current runtime and available tools, not from API-key presence alone.

## Contents

1. Runtime detection and persistent preference
2. First-use selection
3. Codex built-in imagegen
4. Third-party provider selection
5. Secret handling
6. Batch script commands
7. Reference images
8. Failure and recovery
9. Output timing and manifest

## 1. Runtime Detection And Persistent Preference

Inspect the capabilities exposed to the current agent, then read the provider preference before choosing a path.

Preference files are user-level and survive Skill updates:

- Codex: `~/.codex/preferences/wechat-official-account-comic.json`
- WorkBuddy: `~/.workbuddy/preferences/wechat-official-account-comic.json`
- Generic runtime: `~/.config/wechat-official-account-comic/preferences.json`

Use the helper instead of hand-editing JSON:

```bash
python3 wechat-official-account-comic/scripts/provider_preference.py --runtime codex get
python3 wechat-official-account-comic/scripts/provider_preference.py --runtime codex set codex-imagegen
python3 wechat-official-account-comic/scripts/provider_preference.py --runtime codex clear
```

`get` exits with status `3` when no preference exists. The file stores only provider id, version, and update time. Never store keys or other secrets.

Do not treat installed files, API-key presence, or a guessed environment variable as proof that built-in image generation is available. Use the actual runtime identity and currently exposed tool list.

## 2. First-Use Selection

Before the first image-generation job:

1. Detect `codex`, `workbuddy`, or `generic` from the actual runtime.
2. Run the preference helper with that explicit runtime.
3. If a valid saved provider is available, use it and continue.
4. If no preference exists, show the choices below and **STOP** for the user's selection.
5. Save the confirmed choice before continuing to `PROMPTS` or `PANELS`.

Codex menu:

- **Codex 内置 imagegen（推荐）**: no API key; one built-in call per panel.
- **破局问问**: requires `BREAKOUT_API_KEY`; two concurrent panels by default.
- **Agnes Image**: requires an Agnes key.
- **Seedream/即梦**: requires a Doubao/Ark key.

WorkBuddy or generic menu:

- **Agnes Image（推荐）**: default non-Codex HTTP path; requires an Agnes key.
- **破局问问**: requires `BREAKOUT_API_KEY`; two concurrent panels by default.
- **Seedream/即梦**: requires a Doubao/Ark key.

If the user's request already says which provider to use and no preference exists, save that provider as the first-use choice without asking again. A phrase such as “这次用破局问问” is a one-job override only when a saved preference already exists. Change the persistent preference only for explicit language such as “以后默认破局问问” or “更换默认生图方式”.

If a saved choice is unavailable, do not delete or replace it automatically. Explain the incompatibility, offer valid choices, and wait.

## 3. Codex Built-In Imagegen

When running in Codex with built-in `image_gen`:

- Load and follow the system `imagegen` skill before generating.
- Use built-in tool mode for normal generation and editing.
- Do not request `OPENAI_API_KEY`.
- Issue one built-in call per panel or distinct prompt. The word `batch` does not authorize CLI fallback.
- Do not run `scripts/generate_panels_seedream.py` for the Codex built-in path.
- Do not switch to `scripts/image_gen.py` or another CLI merely for quality, size, filenames, or multiple panels.
- If the built-in tool is unavailable or fails, report that fact. Offer the user a choice of Agnes, Seedream, 破局问问, or the imagegen CLI fallback; use none without explicit approval.

Built-in outputs are saved under Codex-managed storage by default. After each accepted generation:

1. locate the generated output under the Codex generated-image area;
2. copy or move it into the comic project's `panels/` directory;
3. name it `panel-01.png`, `panel-02.png`, and so on;
4. never overwrite an existing accepted panel unless the user requested replacement;
5. keep every project-referenced panel inside the project, not only in Codex-managed storage.

Do not describe or rely on a destination-path parameter for built-in `image_gen`. For local image edits, inspect the target with `view_image` first so it is visible to the built-in tool.

## 4. Third-Party Provider Selection

- **Agnes Image 2.0 Flash (default HTTP path)**: run `scripts/generate_panels_seedream.py` without `--provider`. Endpoint: `https://apihub.agnes-ai.com/v1/images/generations`.
- **Volcengine Ark/Doubao Seedream**: pass `--provider seedream`.
- **破局问问 GPT Image**: pass `--provider 破局问问`; legacy `--provider breakout` remains compatible. Default concurrency is two panels.

Use the selected style profile's `text_policy`. Generate every storyboard row as a separate panel and keep the approved numbering stable.

## 5. Secret Handling

Read keys from:

1. explicit `--env-file /path/to/.env`;
2. exported environment variables;
3. `.env` in the current working directory.

Use `--api-key-stdin` for hidden process-local input. Never request a key in chat or write it into tracked files.

Provider variables:

- Agnes: `AGNES_API_KEY`; aliases `GNES_API_KEY`, `AGNESAI_API_KEY`.
- Seedream: `DOUBAO_API_KEY`; fallback `ARK_API_KEY`.
- 破局问问: `BREAKOUT_API_KEY`.

## 6. Batch Script Commands

Install the layout dependency when needed:

```bash
python3 -m pip install -r wechat-official-account-comic/requirements.txt
```

Agnes default:

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style 暖白手绘漫画
```

Seedream:

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --provider seedream \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style 暖白手绘漫画 \
  --size 2304x1728
```

破局问问, two concurrent jobs by default:

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --provider 破局问问 \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style 绿底粗线漫画 \
  --skip-existing \
  --workers 2
```

Use `--style <style-id>` for a profile under `styles/`, or `--style-profile /absolute/path/profile.json` for an explicit/copy-external profile.

These commands are third-party HTTP paths only. They are not the Codex built-in imagegen path.

## 7. Reference Images

Normal production is prompt-only after a style profile exists. Use references only for explicit training, comparison, character continuity, cover merging, or image editing.

With 破局问问, repeat `--reference-image`; the script switches to `/v1/images/edits` and uploads each file under repeated multipart field `image`. Do not use `files[]`.

```bash
python3 wechat-official-account-comic/scripts/generate_panels_seedream.py \
  --provider 破局问问 \
  --prompts output/comics/文章标题/panel-prompts.json \
  --out-dir output/comics/文章标题/panels \
  --style 暖白手绘漫画 \
  --reference-image output/comics/文章标题/cover.png \
  --reference-image output/comics/文章标题/character.png \
  --quality low
```

## 8. Failure And Recovery

On any provider failure, stop the production gate and report the real error. Preserve prompts, completed panels, pending responses, manifest, references, and `article.json`. Never switch provider or substitute placeholders silently.

For Codex built-in failures, follow the `imagegen` skill: report that the built-in path failed or is unavailable. Do not automatically use its CLI fallback or a third-party provider; continue only after the user chooses a fallback.

### General Checks

Check the provider key, account state, balance/quota, model name, request parameters, network access, and request id.

Use `--retries 1 --retry-delay 30` only when the user explicitly accepts a retry for 429/502/503/504. Default is no retry because a timeout may already have created a billable image.

### 破局问问 Protected Downloads

Generation may complete while the returned image URL responds with 401/403. The script:

- saves `panel-NN-pending-response.json` before download;
- applies browser download headers;
- forwards the API key only to the API host or its subdomains;
- recovers the pending response on the next identical run before submitting a new generation.

Rerun the same command with `--skip-existing`. Use `--regenerate-pending` only after the user accepts possible duplicate billing. With concurrency, stop scheduling new panels after the first failure while allowing active jobs to finish and save.

For image edits, verify every reference path exists and uses the repeated `image` field.

### Seedream Billing Errors

For `AccountOverdueError`, `InsufficientBalance`, quota exhaustion, or similar billing errors:

1. State that the account tied to the key cannot call the model because it is overdue or lacks balance/quota.
2. Ask the user to recharge or clear overdue bills in the same Volcengine account.
3. Preserve prompts and partial outputs for a direct retry.
4. Do not produce a fake final comic from local placeholder art.

## 9. Output Timing And Manifest

破局问问 defaults to two workers; override with `--workers N`. The manifest records total elapsed time and per-panel generation, download, and total duration.

Use `--skip-existing` to preserve completed panels. Review the manifest and file count before marking the `PANELS` gate as complete.
