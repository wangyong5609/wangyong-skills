---
name: macos-app-icon
description: 创建或优化 macOS 应用图标，尤其是 .icns 文件、圆角方形图标底板、透明 PNG、Dock 预览图和图标替换资源。Use when the user asks to design, resize, convert, troubleshoot, or package macOS application icons.
---

# macOS 应用图标

## 目标

产出一个可放进 Dock 的 macOS 图标，小尺寸下也要清楚、干净、有设计感：

- 符号一眼能认出
- 没有意外黑边、脏背景
- 使用圆角方形底板时，底板外区域保持透明
- 输出 `.icns`，并附预览 PNG

## 依赖

优先使用系统和常见命令行工具：

- ImageMagick：提供 `magick`，用于抠图、缩放、合成预览和 iconset PNG。
- macOS `iconutil`：把 `.iconset` 打包成 `.icns`。
- Python 3：仅在 `iconutil` 无法打包有效 iconset 时，用作手写 ICNS 容器的 fallback。

如果缺少 `magick`，先提醒用户安装 ImageMagick，不要假装已经完成转换。

## 输出目录

默认把中间文件和结果放到用户指定目录；没有指定时使用：

```text
output/app-icon/
```

不要把用户原始图片、生成的 `.icns`、临时 `.iconset/` 或预览 PNG 提交到仓库，除非它们是明确准备公开的示例资产。

## 默认流程

1. 只在必要时确认视觉需求：主体符号、配色、背景风格。
2. 创建或获取高分辨率 PNG，通常为 `1024x1024` 或更大。
3. 转换前先自查原图：
   - 主体是否一眼能认出？
   - 是否居中并有足够留白？
   - 是否有多余边框、阴影、黑角或背景残留？
4. 如果用户想要 VS Code 风格的 macOS 图标，按这个结构合成：
   - 透明画布
   - 白色圆角方形，约从 `96,96` 到 `928,928`
   - 圆角半径约 `150`
   - 主体符号居中，宽高通常 `560-680px`，视形状调整
5. 最终交付前先做灰底预览图。
6. 用多尺寸 PNG 生成 `.icns`。
7. 只汇报关键输出文件。

## 图片生成建议

使用图像模型生成时：

- 要求纯净、居中、适合作图标的主体符号。
- 如果需要抠图，优先要求“白底黑色主体”。
- 除非用户明确要求，不要让模型生成 macOS 阴影、边框、渐变或装饰背景。
- 打包前必须检查生成图。

推荐提示词模板：

```text
Create a clean minimalist macOS-style app icon symbol of [object], strict [colors].
The object should be instantly recognizable, centered with generous padding.
No text, no border, no shadow, no gradient, no extra objects.
Use [foreground] on a pure white background, crisp edges, icon-ready, 1024x1024.
```

## 透明抠图

黑色主体 + 白色背景时，优先用阈值/容差抠图，然后放到非白背景上预览：

```bash
magick input.png -alpha set -fuzz 18% -transparent white -channel A -threshold 35% +channel symbol-transparent.png
magick symbol-transparent.png -background '#7a8780' -alpha remove -alpha off symbol-preview.png
```

如果预览发灰或有雾感，说明还有背景残留。提高 `-fuzz`、提高 alpha 阈值，或重新生成更干净的白底图。

## 白色圆角底板

合成类似 VS Code 的白色圆角底板，底板外透明：

```bash
magick -size 1024x1024 canvas:none \
  -fill white -draw 'roundrectangle 96,96 928,928 150,150' \
  \( symbol-transparent.png -resize 620x620 \) \
  -gravity center -compose over -composite icon-rounded-white.png

magick icon-rounded-white.png -background '#7a8780' -alpha remove -alpha off icon-rounded-white-preview.png
```

自查预览：

- 外侧圆角区域显示预览底色，而不是黑色
- 白色圆角底板边缘平滑
- 主体不要过大
- 视觉居中，不只是数学居中

## ICNS 打包

生成 iconset 尺寸：

```bash
mkdir -p /private/tmp/icon.iconset
magick icon-rounded-white.png -resize 16x16 PNG32:/private/tmp/icon.iconset/icon_16x16.png
magick icon-rounded-white.png -resize 32x32 PNG32:/private/tmp/icon.iconset/icon_16x16@2x.png
magick icon-rounded-white.png -resize 32x32 PNG32:/private/tmp/icon.iconset/icon_32x32.png
magick icon-rounded-white.png -resize 64x64 PNG32:/private/tmp/icon.iconset/icon_32x32@2x.png
magick icon-rounded-white.png -resize 128x128 PNG32:/private/tmp/icon.iconset/icon_128x128.png
magick icon-rounded-white.png -resize 256x256 PNG32:/private/tmp/icon.iconset/icon_128x128@2x.png
magick icon-rounded-white.png -resize 256x256 PNG32:/private/tmp/icon.iconset/icon_256x256.png
magick icon-rounded-white.png -resize 512x512 PNG32:/private/tmp/icon.iconset/icon_256x256@2x.png
magick icon-rounded-white.png -resize 512x512 PNG32:/private/tmp/icon.iconset/icon_512x512.png
magick icon-rounded-white.png -resize 1024x1024 PNG32:/private/tmp/icon.iconset/icon_512x512@2x.png
```

优先用 `iconutil`：

```bash
iconutil --convert icns --output app-icon.icns /private/tmp/icon.iconset
```

如果 `iconutil` 拒绝有效 iconset，用 PNG chunk 手写 ICNS 容器：

```bash
python3 -c 'exec("from pathlib import Path\nchunks=[(\"icp4\",\"/private/tmp/icon.iconset/icon_16x16.png\"),(\"icp5\",\"/private/tmp/icon.iconset/icon_32x32.png\"),(\"icp6\",\"/private/tmp/icon.iconset/icon_32x32@2x.png\"),(\"ic07\",\"/private/tmp/icon.iconset/icon_128x128.png\"),(\"ic08\",\"/private/tmp/icon.iconset/icon_256x256.png\"),(\"ic09\",\"/private/tmp/icon.iconset/icon_512x512.png\"),(\"ic10\",\"/private/tmp/icon.iconset/icon_512x512@2x.png\")]\nbody=b\"\"\nfor typ,p in chunks:\n    data=Path(p).read_bytes()\n    body += typ.encode(\"ascii\") + (len(data)+8).to_bytes(4,\"big\") + data\nPath(\"app-icon.icns\").write_bytes(b\"icns\" + (len(body)+8).to_bytes(4,\"big\") + body)\n")'
```

验证：

```bash
file app-icon.icns
ls -lh app-icon.icns
```

预期结果包含：`Mac OS X icon`。

## 常见问题

- **Dock 里有黑角**：源图或预览里的底板外透明区域变黑了。用 `canvas:none` 重新合成，并在灰底上预览。
- **图标显得太大**：主体留白不足。合成前把主体缩小，通常 `560-680px`。
- **抠图后有白雾**：白底没去干净。调大 fuzz/threshold，或重新生成干净白底图。
- **不像用户要的对象**：先重新生成或重画，不要急着转 `.icns`，转换修不好语义。
- **`iconutil: Invalid Iconset`**：检查文件名和尺寸；还不行就用手写 ICNS 容器。

## 交付

简洁返回这些路径：

- 最终 `.icns`
- 可编辑/源 PNG
- 灰底预览 PNG

预览没有目检前不要交付。
