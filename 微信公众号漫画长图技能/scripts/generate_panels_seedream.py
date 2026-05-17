#!/usr/bin/env python3
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DEFAULT_MODEL = "doubao-seedream-4-5-251128"
DEFAULT_ENV_FILES = (
    Path.cwd() / ".env",
)
STYLE_PROMPTS = {
    "风格一": (
        "WORDLESS IMAGE ONLY. standalone warm children's book style illustration, finished polished illustration quality, "
        "clean black ink linework, restrained warm colors, soft white or pastel background, "
        "clear central subject, gentle expressive characters, anatomically coherent complete human figures, one head per person, "
        "clear face neck torso arms hands legs feet, natural joints, natural posture, correct scale relationships, "
        "emotionally readable expressions, simple uncluttered mobile-readable composition, purely visual illustration, "
        "the image must contain zero writing, zero typography, zero symbols, zero readable marks, "
        "no Chinese characters, no English letters, no numbers, no captions, no speech bubbles, no comic sound effects, "
        "no title text, no handwriting, no labels, no poster text, no UI text, "
        "all screens, books, clocks, papers, signs, whiteboards, posters, product surfaces, walls, backgrounds must be blank or abstract, "
        "no watermark, no logo, "
        "no rough storyboard, no messy pencil draft, no dirty gray shading, no distorted faces, no duplicate heads, "
        "no floating facial parts, no detached hair, no extra limbs, no missing limbs, no fused bodies, no broken hands, "
        "no backward joints, no stick figures, no bean bodies, no blob people, no pictogram icons"
    ),
    "风格二": (
        "WORDLESS IMAGE ONLY. soft psychological WeChat longform comic illustration panel, portrait-oriented scene, "
        "clean but not glossy hand-drawn manga line art, slightly thicker black outlines, simple elegant facial features, restrained adult proportions, "
        "flat warm colors with light watercolor wash, white glow fade at top and bottom edges, airy white-space friendly composition, "
        "when the scene needs people, use these character types: a calm young adult Chinese female psychological consultant with straight black shoulder-length hair, mustard cardigan or light blazer over cream turtleneck; "
        "or a young adult Chinese female client with long black hair, white shirt and muted green vest or green dress. "
        "For metaphor scenes, simple faceless cream-colored mascot figures, paths, flowers, phones, cups, windows, and symbolic objects are allowed; do not force the recurring women into every metaphor panel. "
        "warm sunlight, cozy counseling room, yellow sofa, plants, books, desk, bed, cup, vase, bright window, gentle outdoor metaphors, "
        "soft golden-beige palette, quiet relationship-healing mood, emotional but restrained expressions, finished public-account comic quality, "
        "the generated image must contain zero written language and zero typography; all blue narration bars and all article text will be added later by the layout script, never draw them inside the panel; "
        "no glossy high-detail anime rendering, no cinematic photorealism, no over-rendered skin, no childlike cute style, no harsh contrast, no grim manga, no rough sketch, no dirty gray shading, no logo, no watermark, "
        "no Chinese characters, no English letters, no numbers, no captions, no labels, no UI text, no blue text bars, no colored text strips, no speech-bubble text; "
        "speech bubbles or thought bubbles may appear only when requested, and their interiors must remain blank unless final rendered text is explicitly required"
    ),
    "风格三": (
        "参考目标是微信公众号长截图风格的中文职场对比漫画小图：粗黑手绘线条，线条略有抖动和手工感，平涂色块叠加轻微纸纹颗粒，"
        "不是精致日漫，不是写实插画。画面要像手机长图里的成稿漫画，人物比例简化但完整，五官朴素夸张，表情直接可读。"
        "常用配色为草绿色、天空蓝、芥末黄、暖棕、橙色、灰紫和米白，饱和但不荧光，整体适合放在绿色纹理文章背景上。"
        "场景以现代中国职场为主：开放办公室、工位、电脑、键盘、文件、咖啡杯、工牌、会议室、夜晚窗景、夕阳窗景、茶水间、楼道。"
        "主角保持为年轻中国女性员工，浅棕色中长发或齐肩发，圆脸，白色皮肤底色，绿色背心或绿色上衣，可搭配白色条纹袖、棕色外套、蓝色长裤和工牌。"
        "构图为竖向公众号漫画分镜，前景人物大、动作明确，背景细节丰富但不抢戏。面板顶部要有黑色圆角标题条时，标题条里的文字必须来自场景提示中的引号。"
        "所有需要出现在图里的中文，包括标题、对白、旁白、手机消息、时间戳、拟声词和强调词，都必须由即梦直接画在图里。"
        "引号里的中文文字优先级最高，必须逐字照抄，不要改写、缩短、替换同义词或漏字；长句自动分行但保持原文顺序。"
        "只渲染场景提示里用引号包住的文字，必须清晰、粗黑或白字黑描边，放进对应的对白气泡、标题条、聊天框或画面指定位置。"
        "不要自己编任何额外文字；没有被引号包住的词语一律只当作画面说明，不要写进图里。"
        "对白气泡要白底黑边，尾巴指向说话人；聊天框要像参考图里的白色矩形消息框；标题条要黑底白字。文字要大而清楚，适合手机阅读。"
        "人物是成年职场人，不要儿童化萌系，不要过度圆润可爱；保留参考图那种粗糙手绘公众号漫画感，黑线更粗，阴影更少，颗粒更明显。"
        "不要英文，不要拼音，不要随机标签，不要无意义乱码，不要界面小字，不要海报墙字，不要水印，不要logo或署名。"
        "不要绿色发光边框，不要内置外框，不要过度光滑的动漫脸，不要电影写实，不要厚涂，不要水彩柔边，不要3D感，不要草稿低清，不要畸形肢体，不要多头，不要坏手。"
    ),
}
QUOTE_TRANSLATION = str.maketrans({
    '"': "",
    "'": "",
    "“": "",
    "”": "",
    "‘": "",
    "’": "",
    "「": "",
    "」": "",
    "『": "",
    "』": "",
})
BILLING_ERROR_CODES = {
    "AccountOverdueError",
    "InsufficientBalance",
    "BalanceNotEnough",
    "QuotaNotEnough",
    "ResourceExhausted",
}
BILLING_ERROR_KEYWORDS = (
    "overdue",
    "insufficient balance",
    "balance",
    "quota",
    "欠费",
    "余额不足",
    "额度不足",
    "账户余额",
)


def parse_env_value(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_env_file(path, *, override=False):
    if not path.exists() or not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = parse_env_value(value)
        if not value:
            continue
        if override or key not in os.environ:
            os.environ[key] = value


def load_default_env_files():
    for path in DEFAULT_ENV_FILES:
        load_env_file(path)


def resolve_api_key(primary_env):
    candidates = [primary_env]
    for env_name in ("DOUBAO_API_KEY", "ARK_API_KEY"):
        if env_name not in candidates:
            candidates.append(env_name)
    for env_name in candidates:
        value = os.environ.get(env_name)
        if value:
            return value, env_name
    return None, ""


def load_prompts(path):
    raw = Path(path).read_text(encoding="utf-8")
    if path.endswith(".json"):
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(item) if not isinstance(item, dict) else item.get("prompt", "") for item in data]
        if isinstance(data, dict):
            prompts = data.get("prompts", [])
            return [str(item) if not isinstance(item, dict) else item.get("prompt", "") for item in prompts]
        raise ValueError("JSON prompts file must be a list or an object with a prompts list")
    return [line.strip() for line in raw.splitlines() if line.strip()]


def sanitize_prompt(prompt, preserve_quotes=False):
    if preserve_quotes:
        return prompt.strip()
    return prompt.translate(QUOTE_TRANSLATION).strip()


def build_full_prompt(style, prompt, style_prompt):
    if style == "风格三":
        return (
            "生成一张完整的中文职场公众号漫画小图，图中所有标题、对白、旁白、手机消息和拟声词都由你直接渲染。"
            "只有场景提示中被引号包住的文字可以写进画面，必须放在对应气泡、标题条、聊天框或指定位置；"
            "不要添加任何未被引号包住的额外文字，不要英文，不要乱码。\n\n"
            f"场景：{prompt}\n\n风格和限制：{style_prompt}"
        )
    return (
        "Create a wordless illustration only. Do not render any text, characters, letters, numbers, captions, labels, "
        "speech bubbles, title text, poster text, screen text, or watermark anywhere in the image. "
        "If an object could normally contain writing, leave it completely blank.\n\n"
        f"Scene: {prompt}\n\nStyle and constraints: {style_prompt}"
    )


def parse_api_error(detail):
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return "", detail.strip()

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        code = str(error.get("code") or "")
        message = str(error.get("message") or detail).strip()
        return code, message
    return "", detail.strip()


def is_billing_error(code, message):
    text = f"{code} {message}".lower()
    return code in BILLING_ERROR_CODES or any(keyword.lower() in text for keyword in BILLING_ERROR_KEYWORDS)


def build_failure_guidance(code, message):
    if is_billing_error(code, message):
        return (
            "\n\n生成已停止：当前火山方舟/豆包账号无法继续调用 Seedream/即梦图片模型。"
            "\n检测到的原因：账号欠费、余额不足或可用额度不足。"
            "\n处理方式："
            "\n1. 登录与当前 API Key 对应的火山引擎账号。"
            "\n2. 打开费用中心充值页：https://console.volcengine.com/finance/fund/recharge"
            "\n3. 给该账号充值，或先结清待支付/欠费账单；确认火山方舟/即梦模型调用账户有可用余额后再重试。"
            "\n4. 重新运行同一个 generate_panels_seedream.py 命令即可继续生成。"
            "\n\n不会自动改用本地矢量图、PIL 占位图或其他非 Seedream 图片生成方式，以免把 mockup 误当成最终效果。"
        )
    return (
        "\n\n生成已停止：Seedream/即梦 API 调用失败。"
        "\n请根据上面的错误码检查 API Key、模型开通状态、账户额度、网络或请求参数后再重试。"
        "\n不会自动改用本地矢量图或占位图生成最终长图。"
    )


def request_image(api_url, api_key, model, prompt, size, response_format, timeout, watermark):
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "response_format": response_format,
        "stream": False,
        "watermark": watermark,
        "sequential_image_generation": "disabled",
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        error_code, message = parse_api_error(detail)
        guidance = build_failure_guidance(error_code, message)
        label = f"{error_code}: {message}" if error_code else detail
        raise RuntimeError(f"Seedream API error {exc.code}: {label}{guidance}") from exc


def save_image(item, out_path, timeout):
    if item.get("b64_json"):
        out_path.write_bytes(base64.b64decode(item["b64_json"]))
        return
    if item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=timeout) as response:
            out_path.write_bytes(response.read())
        return
    raise RuntimeError(f"No image payload in response item: {item.keys()}")


def main():
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--env-file", default="", help="Load an extra .env file; overrides current directory .env")
    pre_args, _ = pre_parser.parse_known_args()

    load_default_env_files()
    if pre_args.env_file:
        load_env_file(Path(pre_args.env_file).expanduser(), override=True)

    parser = argparse.ArgumentParser(
        description="Generate WeChat comic panel images with Volcengine Ark Seedream.",
        parents=[pre_parser],
    )
    parser.add_argument("--prompts", required=True, help="JSON or text file containing panel prompts")
    parser.add_argument("--out-dir", required=True, help="Output directory for panel PNG files")
    parser.add_argument("--style", default="风格一", choices=sorted(STYLE_PROMPTS), help="Style prompt to append")
    parser.add_argument("--model", default=os.environ.get("ARK_IMAGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--api-url", default=os.environ.get("ARK_API_URL", DEFAULT_API_URL))
    parser.add_argument("--api-key-env", default="DOUBAO_API_KEY", help="Environment variable containing Ark/Doubao API key")
    parser.add_argument("--size", default="2304x1728", help="Seedream output size, for example 2304x1728, 1536x2560, or 2K")
    parser.add_argument("--response-format", default="b64_json", choices=["b64_json", "url"])
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to wait between requests")
    parser.add_argument("--watermark", action="store_true", help="Ask API to add watermark")
    args = parser.parse_args()

    api_key, api_key_env = resolve_api_key(args.api_key_env)
    if not api_key:
        env_names = []
        for name in (args.api_key_env, "DOUBAO_API_KEY", "ARK_API_KEY"):
            if name not in env_names:
                env_names.append(name)
        print(
            f"Missing API key. Export one of: {', '.join(env_names)}; "
            "put it in the current directory .env; or pass --env-file /path/to/.env",
            file=sys.stderr,
        )
        return 2

    prompts = [prompt for prompt in load_prompts(args.prompts) if prompt.strip()]
    if not prompts:
        print("No prompts found.", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    style_prompt = STYLE_PROMPTS[args.style]
    manifest = {
        "api_url": args.api_url,
        "model": args.model,
        "style": args.style,
        "size": args.size,
        "response_format": args.response_format,
        "watermark": args.watermark,
        "api_key_env": api_key_env,
        "panels": [],
    }

    for index, prompt in enumerate(prompts, start=1):
        clean_prompt = sanitize_prompt(prompt, preserve_quotes=args.style == "风格三")
        full_prompt = build_full_prompt(args.style, clean_prompt, style_prompt)
        out_path = out_dir / f"panel-{index:02d}.png"
        print(f"[{index}/{len(prompts)}] generating {out_path}", flush=True)
        try:
            response = request_image(
                args.api_url,
                api_key,
                args.model,
                full_prompt,
                args.size,
                args.response_format,
                args.timeout,
                args.watermark,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        data = response.get("data") or []
        if not data:
            raise RuntimeError(f"No image data returned for panel {index}: {response}")
        save_image(data[0], out_path, args.timeout)
        manifest["panels"].append({"file": out_path.name, "prompt": clean_prompt})
        if args.sleep and index < len(prompts):
            time.sleep(args.sleep)

    (out_dir / "seedream-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(prompts)} panels to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
