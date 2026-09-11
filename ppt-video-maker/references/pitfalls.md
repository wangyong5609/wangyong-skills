# 踩坑记录（PPT 讲解视频管线）

## PPT 转图

- **LibreOffice 中文渲染完全坏**：所有中文变豆腐块。装 Noto 字体、换用户 profile、换导出格式都无效。必须用 macOS 的 PowerPoint AppleScript 导出 PDF，再 `pdftoppm -png -r 120` 转 PNG。`export_slides.sh` 已封装。
- **PowerPoint 自动化偶发失败**：报 -9074 / -128 / -1712 等错误，属正常抖动，重试即可；脚本已内置一次重试。若反复 -1712（AppleEvent 超时），说明 PowerPoint 里卡着一个未处理的弹窗（恢复文件/登录/格式提示等），所有自动化都会被挡住——让用户去点掉弹窗，或退出 PowerPoint 重开后再跑。文件已在 PowerPoint 中打开时不要重复 open（会触发 -9074），脚本已判断，直接对已打开的文档 save as PDF。
- pdftoppm 按总页数给序号补零（9 页以下是 `slide-1.png`，10 页以上是 `slide-01.png`），脚本已统一改成两位命名。

## 配音（腾讯云 TTS）

- 时间轴依赖 `EnableSubtitle: true` 返回的字级时间戳；**不是所有音色都支持**，501000（智斌）已验证支持。换音色必须先验证时间戳可用。
- 单次合成文本上限约 150 字，脚本按 140 字在句末标点处切分；多段 MP3 用 ffmpeg concat 合并，时间戳按各段实测时长累加偏移。
- 腾讯云 Speed 参数不是倍速本身，是 [-2, 6] 的分段线性映射（1.0→0，1.2→1，1.5→2），`tts_prepare.py` 里的 `tencent_speed()` 已处理。
- **文案里的数字必须先写成中文读法**（"72%"→"百分之七十二"、"100万-800万"→"一百万到八百万"），否则 TTS 读法不可控、字幕也对不上。

## 字幕（用户已确认的规范，勿回退）

- **结尾标点剥除**——字幕行尾不允许出现 `，。、；：？！—…·`。
- 单条字幕 ≤24 字，超出在标点处切分、按字数均摊时间。
- 默认样式 MarginV=130（底部）；**PPT 页底部有文字/红框/表格延伸到底部时**，该页的 beat 要标 `high: true`，字幕用 MarginV=210 抬高。若抽帧发现仍轻微相碰，把 `make_video.py` 里 High 的 MarginV 调到 240–260 重渲染。
- 字体用 PingFang SC + `fontsdir=/System/Library/Fonts`，ASS 烧录正常；不要换不存在的字体名。

## 合成

- 停顿处理是**后处理**不是 TTS 参数：atempo 0.92 后 silencedetect（-40dB / 0.15s）找静音段，每段只保留 0.2s，然后把字幕和分页边界的时间轴同步重映射。改 MAX_PAUSE_MS 会同时影响节奏和所有时间轴，勿单独改一处。
- silencedetect 对裸 PCM 流检测不可靠，必须先包成 WAV 再检测（脚本已处理）。
- xfade 的 offset 是累计的：第 i 段 offset = 前 i-1 段时长之和减去重叠，改 FADE 或分段逻辑时注意。
