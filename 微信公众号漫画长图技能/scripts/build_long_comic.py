#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DEFAULT_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def load_font(size, bold=False, font_path=None):
    candidates = []
    if font_path:
        candidates.append(font_path)
    candidates.extend(DEFAULT_FONT_CANDIDATES)
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size, index=1 if bold else 0)
            except Exception:
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    pass
    return ImageFont.load_default()


def text_width(draw, text, font):
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap_cjk(draw, text, font, max_width):
    no_line_start = set("，。！？、；：）】》”’")
    lines = []
    for para in str(text).split("\n"):
        if not para:
            lines.append("")
            continue
        line = ""
        for char in para:
            test = line + char
            if line and text_width(draw, test, font) > max_width:
                if char in no_line_start:
                    lines.append(test)
                    line = ""
                else:
                    lines.append(line)
                    line = char
            else:
                line = test
        if line:
            lines.append(line)
    return lines


def render_text(draw, x, y, width, text, font, fill, align="center", line_gap=12, stroke_width=0, stroke_fill=None):
    lines = wrap_cjk(draw, text, font, width)
    line_h = math.ceil(font.size * 1.25)
    cursor = y
    for line in lines:
        w = text_width(draw, line, font)
        if align == "left":
            lx = x
        elif align == "right":
            lx = x + width - w
        else:
            lx = x + (width - w) / 2
        draw.text((lx, cursor), line, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        cursor += line_h + line_gap
    return cursor - y - line_gap if lines else 0


def fit_image(img, target_width):
    if img.width == target_width:
        return img
    scale = target_width / img.width
    target_height = max(1, round(img.height * scale))
    return img.resize((target_width, target_height), Image.Resampling.LANCZOS)


def fade_vertical_edges(panel, fade_px=36):
    if fade_px <= 0:
        return panel.convert("RGBA")
    rgba = panel.convert("RGBA")
    mask = Image.new("L", rgba.size, 255)
    draw = ImageDraw.Draw(mask)
    fade_px = min(fade_px, rgba.height // 3)
    for i in range(fade_px):
        alpha = round(255 * (i + 1) / fade_px)
        draw.line((0, i, rgba.width, i), fill=alpha)
        draw.line((0, rgba.height - 1 - i, rgba.width, rgba.height - 1 - i), fill=alpha)
    rgba.putalpha(mask)
    return rgba


def resolve_path(spec_dir, path):
    p = Path(path)
    return p if p.is_absolute() else spec_dir / p


def block_height(block, draw, fonts, spec_dir, canvas_width):
    t = block.get("type")
    margin_x = int(block.get("margin_x", 48))
    content_w = int(block.get("text_width", canvas_width - margin_x * 2))
    pad_top = int(block.get("pad_top", default_pad_top(t)))
    pad_bottom = int(block.get("pad_bottom", default_pad_bottom(t)))
    if t in ["image", "framed_image"]:
        img = Image.open(resolve_path(spec_dir, block["path"]))
        img = fit_image(img.convert("RGB"), int(block.get("width", canvas_width - 60)))
        if t == "framed_image":
            header_h = int(block.get("header_height", 54 if block.get("header") else 0))
            border = int(block.get("border", 10))
            return pad_top + header_h + img.height + border * 2 + pad_bottom
        return pad_top + img.height + pad_bottom
    if t == "text_bars":
        font = font_for_block(t, fonts, block)
        lines = bars_lines(block)
        bar_h = int(block.get("bar_height", math.ceil(font.size * 1.42)))
        gap = int(block.get("bar_gap", 9))
        return pad_top + len(lines) * bar_h + max(0, len(lines) - 1) * gap + pad_bottom
    if t == "section_label":
        font = font_for_block(t, fonts, block)
        lines = wrap_cjk(draw, block.get("text", ""), font, content_w)
        line_h = math.ceil(font.size * 1.25)
        return pad_top + len(lines) * line_h + max(0, len(lines) - 1) * line_h * 0.15 + pad_bottom
    if t == "spacer":
        return int(block.get("height", 40))
    if t == "rule":
        return pad_top + 1 + pad_bottom
    font = font_for_block(t, fonts, block)
    lines = wrap_cjk(draw, block.get("text", ""), font, content_w)
    line_gap = int(block.get("line_gap", default_line_gap(t)))
    line_h = math.ceil(font.size * 1.25)
    text_h = len(lines) * line_h + max(0, len(lines) - 1) * line_gap
    if t == "callout":
        text_h += 34
    return pad_top + text_h + pad_bottom


def default_pad_top(t):
    return {
        "title": 58,
        "subtitle": 12,
        "heading": 52,
        "image": 32,
        "framed_image": 26,
        "text_bars": 22,
        "emphasis": 42,
        "section_label": 46,
        "callout": 30,
        "rule": 40,
    }.get(t, 28)


def default_pad_bottom(t):
    return {
        "title": 24,
        "subtitle": 34,
        "heading": 22,
        "image": 36,
        "framed_image": 36,
        "text_bars": 22,
        "emphasis": 42,
        "section_label": 20,
        "callout": 30,
        "rule": 36,
    }.get(t, 24)


def default_line_gap(t):
    return {
        "title": 10,
        "subtitle": 10,
        "heading": 8,
        "callout": 10,
    }.get(t, 12)


def font_for_block(t, fonts, block):
    if "font_size" in block:
        return load_font(int(block["font_size"]), bold=block.get("bold", True), font_path=block.get("font"))
    if t == "title":
        return fonts["title"]
    if t == "subtitle":
        return fonts["subtitle"]
    if t == "heading":
        return fonts["heading"]
    if t == "callout":
        return fonts["callout"]
    if t == "text_bars":
        return fonts.get("bar", fonts["body"])
    if t == "emphasis":
        return fonts.get("emphasis", fonts["heading"])
    if t == "section_label":
        return fonts.get("section_label", fonts["heading"])
    return fonts["body"]


def bars_lines(block):
    if "lines" in block:
        return block["lines"]
    return [line for line in str(block.get("text", "")).split("\n") if line]


def line_text(line):
    return line.get("text", "") if isinstance(line, dict) else str(line)


def line_color(line, default):
    return line.get("color", default) if isinstance(line, dict) else default


def draw_speech_bubbles(draw, bubbles, origin_x, origin_y, panel_w, panel_h, font):
    for bubble in bubbles or []:
        x = origin_x + int(bubble.get("x", 0))
        y = origin_y + int(bubble.get("y", 0))
        w = int(bubble.get("width", panel_w * 0.35))
        h = int(bubble.get("height", 72))
        radius = int(bubble.get("radius", 18))
        fill = bubble.get("fill", "#ffffff")
        outline = bubble.get("outline", "#111111")
        draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=outline, width=int(bubble.get("outline_width", 2)))
        if bubble.get("tail"):
            tx = origin_x + int(bubble["tail"][0])
            ty = origin_y + int(bubble["tail"][1])
            base_y = y + h - radius
            draw.polygon([(x + w * 0.45, base_y), (x + w * 0.62, base_y), (tx, ty)], fill=fill, outline=outline)
        render_text(
            draw,
            x + 12,
            y + 10,
            w - 24,
            bubble.get("text", ""),
            font,
            bubble.get("text_color", "#111111"),
            bubble.get("align", "center"),
            int(bubble.get("line_gap", 2)),
        )


def draw_block(img, draw, y, block, fonts, spec_dir):
    canvas_width = img.width
    t = block.get("type")
    pad_top = int(block.get("pad_top", default_pad_top(t)))
    pad_bottom = int(block.get("pad_bottom", default_pad_bottom(t)))
    y += pad_top
    if t == "spacer":
        return y + int(block.get("height", 40))
    if t == "image":
        panel = Image.open(resolve_path(spec_dir, block["path"])).convert("RGB")
        panel = fit_image(panel, int(block.get("width", canvas_width - 60)))
        x = (canvas_width - panel.width) // 2
        pasted = fade_vertical_edges(panel, int(block.get("fade_edges", 0))) if block.get("fade_edges") else panel
        if block.get("radius"):
            radius = int(block["radius"])
            mask = Image.new("L", panel.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel.width, panel.height), radius=radius, fill=255)
            if block.get("fade_edges"):
                mask = Image.composite(pasted.getchannel("A"), mask, mask)
                img.paste(pasted.convert("RGB"), (x, y), mask)
            else:
                img.paste(panel, (x, y), mask)
        else:
            if block.get("fade_edges"):
                img.paste(pasted.convert("RGB"), (x, y), pasted.getchannel("A"))
            else:
                img.paste(panel, (x, y))
        draw_speech_bubbles(draw, block.get("speech_bubbles"), x, y, panel.width, panel.height, fonts["bubble"])
        return y + panel.height + pad_bottom
    if t == "framed_image":
        panel = Image.open(resolve_path(spec_dir, block["path"])).convert("RGB")
        panel = fit_image(panel, int(block.get("width", canvas_width - 84)))
        frame_w = panel.width + int(block.get("border", 10)) * 2
        border = int(block.get("border", 10))
        header_h = int(block.get("header_height", 54 if block.get("header") else 0))
        frame_h = header_h + panel.height + border * 2
        x = (canvas_width - frame_w) // 2
        radius = int(block.get("radius", 18))
        frame_color = block.get("frame_color", "#050505")
        draw.rounded_rectangle((x, y, x + frame_w, y + frame_h), radius=radius, fill=frame_color)
        if block.get("header"):
            render_text(draw, x + border, y + 13, frame_w - border * 2, block["header"], fonts["framed_header"], block.get("header_color", "#ffffff"), "center", 0)
        panel_x = x + border
        panel_y = y + header_h + border
        inner_radius = max(6, radius - border)
        mask = Image.new("L", panel.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel.width, panel.height), radius=inner_radius, fill=255)
        img.paste(panel, (panel_x, panel_y), mask)
        draw_speech_bubbles(draw, block.get("speech_bubbles"), panel_x, panel_y, panel.width, panel.height, fonts["bubble"])
        return y + frame_h + pad_bottom
    if t == "rule":
        margin = int(block.get("margin_x", 120))
        draw.line((margin, y, canvas_width - margin, y), fill=block.get("color", "#d9d9d9"), width=1)
        return y + 1 + pad_bottom

    margin_x = int(block.get("margin_x", 48))
    content_w = int(block.get("text_width", canvas_width - margin_x * 2))
    x = (canvas_width - content_w) // 2
    font = font_for_block(t, fonts, block)
    fill = block.get("color", default_color(t))
    align = block.get("align", "center")
    line_gap = int(block.get("line_gap", default_line_gap(t)))

    if t == "callout":
        temp_lines = wrap_cjk(draw, block.get("text", ""), font, content_w - 54)
        line_h = math.ceil(font.size * 1.25)
        text_h = len(temp_lines) * line_h + max(0, len(temp_lines) - 1) * line_gap
        box_h = text_h + 34
        box_color = block.get("bubble_color", "#f0a020")
        draw.rounded_rectangle((x, y, x + content_w, y + box_h), radius=18, fill=box_color)
        render_text(draw, x + 27, y + 17, content_w - 54, block.get("text", ""), font, block.get("text_color", "#222222"), "center", line_gap)
        return y + box_h + pad_bottom
    if t == "text_bars":
        lines = bars_lines(block)
        bar_h = int(block.get("bar_height", math.ceil(font.size * 1.42)))
        gap = int(block.get("bar_gap", 9))
        bar_color = block.get("bar_color", "#284f9b")
        text_color = block.get("text_color", "#ffffff")
        pad_x = int(block.get("bar_pad_x", 24))
        full_width = bool(block.get("full_width", False))
        max_bar_w = int(block.get("max_bar_width", content_w))
        min_bar_w = int(block.get("min_bar_width", 0))
        for line in lines:
            text = line_text(line)
            tw = text_width(draw, text, font)
            bar_w = content_w if full_width else min(max(tw + pad_x * 2, min_bar_w), max_bar_w)
            bx = (canvas_width - bar_w) // 2
            draw.rectangle((bx, y, bx + bar_w, y + bar_h), fill=line_color(line, bar_color))
            tx = bx + (bar_w - tw) / 2
            draw.text((tx, y + (bar_h - font.size) / 2 - 2), text, font=font, fill=line.get("text_color", text_color) if isinstance(line, dict) else text_color)
            y += bar_h + gap
        return y - gap + pad_bottom
    if t == "section_label":
        text_h = render_text(
            draw,
            x,
            y,
            content_w,
            block.get("text", ""),
            font,
            fill,
            align,
            line_gap,
            int(block.get("stroke_width", 2)),
            block.get("stroke_fill", "#111111"),
        )
        return y + text_h + pad_bottom

    stroke_width = int(block.get("stroke_width", 0))
    stroke_fill = block.get("stroke_fill")
    text_h = render_text(draw, x, y, content_w, block.get("text", ""), font, fill, align, line_gap, stroke_width, stroke_fill)
    return y + text_h + pad_bottom


def default_color(t):
    if t == "title" or t == "heading":
        return "#111111"
    if t == "subtitle":
        return "#666666"
    return "#222222"


def build(spec_path, out_path):
    spec_path = Path(spec_path)
    spec_dir = spec_path.parent
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    canvas_width = int(spec.get("canvas_width", 600))
    probe = Image.new("RGB", (canvas_width, 100), "white")
    draw = ImageDraw.Draw(probe)
    font_path = spec.get("font")
    fonts = {
        "title": load_font(int(spec.get("title_size", 36)), bold=True, font_path=font_path),
        "subtitle": load_font(int(spec.get("subtitle_size", 24)), font_path=font_path),
        "heading": load_font(int(spec.get("heading_size", 34)), bold=True, font_path=font_path),
        "body": load_font(int(spec.get("body_size", 26)), font_path=font_path),
        "callout": load_font(int(spec.get("callout_size", 23)), bold=True, font_path=font_path),
        "bar": load_font(int(spec.get("bar_size", 24)), bold=True, font_path=font_path),
        "emphasis": load_font(int(spec.get("emphasis_size", spec.get("heading_size", 34))), bold=True, font_path=font_path),
        "section_label": load_font(int(spec.get("section_label_size", 36)), bold=True, font_path=font_path),
        "framed_header": load_font(int(spec.get("framed_header_size", 30)), bold=True, font_path=font_path),
        "bubble": load_font(int(spec.get("bubble_size", 20)), bold=True, font_path=font_path),
    }
    heights = [block_height(b, draw, fonts, spec_dir, canvas_width) for b in spec["blocks"]]
    total_height = max(1, int(sum(heights) + spec.get("bottom_padding", 64)))
    img = Image.new("RGB", (canvas_width, total_height), spec.get("background", "#ffffff"))
    draw = ImageDraw.Draw(img)
    if spec.get("background_pattern") == "soft_diagonal":
        color = spec.get("background_pattern_color", "#96b65b")
        for offset in range(-total_height, canvas_width, 18):
            draw.line((offset, 0, offset + total_height, total_height), fill=color, width=1)
    y = 0
    for block in spec["blocks"]:
        y = draw_block(img, draw, y, block, fonts, spec_dir)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {}
    if out_path.suffix.lower() in [".jpg", ".jpeg"]:
        save_kwargs.update(quality=92, optimize=True)
    img.save(out_path, **save_kwargs)
    print(f"wrote {out_path} ({img.width}x{img.height})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    build(args.spec, args.out)


if __name__ == "__main__":
    main()
