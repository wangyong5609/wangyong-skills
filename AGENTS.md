# Repository Guidelines

## Project Structure & Module Organization

This repository stores standalone AI Agent skills. Each skill lives in its own top-level directory and should include a `SKILL.md` entry point with YAML frontmatter:

```text
skill-name/
  SKILL.md
  scripts/
  docs/
  templates/
  agents/ or config/
```

Current examples include `macos-app-icon/`, `wechat-article-collector/`, `wechat-comic-longform/`, `life-interview-planner/`, and `ai-creator-cover/`. Put reusable Python or shell helpers in `scripts/`, reference material in `docs/` or `references/`, static prompt/data files in `templates/`, and model or agent settings in `agents/` or `config/`.

## Build, Test, and Development Commands

There is no repository-wide build system yet. Work within the skill directory you are changing.

Useful commands:

```bash
git status --short
python3 path/to/script.py --help
python3 -m py_compile path/to/script.py
```

Use `--help` to verify script interfaces, and `py_compile` as a quick syntax check for Python scripts. If a skill adds dependencies, document install and run commands inside that skill's `SKILL.md`.

## Coding Style & Naming Conventions

Prefer kebab-case directory names for new skills, matching the skill `name` in `SKILL.md` frontmatter. Keep Markdown direct and task-oriented. For Python, use 4-space indentation, clear `argparse` options, and environment variables for local configuration. Avoid committing generated outputs, local IDE state, `.DS_Store`, credentials, cookies, API keys, or user private exports.

When adding a skill, include:

```yaml
---
name: example-skill
description: Short trigger-focused description.
---
```

## Testing Guidelines

No formal test framework is configured at the root. For script-based skills, add focused tests when behavior is non-trivial, preferably near the script as `test_*.py` or `*.test.py`. At minimum, run syntax checks and a small dry run or limited command, for example:

```bash
python3 -m py_compile wechat-article-collector/scripts/collect_wechat_articles.py
python3 -m py_compile wechat-comic-longform/scripts/build_long_comic.py
python3 wechat-article-collector/scripts/collect_wechat_articles.py --help
```

Do not run commands that call paid or rate-limited APIs unless credentials and scope are explicit.

## Commit & Pull Request Guidelines

The current history starts with `Initial commit`, so use simple imperative commit messages going forward, such as `Add wechat article collector skill` or `Update macOS icon workflow`.

Pull requests should describe the changed skill, list verification commands, mention any new environment variables, and include screenshots or sample outputs for visual or generated-asset workflows.

## Security & Configuration Tips

Keep secrets outside the repository. Use `.env` files, local config files, or environment variables, and document required variable names without real values. If a script writes into external folders, make the output path explicit and avoid deleting unrelated files.
