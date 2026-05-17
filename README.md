# wangyong-skills

一组面向中文创作者和个人效率场景的 AI Agent skills。它们不是某一个 Agent 的专属格式，只要你的 Agent 支持读取 `SKILL.md` 形式的技能目录，就可以按自己的安装方式使用。

## 包含哪些 skills

| Skill | 用途 |
| --- | --- |
| `wechat-article-collector` | 采集微信公众号历史文章，导出 Markdown、账号概览和 CSV 数据。 |
| `微信公众号漫画长图技能` | 把主题、草稿或文章结构做成微信公众号漫画长图。 |
| `macos-app-icon` | 生成、优化和打包 macOS 应用图标 `.icns`。 |
| `life-interview-planner` | 通过结构化访谈挖掘人生可能性、优势假设、价值观和验证实验。 |

## 怎么安装

最简单的方式是把下面这段话复制给你的 AI Agent：

```text
请帮我安装这个 GitHub 仓库里的 AI Agent skills：
https://github.com/wangyong5609/wangyong-skills

请先确认你当前环境支持的 skills 安装目录和格式，然后下载这个仓库，把里面的 skill 目录安装到正确位置。安装完成后，请告诉我安装了哪些 skill，以及是否需要重启 Agent 或新开会话。
```

如果你只想安装其中一个 skill，把上面那段话改成：

```text
请帮我只安装这个仓库里的 <skill目录名>：
https://github.com/wangyong5609/wangyong-skills

请先确认你当前环境支持的 skills 安装目录和格式，然后只安装这个 skill。
```

可选的 `<skill目录名>`：

- `wechat-article-collector`
- `微信公众号漫画长图技能`
- `macos-app-icon`
- `life-interview-planner`

如果你的 Agent 使用 Codex 兼容目录，通常可以把 skill 目录放到 `~/.codex/skills/`。

## 怎么使用

安装后，在支持 skills 的 Agent 里直接描述需求即可。也可以显式写 skill 名：

```text
Use $wechat-article-collector 采集「公众号名称」的历史文章，保存到我指定的目录。
```

```text
Use $wechat-comic-longform 把「主题」做成风格一的公众号漫画长图。
```

```text
Use $macos-app-icon 根据这张图片生成 macOS .icns 图标，并给我灰底预览。
```

```text
Use $life-interview-planner 和我做一次 60 分钟的人生方向访谈。
```

## API 配置

有些 skill 会调用第三方服务，需要你自己准备 API key。

公众号文章采集需要大加啦/极致了 API key。可以打开官方接口页注册或登录：

```text
https://www.dajiala.com/main/interface?actnav=0
```

漫画长图如果使用 Seedream/Doubao 批量生图，需要火山方舟/豆包图片模型 API key。你也可以让 Agent 使用它自己可用的 imagegen 能力生成 panels，再用本仓库的脚本拼接长图。

可以复制 `.env.example` 为本地 `.env`，填入自己的 key：

```bash
cp .env.example .env
```

常用变量：

- `DAJIALA_API_KEY`
- `DAJIALA_VERIFY_CODE`
- `DAJIALA_COOKIE`
- `DOUBAO_API_KEY`
- `ARK_API_KEY`

## 依赖

Python 脚本使用 Python 3。漫画长图拼接需要 Pillow：

```bash
python3 -m pip install -r requirements.txt
```

macOS 图标 skill 建议安装 ImageMagick，以便使用 `magick` 处理图片；在 macOS 上打包 `.icns` 时会优先使用系统自带的 `iconutil`。

## 目录结构

每个 skill 都是一个独立目录，核心入口是 `SKILL.md`：

```text
skill-name/
  SKILL.md
  agents/ or config/
  scripts/
  docs/ or references/
  templates/
```

不同 skill 不一定包含所有子目录。
