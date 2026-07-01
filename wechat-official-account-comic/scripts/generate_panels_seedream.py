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


DEFAULT_PROVIDER = "agnes"
DEFAULT_AGNES_API_URL = "https://apihub.agnes-ai.com/v1/images/generations"
DEFAULT_AGNES_MODEL = "agnes-image-2.0-flash"
DEFAULT_AGNES_SIZE = "1024x768"
DEFAULT_SEEDREAM_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DEFAULT_SEEDREAM_MODEL = "doubao-seedream-4-5-251128"
DEFAULT_SEEDREAM_SIZE = "2304x1728"
DEFAULT_API_URL = DEFAULT_SEEDREAM_API_URL
DEFAULT_MODEL = DEFAULT_SEEDREAM_MODEL
DEFAULT_ENV_FILES = (
    Path.cwd() / ".env",
)
DEFAULT_STYLES_DIR = Path(__file__).resolve().parents[1] / "styles"
MODEL_RENDERED_TEXT_POLICIES = {"model-rendered", "quoted-text", "in-panel-text"}
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
    "credit",
    "credits",
    "token plan",
    "欠费",
    "余额不足",
    "额度不足",
    "账户余额",
)
PROVIDER_ALIASES = {
    "agnes": "agnes",
    "agnes-ai": "agnes",
    "gnes": "agnes",
    "seedream": "seedream",
    "doubao": "seedream",
    "ark": "seedream",
    "volcengine": "seedream",
    "volcengine-ark": "seedream",
}


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


def normalize_provider(provider):
    normalized = str(provider or DEFAULT_PROVIDER).strip().lower().replace("_", "-")
    provider_name = PROVIDER_ALIASES.get(normalized)
    if not provider_name:
        supported = ", ".join(sorted(PROVIDER_ALIASES))
        raise ValueError(f"Unknown image provider: {provider}. Use one of: {supported}")
    return provider_name


def unique_names(names):
    seen = set()
    result = []
    for name in names:
        name = str(name or "").strip()
        if name and name not in seen:
            result.append(name)
            seen.add(name)
    return result


def resolve_provider_config(provider, model="", api_url="", api_key_env=""):
    provider_name = normalize_provider(provider or os.environ.get("COMIC_IMAGE_PROVIDER") or DEFAULT_PROVIDER)
    if provider_name == "agnes":
        return {
            "provider": "agnes",
            "label": "Agnes Image 2.0 Flash",
            "api_url": api_url or os.environ.get("AGNES_API_URL") or DEFAULT_AGNES_API_URL,
            "model": model or os.environ.get("AGNES_IMAGE_MODEL") or DEFAULT_AGNES_MODEL,
            "api_key_envs": unique_names([api_key_env, "AGNES_API_KEY", "GNES_API_KEY", "AGNESAI_API_KEY"]),
            "default_size": DEFAULT_AGNES_SIZE,
        }
    if provider_name == "seedream":
        return {
            "provider": "seedream",
            "label": "Volcengine Ark/Doubao Seedream",
            "api_url": api_url or os.environ.get("ARK_API_URL") or DEFAULT_SEEDREAM_API_URL,
            "model": model or os.environ.get("ARK_IMAGE_MODEL") or DEFAULT_SEEDREAM_MODEL,
            "api_key_envs": unique_names([api_key_env, "DOUBAO_API_KEY", "ARK_API_KEY"]),
            "default_size": DEFAULT_SEEDREAM_SIZE,
        }
    raise ValueError(f"Unsupported image provider: {provider}")


def resolve_api_key(env_names):
    if isinstance(env_names, str):
        candidates = unique_names([env_names, "DOUBAO_API_KEY", "ARK_API_KEY"])
    else:
        candidates = unique_names(env_names)
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


def load_style_profile(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Style profile not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Style profile is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Style profile must be a JSON object: {path}")
    style_prompt = data.get("style_prompt") or data.get("prompt")
    if not style_prompt:
        raise ValueError(f"Style profile must include style_prompt or prompt: {path}")
    text_policy = str(data.get("text_policy") or "wordless").strip() or "wordless"
    name = str(data.get("name") or data.get("style") or path.stem).strip() or path.stem
    aliases = data.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    return {
        "name": name,
        "aliases": [str(alias).strip() for alias in aliases if str(alias).strip()],
        "style_prompt": str(style_prompt).strip(),
        "text_policy": text_policy,
        "default": bool(data.get("default", False)),
        "source": str(path),
    }


def iter_style_profiles(styles_dir):
    styles_dir = Path(styles_dir).expanduser()
    if not styles_dir.exists():
        return
    for path in sorted(p for p in styles_dir.glob("*.json") if p.is_file()):
        try:
            yield path, load_style_profile(path)
        except ValueError:
            continue


def resolve_default_style_profile(styles_dir):
    defaults = []
    for path, profile in iter_style_profiles(styles_dir):
        if profile.get("default"):
            defaults.append((path, profile))
    if not defaults:
        raise ValueError(
            f"No default style profile found in {Path(styles_dir).expanduser()}. "
            'Mark exactly one profile with "default": true, pass --style, or pass --style-profile.'
        )
    if len(defaults) > 1:
        names = ", ".join(str(path.name) for path, _ in defaults)
        raise ValueError(f"Multiple default style profiles found: {names}. Mark exactly one profile as default.")
    return defaults[0][1]


def resolve_style_settings(style, style_profile, styles_dir):
    if style_profile:
        profile = load_style_profile(Path(style_profile).expanduser())
        return profile["name"], profile["style_prompt"], profile["text_policy"], profile["source"]

    styles_dir = Path(styles_dir).expanduser()
    style = str(style or "").strip()
    if not style:
        profile = resolve_default_style_profile(styles_dir)
        return profile["name"], profile["style_prompt"], profile["text_policy"], profile["source"]

    candidate = styles_dir / f"{style}.json"
    if candidate.exists():
        profile = load_style_profile(candidate)
        return profile["name"], profile["style_prompt"], profile["text_policy"], profile["source"]

    available_styles = []
    for path, profile in iter_style_profiles(styles_dir):
        available_styles.append(path.stem)
        aliases = set(profile.get("aliases", []))
        aliases.add(profile["name"])
        if style in aliases:
            return profile["name"], profile["style_prompt"], profile["text_policy"], profile["source"]
    available = available_styles
    raise ValueError(
        f"Unknown style: {style}. Use one of: {', '.join(available)}; "
        "or pass --style-profile /path/to/style.json"
    )


def uses_model_rendered_text(text_policy):
    normalized = str(text_policy or "").strip().lower().replace("_", "-")
    return normalized in MODEL_RENDERED_TEXT_POLICIES


def sanitize_prompt(prompt, preserve_quotes=False):
    if preserve_quotes:
        return prompt.strip()
    return prompt.translate(QUOTE_TRANSLATION).strip()


def build_full_prompt(style, prompt, style_prompt, text_policy="wordless"):
    if uses_model_rendered_text(text_policy):
        intro = (
            "根据风格 profile 生成一张完整的中文公众号漫画图。"
            "图中需要出现的标题、对白、旁白、标签、消息、拟声词或手写 caption 都由图像模型直接渲染。"
            "只有场景提示中被引号包住的文字可以写进画面；必须遵循 profile 里的构图、文字位置和字形规则。"
            "不要添加任何未被引号包住的额外文字，不要英文，不要乱码。"
        )
        return (
            f"{intro}\n\n"
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


def build_failure_guidance(code, message, provider):
    provider_name = normalize_provider(provider)
    if provider_name == "seedream" and is_billing_error(code, message):
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
    if provider_name == "agnes" and is_billing_error(code, message):
        return (
            "\n\n生成已停止：当前 Agnes 账号无法继续调用 Agnes Image 图片模型。"
            "\n检测到的原因可能是 API Key 对应账号额度、订阅或 Token Plan 不可用。"
            "\n处理方式："
            "\n1. 登录与当前 API Key 对应的 Agnes 账号：https://platform.agnes-ai.com/"
            "\n2. 打开「账户 / 订阅 / Token Plan」或 API 密钥页面，确认账号状态和可用额度。"
            "\n3. 修复账号额度或重新创建有效 API Key 后，再运行同一个生成命令。"
            "\n\n不会自动改用本地矢量图、PIL 占位图或其他 provider，以免把 mockup 误当成最终效果。"
        )
    if provider_name == "agnes":
        return (
            "\n\n生成已停止：Agnes Image API 调用失败。"
            "\n请检查 AGNES_API_KEY/GNES_API_KEY、账号状态、网络、模型名、图片尺寸或请求参数后再重试。"
            "\n不会自动改用本地矢量图、占位图或其他 provider 生成最终长图。"
        )
    return (
        "\n\n生成已停止：Seedream/即梦 API 调用失败。"
        "\n请根据上面的错误码检查 API Key、模型开通状态、账户额度、网络或请求参数后再重试。"
        "\n不会自动改用本地矢量图或占位图生成最终长图。"
    )


def build_api_payload(provider, model, prompt, size, response_format, watermark):
    provider_name = normalize_provider(provider)
    if provider_name == "agnes":
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
        }
        extra_body = {}
        if response_format == "b64_json":
            payload["return_base64"] = True
            extra_body["response_format"] = "b64_json"
        elif response_format == "url":
            extra_body["response_format"] = "url"
        if extra_body:
            payload["extra_body"] = extra_body
        return payload
    if provider_name == "seedream":
        return {
            "model": model,
            "prompt": prompt,
            "size": size,
            "response_format": response_format,
            "stream": False,
            "watermark": watermark,
            "sequential_image_generation": "disabled",
        }
    raise ValueError(f"Unsupported image provider: {provider}")


def request_image(provider, api_url, api_key, model, prompt, size, response_format, timeout, watermark):
    provider_name = normalize_provider(provider)
    payload = build_api_payload(provider_name, model, prompt, size, response_format, watermark)
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
        guidance = build_failure_guidance(error_code, message, provider_name)
        label = f"{error_code}: {message}" if error_code else detail
        provider_label = "Agnes Image API" if provider_name == "agnes" else "Seedream API"
        raise RuntimeError(f"{provider_label} error {exc.code}: {label}{guidance}") from exc


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
        description="Generate WeChat comic panel images with Agnes Image (default) or Volcengine Ark Seedream.",
        parents=[pre_parser],
    )
    parser.add_argument("--provider", default=os.environ.get("COMIC_IMAGE_PROVIDER", DEFAULT_PROVIDER), help="Image provider: agnes/gnes (default) or seedream/doubao/ark")
    parser.add_argument("--prompts", required=True, help="JSON or text file containing panel prompts")
    parser.add_argument("--out-dir", required=True, help="Output directory for panel PNG files")
    parser.add_argument("--style", default="", help='Style name, alias, or JSON profile stem in --styles-dir; omit to use the profile marked "default": true')
    parser.add_argument("--style-profile", default="", help="Explicit JSON style profile to use")
    parser.add_argument("--styles-dir", default=str(DEFAULT_STYLES_DIR), help="Directory containing reusable JSON style profiles")
    parser.add_argument("--model", default="", help="Override provider default model")
    parser.add_argument("--api-url", default="", help="Override provider default API URL")
    parser.add_argument("--api-key-env", default="", help="Environment variable containing the selected provider API key")
    parser.add_argument("--size", default="", help="Output size. Agnes default: 1024x768. Seedream default: 2304x1728")
    parser.add_argument("--response-format", default="b64_json", choices=["b64_json", "url"])
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to wait between requests")
    parser.add_argument("--watermark", action="store_true", help="Ask Seedream API to add watermark; ignored by Agnes")
    args = parser.parse_args()

    try:
        provider_config = resolve_provider_config(args.provider, args.model, args.api_url, args.api_key_env)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    args.size = args.size or provider_config["default_size"]

    api_key, api_key_env = resolve_api_key(provider_config["api_key_envs"])
    if not api_key:
        print(
            f"Missing API key for {provider_config['label']}. Export one of: {', '.join(provider_config['api_key_envs'])}; "
            "put it in the current directory .env; or pass --env-file /path/to/.env",
            file=sys.stderr,
        )
        return 2

    prompts = [prompt for prompt in load_prompts(args.prompts) if prompt.strip()]
    if not prompts:
        print("No prompts found.", file=sys.stderr)
        return 2

    try:
        style_name, style_prompt, text_policy, style_source = resolve_style_settings(
            args.style,
            args.style_profile,
            args.styles_dir,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "provider": provider_config["provider"],
        "provider_label": provider_config["label"],
        "api_url": provider_config["api_url"],
        "model": provider_config["model"],
        "style": style_name,
        "requested_style": args.style,
        "style_source": style_source,
        "text_policy": text_policy,
        "size": args.size,
        "response_format": args.response_format,
        "watermark": args.watermark,
        "api_key_env": api_key_env,
        "panels": [],
    }

    for index, prompt in enumerate(prompts, start=1):
        render_text_in_model = uses_model_rendered_text(text_policy)
        clean_prompt = sanitize_prompt(prompt, preserve_quotes=render_text_in_model)
        full_prompt = build_full_prompt(style_name, clean_prompt, style_prompt, text_policy)
        out_path = out_dir / f"panel-{index:02d}.png"
        print(f"[{index}/{len(prompts)}] generating {out_path}", flush=True)
        try:
            response = request_image(
                provider_config["provider"],
                provider_config["api_url"],
                api_key,
                provider_config["model"],
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

    manifest_name = f"{provider_config['provider']}-manifest.json"
    (out_dir / manifest_name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(prompts)} panels to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
