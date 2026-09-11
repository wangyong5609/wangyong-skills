---
name: ppt-video-maker
description: 把 PPT(.pptx) 和口播文案（Word/文本）转成带配音和字幕的横版讲解视频（1920x1080 mp4）。流程：PPT 导出分页图 → 文案拆句写分镜 → 腾讯云 TTS（智斌 501000，已跑通的音色与语速）合成配音并取句级时间轴 → ffmpeg 合成带字幕成片。当用户要给 PPT 配讲解语音做成视频、把口播文案转成 PPT 讲解视频、或要求"用这个 PPT 和文案出片子"时使用。不适用于竖版短视频、Remotion 动画视频、或无 PPT 的纯文案视频。
---

# PPT 讲解视频制作

输入：一个 .pptx + 一份口播文案（.docx/.txt）。输出：横版 1920x1080 mp4，配音 + 底部字幕 + 分页切换。

## 一次性配置

```bash
cp .env.example .env   # 填入 TENCENT_SECRET_ID / TENCENT_SECRET_KEY
```

声音参数（智斌 501000、TTS 1.3x、播放 0.92、停顿 0.2s）已跑通并写死在脚本里，不要改、不要问用户。

依赖：ffmpeg、ffprobe、pdftoppm（poppler）、macOS PowerPoint、Python3（仅标准库）。

## 流程

### 1. PPT → 分页 PNG

```bash
scripts/export_slides.sh 输入.pptx slides/
# 产物 slides/slide-01.png …；必须用 PowerPoint 导 PDF，LibreOffice 中文是坏的
```

同时提取每页文字帮助理解内容（口播对页用）：

```bash
python3 -c "
from zipfile import ZipFile; import re, sys
z = ZipFile(sys.argv[1])
slides = sorted((n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)),
                key=lambda n: int(re.search(r'\d+', n.split('/')[-1]).group()))
for i, n in enumerate(slides, 1):
    texts = re.findall(r'<a:t>([^<]*)</a:t>', z.read(n).decode('utf8'))
    print(f'--- P{i} ---'); print(' / '.join(texts))
" 输入.pptx
```

### 2. 读文案，写分镜 storyboard.json

- 用 `textutil -convert txt 文案.docx -stdout` 读 Word 文案。
- 把口播按句拆成 beats，**每句一个 beat**，id 递增（b01、b02…）：
  ```json
  {"id": "run-id", "title": "片名",
   "beats": [{"id": "b01", "text": "口播句子。", "slide": 1, "high": false}, ...]}
  ```
- `slide`：这句讲解时画面停在第几页 PPT。按内容对页；章节过渡页可跳过不映射。
- `high: true`：该句所在页 PPT **底部有文字/红框/表格**，字幕需抬高避开。对着分页图逐页确认。
- **数字全部写成中文读法**（"72%"→"百分之七十二"、"2025年"→"二零二五年"），否则 TTS 读错且字幕对不上。
- 忽略文案里的制作标注（括号说明、分镜提示等），只取口播正文。
- 所有 beat 的 text 拼接必须就是完整口播，逐字不差（时间轴靠文本内容对齐）。

### 3. 合成配音

```bash
python3 scripts/tts_prepare.py storyboard.json --out runs/<run-id>/
# 产物：narration.mp3 + props.json（句级时间轴）+ storyboard.json 拷贝
```

失败处理见 references/pitfalls.md；时间轴对不上时先检查 storyboard 文本是否与口播逐字一致。

### 4. 合成成片

```bash
python3 scripts/make_video.py runs/<run-id>/ slides/ 输出.mp4
```

字幕规范已内置：结尾标点剥除、≤24 字按标点切分、默认 MarginV=130 / high 页 MarginV=210、PingFang SC、xfade 0.4s、片头 0.6s 片尾 1.6s。

### 5. 验收（必做）

抽帧核对字幕位置和内容，重点看 high 页是否还碰到底部文字：

```bash
ffmpeg -y -v error -ss <秒> -i 输出.mp4 -frames:v 1 frame.png   # 每个分页段抽 1-2 帧
```

用读图工具逐张检查：字幕不遮 PPT 内容、无结尾标点、无超宽换行。有问题改 storyboard（high 标记）或 make_video.py 的 MarginV 后重渲染即可——**重渲染不用重新合成配音**，除非改了口播文案。

## 工作目录约定

在项目目录下建 `runs/<run-id>/` 之外，分镜、分页图、成片都放项目目录，不要往 skill 目录写产物（.env 除外）。

## 踩坑清单

PPT 转图、TTS 时间戳、停顿后处理、字幕样式的所有已知坑见 [references/pitfalls.md](references/pitfalls.md)，动手前先读一遍。
