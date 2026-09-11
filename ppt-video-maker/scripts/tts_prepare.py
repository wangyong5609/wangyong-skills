#!/usr/bin/env python3
"""口播分镜 → 腾讯云 TTS 配音 + 句级时间轴。

用法:
  python3 tts_prepare.py storyboard.json --out RUN_DIR

输入 storyboard.json:
  {"id": "run-id", "title": "...",
   "beats": [{"id": "b01", "text": "口播句子。", "slide": 1, "high": false}, ...]}
  - text 里数字必须先转成中文读法（"72%"→"百分之七十二"），否则 TTS 读法不可控
  - high: 该句所在 PPT 页底部有文字，字幕需抬高（见 make_video.py）

输出到 RUN_DIR:
  narration.mp3   完整配音（TTS 原始速率）
  props.json      {"captions": [{text,startMs,endMs,high}], "cues": {beatId: startMs}}
                  时间是 TTS 原始速率音频上的毫秒（atempo 缩放与片头留白由 make_video 处理）
  storyboard.json 原样拷贝，供 make_video 取分页信息

凭证: skill 根目录 .env（见 .env.example），或环境变量
  TENCENT_SECRET_ID / TENCENT_SECRET_KEY
  TTS_VOICE_ID（默认 501000 智斌）/ TTS_SPEED（默认 1.3）
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path
from uuid import uuid4

ENDPOINT = "https://tts.tencentcloudapi.com"
MAX_CHUNK_CHARS = 140          # 腾讯云单次上限附近，按句末标点切
SAMPLE_RATE = 16000

SKILL_DIR = Path(__file__).resolve().parent.parent


def fail(msg: str) -> None:
    print(f"错误: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_config() -> dict:
    cfg = {}
    env_file = SKILL_DIR / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    for k in ("TENCENT_SECRET_ID", "TENCENT_SECRET_KEY", "TTS_VOICE_ID", "TTS_SPEED"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    if not cfg.get("TENCENT_SECRET_ID") or not cfg.get("TENCENT_SECRET_KEY"):
        fail(f"缺少腾讯云凭证，请在 {env_file} 填入 TENCENT_SECRET_ID / TENCENT_SECRET_KEY（参考 .env.example）")
    cfg.setdefault("TTS_VOICE_ID", "501000")
    cfg.setdefault("TTS_SPEED", "1.3")
    return cfg


# ---------- 腾讯云 TC3 签名 + TextToVoice ----------

def tencent_speed(multiplier: float) -> float:
    """倍速 → 腾讯云 Speed 参数（[-2,6]，分段线性，与线上验证过的映射一致）"""
    anchors = ((0.5, -2.0), (0.8, -1.0), (1.0, 0.0), (1.2, 1.0), (1.5, 2.0), (2.0, 4.0))
    bounded = min(max(multiplier, anchors[0][0]), anchors[-1][0])
    for (lr, lv), (rr, rv) in pairwise(anchors):
        if bounded <= rr:
            return round(lv + (bounded - lr) / (rr - lr) * (rv - lv), 2)
    return anchors[-1][1]


def hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def text_to_voice(text: str, cfg: dict) -> tuple[bytes, list[dict]]:
    """返回 (mp3_bytes, subtitles)，subtitles 为 [{Text,BeginTime,EndTime}]"""
    payload = {
        "Text": text,
        "SessionId": str(uuid4()),
        "Volume": 0,
        "Speed": tencent_speed(float(cfg["TTS_SPEED"])),
        "ProjectId": 0,
        "ModelType": 1,
        "VoiceType": int(cfg["TTS_VOICE_ID"]),
        "PrimaryLanguage": 1,
        "SampleRate": SAMPLE_RATE,
        "Codec": "mp3",
        "EnableSubtitle": True,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    host = "tts.tencentcloudapi.com"
    content_type = "application/json; charset=utf-8"
    action = "TextToVoice"
    timestamp = int(datetime.now(timezone.utc).timestamp())
    signed_headers = "content-type;host;x-tc-action"
    canonical_headers = f"content-type:{content_type}\nhost:{host}\nx-tc-action:{action.lower()}\n"
    canonical_request = "\n".join(("POST", "/", "", canonical_headers, signed_headers,
                                   hashlib.sha256(body).hexdigest()))
    date = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
    scope = f"{date}/tts/tc3_request"
    string_to_sign = "\n".join(("TC3-HMAC-SHA256", str(timestamp), scope,
                                hashlib.sha256(canonical_request.encode()).hexdigest()))
    signing = hmac_sha256(hmac_sha256(hmac_sha256(f"TC3{cfg['TENCENT_SECRET_KEY']}".encode(), date), "tts"), "tc3_request")
    signature = hmac.new(signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
    authorization = (f"TC3-HMAC-SHA256 Credential={cfg['TENCENT_SECRET_ID']}/{scope}, "
                     f"SignedHeaders={signed_headers}, Signature={signature}")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Authorization": authorization, "Content-Type": content_type, "Host": host,
        "X-TC-Action": action, "X-TC-Timestamp": str(timestamp), "X-TC-Version": "2019-08-23",
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())["Response"]
    except urllib.error.HTTPError as e:
        fail(f"腾讯云请求失败 HTTP {e.code}: {e.read()[:500].decode(errors='replace')}")
    except urllib.error.URLError as e:
        fail(f"无法连接腾讯云语音服务: {e.reason}")
    if result.get("Error"):
        fail(f"腾讯云拒绝请求: {result['Error'].get('Code')} {result['Error'].get('Message')}")
    try:
        audio = base64.b64decode(result["Audio"], validate=True)
    except (KeyError, binascii.Error):
        fail("腾讯云返回了无法识别的音频")
    if not (audio.startswith(b"ID3") or (len(audio) >= 2 and audio[0] == 0xFF and audio[1] & 0xE0 == 0xE0)):
        fail("腾讯云没有返回有效 MP3")
    subs = result.get("Subtitles")
    if not isinstance(subs, list) or not subs:
        fail("该音色没有返回字幕时间轴（EnableSubtitle 无效），请确认音色支持时间戳")
    return audio, subs


# ---------- 文本切分 / 音频合并 ----------

def split_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks, remaining = [], text
    endings = "。！？!?；;\n"
    while len(remaining) > max_chars:
        minimum = max_chars // 2
        at = max((remaining.rfind(m, minimum, max_chars) for m in endings), default=-1)
        at = at + 1 if at >= minimum else max_chars
        chunks.append(remaining[:at])
        remaining = remaining[at:]
    if remaining:
        chunks.append(remaining)
    return chunks


def probe_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"ffprobe 无法读取时长: {path}")
    return float(json.loads(r.stdout)["format"]["duration"])


def concat_mp3(parts: list[bytes], out_path: Path) -> None:
    if len(parts) == 1:
        out_path.write_bytes(parts[0])
        return
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        lines = []
        for i, p in enumerate(parts):
            seg = td / f"seg-{i:03d}.mp3"
            seg.write_bytes(p)
            lines.append(f"file '{seg}'")
        lst = td / "list.txt"
        lst.write_text("\n".join(lines) + "\n")
        r = subprocess.run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "0",
                            "-i", str(lst), "-c:a", "libmp3lame", "-y", str(out_path)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"ffmpeg 合并语音失败: {r.stderr[-500:]}")


# ---------- 时间轴对齐 ----------

def content_text(s: str) -> str:
    return "".join(c.casefold() for c in unicodedata.normalize("NFKC", s) if c.isalnum())


def clean_spans(raw: list[dict]) -> list[dict]:
    """清洗腾讯云字级时间戳：去空白/零时长非标点，压掉 ≤250ms 重叠"""
    spans, prev_end = [], 0
    for item in raw:
        text, start, end = item.get("Text", ""), item.get("BeginTime", 0), item.get("EndTime", 0)
        if not text.strip():
            continue
        if end <= start:
            if not any(c.isalnum() for c in text):
                continue
            fail("腾讯云时间戳异常（内容零时长），请重试")
        if prev_end - start > 250:
            fail("腾讯云时间戳重叠过多，请重试")
        start = max(start, prev_end)
        if end <= start:
            continue
        spans.append({"text": text, "start_ms": start, "end_ms": end})
        prev_end = end
    return spans


def map_beats(beats: list[dict], spans: list[dict]) -> tuple[list[dict], dict]:
    """把每个 beat 对齐到 span 区间，返回 (captions, cues)。文本内容必须逐字对上。"""
    captions, cues = [], {}
    cursor = 0
    for beat in beats:
        target = content_text(beat["text"])
        if not target:
            fail(f"beat {beat['id']} 没有可读内容")
        matched, idxs = "", []
        while matched != target:
            if cursor >= len(spans):
                fail(f"beat {beat['id']} 边界对不上语音时间轴，检查 storyboard 文本与合成文本是否一致")
            candidate = matched + content_text(spans[cursor]["text"])
            if not target.startswith(candidate):
                fail(f"beat {beat['id']} 边界落在词语中间，检查该句文本")
            idxs.append(cursor)
            matched = candidate
            cursor += 1
        first, last = spans[idxs[0]], spans[idxs[-1]]
        captions.append({"text": beat["text"], "startMs": float(first["start_ms"]),
                         "endMs": float(last["end_ms"]), "high": bool(beat.get("high"))})
        cues[beat["id"]] = float(first["start_ms"])
    if cursor != len(spans):
        tail = [s for s in spans[cursor:] if content_text(s["text"])]
        if tail:
            fail(f"语音时间轴有未映射的尾部（{len(tail)} 个非标点 span），检查 storyboard 文本")
    return captions, cues


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    story = json.loads(Path(args.storyboard).read_text())
    beats = story["beats"]
    if not beats:
        fail("storyboard 没有 beats")
    narration = "".join(b["text"] for b in beats)
    cfg = load_config()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    chunks = split_chunks(narration)
    print(f"共 {len(narration)} 字，{len(chunks)} 段合成（音色 {cfg['TTS_VOICE_ID']}，速度 {cfg['TTS_SPEED']}x）")
    audios, all_spans, offset_ms = [], [], 0
    with tempfile.TemporaryDirectory() as td:
        for i, chunk in enumerate(chunks):
            audio, subs = text_to_voice(chunk, cfg)
            seg = Path(td) / f"seg-{i:03d}.mp3"
            seg.write_bytes(audio)
            all_spans.extend({"Text": s["Text"], "BeginTime": s["BeginTime"] + offset_ms,
                              "EndTime": s["EndTime"] + offset_ms} for s in subs)
            offset_ms += round(probe_duration(seg) * 1000)
            audios.append(audio)
            print(f"  段 {i + 1}/{len(chunks)} 完成（{len(chunk)} 字）")

    spans = clean_spans(all_spans)
    if content_text("".join(s["text"] for s in spans)) != content_text(narration):
        fail("语音时间轴与文案对不上，请重试；仍失败请检查文案中的特殊字符")

    mp3_path = out_dir / "narration.mp3"
    concat_mp3(audios, mp3_path)
    captions, cues = map_beats(beats, spans)

    (out_dir / "props.json").write_text(json.dumps(
        {"title": story.get("title", ""), "captions": captions, "cues": cues},
        ensure_ascii=False, indent=1))
    (out_dir / "storyboard.json").write_text(json.dumps(story, ensure_ascii=False, indent=1))
    (out_dir / "narration.txt").write_text(narration)
    print(f"OK -> {out_dir}  配音 {probe_duration(mp3_path):.1f}s，{len(captions)} 句")


if __name__ == "__main__":
    main()
