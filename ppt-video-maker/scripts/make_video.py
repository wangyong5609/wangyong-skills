#!/usr/bin/env python3
"""配音 + PPT 分页图 → 横版讲解成片（1920x1080，H.264+AAC）。

用法:
  python3 make_video.py RUN_DIR SLIDES_DIR OUT.mp4

  RUN_DIR     tts_prepare.py 的输出目录（props.json / narration.mp3 / storyboard.json）
  SLIDES_DIR  分页 PNG 目录，命名 slide-01.png（export_slides.sh 的产物）
  OUT.mp4     输出路径

内置处理（均已按用户确认定死，不要改默认值）:
  - atempo 0.92 播放加速（配合 TTS 1.3x，等效约 1.41 倍速）
  - 句间停顿统一压到 0.2s，字幕/分页时间轴同步重映射
  - 字幕单条 ≤24 字，超长按标点切分、按字数均摊时间
  - 字幕结尾标点剥除
  - 字幕默认 MarginV=130；storyboard 里 high=true 的句子用 High 样式 MarginV=210
    （该页 PPT 底部有文字时避免遮挡；若仍轻微相碰，把 High 的 MarginV 调大到 240-260）
  - 分页淡入淡出 xfade 0.4s，片头留白 0.6s，片尾 1.6s
"""
import json
import re
import subprocess
import sys
from pathlib import Path

RATE, LEAD_MS, TAIL_MS, MAX_PAUSE_MS, SR, FADE = 0.92, 600, 1600, 200, 16000, 0.4
CAP_MAX = 24
TRAIL_PUNCT = "，。、；：？！—…·"   # 字幕结尾标点剥除
SPLIT_PUNCT = "，；。、：？！—"

if len(sys.argv) != 4:
    sys.exit(__doc__)
RUN, SLIDES_DIR, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
props = json.loads((RUN / "props.json").read_text())
story = json.loads((RUN / "storyboard.json").read_text())
beats = story["beats"]


def sh(cmd, **kw):
    binary = isinstance(kw.get("input"), bytes)
    r = subprocess.run(cmd, capture_output=True, text=not binary, **kw)
    if r.returncode != 0:
        err = r.stderr if isinstance(r.stderr, str) else r.stderr.decode(errors="replace")
        print(err[-3000:])
        raise SystemExit(1)
    return r


# --- 音频: atempo → 静音检测 → 停顿裁到 0.2s ---
pcm = RUN / "voice_rate.pcm"
sh(["ffmpeg", "-y", "-v", "error", "-i", str(RUN / "narration.mp3"),
    "-af", f"atempo={RATE}", "-ac", "1", "-ar", str(SR), "-f", "s16le", str(pcm)])
wav_tmp = RUN / "voice_rate.wav"
sh(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1",
    "-i", str(pcm), str(wav_tmp)])
r = subprocess.run(["ffmpeg", "-i", str(wav_tmp), "-af", "silencedetect=n=-40dB:d=0.15",
                    "-f", "null", "-"], capture_output=True, text=True)
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
assert len(starts) == len(ends), "静音检测结果异常"
silences = list(zip(starts, ends))
print(f"静音段 {len(silences)} 个")

data = pcm.read_bytes()
def ms2b(ms):
    return int(ms / 1000 * SR) * 2

buf = bytearray()
cur = 0.0
for s, e in silences:
    keep = min(e - s, MAX_PAUSE_MS / 1000)
    buf += data[ms2b(cur * 1000):ms2b(s * 1000)]
    buf += data[ms2b(s * 1000):ms2b((s + keep) * 1000)]
    cur = e
buf += data[ms2b(cur * 1000):]
voice_final = RUN / "voice_final.wav"
sh(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1",
    "-i", "-", str(voice_final)], input=bytes(buf))
audio_ms = len(buf) / 2 / SR * 1000
print(f"音频 {len(data) / 2 / SR:.1f}s -> {audio_ms / 1000:.1f}s")


def remap(t_ms):
    """原始音频时间轴 → 裁停顿后的时间轴"""
    removed = 0.0
    for s, e in silences:
        s_ms, e_ms = s * 1000, e * 1000
        rs = s_ms + min(e_ms - s_ms, MAX_PAUSE_MS)
        removed += max(0.0, min(t_ms, e_ms) - min(t_ms, rs))
    return t_ms - removed


# --- 字幕: 重映射 → 切分 ≤24 字 → 剥结尾标点 ---
def clean(t):
    return t.rstrip(TRAIL_PUNCT)


def split_cap(text, t0, t1, high):
    if len(text) <= CAP_MAX:
        return [{"text": clean(text), "startMs": t0, "endMs": t1, "high": high}]
    parts, seg = [], ""
    for ch in text:
        seg += ch
        if len(seg) >= CAP_MAX - 6 and ch in SPLIT_PUNCT:
            parts.append(seg)
            seg = ""
        elif len(seg) >= CAP_MAX:
            parts.append(seg)
            seg = ""
    if seg:
        parts.append(seg)
    total = sum(len(p) for p in parts)
    out, acc = [], 0
    for p in parts:
        s = t0 + (t1 - t0) * acc / total
        acc += len(p)
        out.append({"text": clean(p), "startMs": s,
                    "endMs": t0 + (t1 - t0) * acc / total, "high": high})
    return out


caps = []
for c in props["captions"]:
    # props 时间轴是 TTS 原始速率，先乘 1/RATE 对齐到 atempo 后的音频，再裁停顿重映射
    t0 = remap(c["startMs"] / RATE) + LEAD_MS
    t1 = remap(c["endMs"] / RATE) + LEAD_MS
    caps.extend(split_cap(c["text"], t0, t1, c.get("high", False)))
video_ms = LEAD_MS + audio_ms + TAIL_MS

# --- 分页: storyboard beats 的 slide 变化处为边界 ---
bounds, slides_used = [], []
for b in beats:
    slide = b["slide"]
    if not slides_used or slides_used[-1] != slide:
        bounds.append(remap(props["cues"][b["id"]] / RATE) + LEAD_MS)
        slides_used.append(slide)
bounds.append(video_ms)
n = len(slides_used)
durs = [(bounds[i + 1] - bounds[i]) / 1000 for i in range(n)]
for i, s in enumerate(slides_used):
    p = SLIDES_DIR / f"slide-{s:02d}.png"
    if not p.is_file():
        sys.exit(f"缺少分页图: {p}")
print(f"分页 {n} 段: {slides_used}")


def ass_ts(ms):
    h = int(ms // 3600000)
    m = int(ms // 60000) % 60
    s = int(ms // 1000) % 60
    cs = int(ms % 1000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "",
       "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
       "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
       "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: Default,PingFang SC,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
       "-1,0,0,0,100,100,0,0,3,2,0,2,80,80,130,1",
       "Style: High,PingFang SC,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
       "-1,0,0,0,100,100,0,0,3,2,0,2,80,80,210,1", "",
       "[Events]",
       "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
for c in caps:
    style = "High" if c["high"] else "Default"
    ass.append(f"Dialogue: 0,{ass_ts(c['startMs'])},{ass_ts(c['endMs'])},{style},,0,0,0,,{c['text']}")
ass_path = RUN / "subtitles.ass"
ass_path.write_text("\n".join(ass))

inputs = []
for i, d in enumerate(durs):
    inputs += ["-loop", "1", "-framerate", "30", "-t", f"{d + FADE:.3f}",
               "-i", str(SLIDES_DIR / f"slide-{slides_used[i]:02d}.png")]
inputs += ["-i", str(voice_final)]

fc = [f"[{i}:v]scale=1920:1080,setsar=1,fps=30,format=yuv420p[s{i}]" for i in range(n)]
if n == 1:
    fc.append("[s0]null[vx]")
else:
    prev, offset = "s0", 0.0
    for i in range(1, n):
        offset += durs[i - 1] - (FADE if i > 1 else 0)
        nxt = f"x{i}" if i < n - 1 else "vx"
        fc.append(f"[{prev}][s{i}]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[{nxt}]")
        prev = nxt
fc.append(f"[vx]subtitles='{ass_path}':fontsdir=/System/Library/Fonts[vout]")
fc.append(f"[{n}:a]adelay={LEAD_MS}|{LEAD_MS},apad[aout]")

sh(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc),
    "-map", "[vout]", "-map", "[aout]",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-t", f"{video_ms / 1000:.3f}", str(OUT)])
print(f"OK -> {OUT}  {video_ms / 1000:.1f}s")
