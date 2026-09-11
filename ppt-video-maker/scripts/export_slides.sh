#!/bin/bash
# PPTX → 分页 PNG（slide-01.png …）
# 用法: export_slides.sh 输入.pptx 输出目录
#
# 必须用 PowerPoint 导出 PDF 再转 PNG。不要用 LibreOffice：
# 本机 LibreOffice 中文渲染是坏的（全部豆腐块），装字体、换 profile 都无效。
set -euo pipefail

PPTX="$1"
OUT="$2"
mkdir -p "$OUT"
PPTX_ABS="$(cd "$(dirname "$PPTX")" && pwd)/$(basename "$PPTX")"
OUT_ABS="$(cd "$OUT" && pwd)"
PDF="$OUT_ABS/slides.pdf"

export_pdf() {
  osascript <<EOF
tell application "Microsoft PowerPoint"
    set pptxName to "$(basename "$PPTX_ABS")"
    if not (exists presentation pptxName) then
        open POSIX file "$PPTX_ABS"
    end if
    save presentation pptxName in POSIX file "$PDF" as save as PDF
end tell
EOF
}

# PowerPoint 自动化偶发超时（-9074/-128）或静默失败，导出后验证 PDF 存在，失败重试一次
if ! export_pdf || [ ! -f "$PDF" ]; then
  echo "PowerPoint 导出失败，3 秒后重试…" >&2
  sleep 3
  export_pdf
fi
[ -f "$PDF" ] || { echo "PDF 导出失败: $PDF" >&2; exit 1; }

pdftoppm -png -r 120 "$PDF" "$OUT/slide"

# pdftoppm 按总页数补零，统一命名为两位 slide-01.png
for f in "$OUT"/slide-*.png; do
  base="$(basename "$f" .png)"
  num="${base#slide-}"
  num=$((10#$num))
  target="$OUT/$(printf 'slide-%02d.png' "$num")"
  [ "$f" = "$target" ] || mv "$f" "$target"
done

echo "OK -> $OUT ($(ls "$OUT"/slide-*.png | wc -l | tr -d ' ') 页)"
