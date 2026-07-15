#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


DEFAULT_PROVIDER = "agnes"
DEFAULT_AGNES_API_URL = "https://apihub.agnes-ai.com/v1/images/generations"
DEFAULT_AGNES_MODEL = "agnes-image-2.0-flash"
DEFAULT_AGNES_SIZE = "1024x768"
DEFAULT_SEEDREAM_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DEFAULT_SEEDREAM_MODEL = "doubao-seedream-4-5-251128"
DEFAULT_SEEDREAM_SIZE = "2304x1728"
DEFAULT_BREAKOUT_API_URL = "https://breakout.wenwen-ai.com/v1/images/generations"
DEFAULT_BREAKOUT_EDIT_API_URL = "https://breakout.wenwen-ai.com/v1/images/edits"
DEFAULT_BREAKOUT_MODEL = "gpt-image-2"
DEFAULT_BREAKOUT_SIZE = "1536x1024"
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
    "breakout": "breakout",
    "wenwen": "breakout",
    "breakoutapi": "breakout",
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
    if provider_name == "breakout":
        return {
            "provider": "breakout",
            "label": "Breakout API GPT Image",
            "api_url": api_url or os.environ.get("BREAKOUT_API_URL") or DEFAULT_BREAKOUT_API_URL,
            "edit_api_url": os.environ.get("BREAKOUT_EDIT_API_URL") or DEFAULT_BREAKOUT_EDIT_API_URL,
            "model": model or os.environ.get("BREAKOUT_IMAGE_MODEL") or DEFAULT_BREAKOUT_MODEL,
            "api_key_envs": unique_names([api_key_env, "BREAKOUT_API_KEY"]),
            "default_size": DEFAULT_BREAKOUT_SIZE,
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


def build_image_edit_prompt(prompt, text_policy="wordless"):
    """Build a compact prompt for reference-image editing.

    Reference images already carry the visual style and can contain article text.
    Do not reuse the text-to-image wrapper here: its wordless requirement would
    contradict a request to preserve an existing cover or caption.
    """
    if uses_model_rendered_text(text_policy):
        text_instruction = (
            "Preserve readable text already present in the primary reference image unless "
            "the edit request explicitly changes it. Do not add unrelated text."
        )
    else:
        text_instruction = (
            "Preserve readable text already present in the primary reference image when the "
            "edit request calls for it. Do not add unrelated text, logos, or watermarks."
        )
    return (
        "Use the supplied reference images as the source of identity, composition, and visual style. "
        "Create one polished final image that follows this edit request. "
        f"{text_instruction}\n\nEdit request: {prompt}"
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
    if provider_name == "breakout":
        return (
            "\n\n生成已停止：Breakout API 图片调用失败。"
            "\n请检查 BREAKOUT_API_KEY、模型可用性、账户余额、图片字段或服务端请求 ID 后再重试。"
            "\n图生图使用 multipart/form-data；每张参考图都必须作为同名 image 文件字段上传。"
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
    if provider_name == "breakout":
        return {
            "model": model,
            "prompt": prompt,
            "size": size,
        }
    raise ValueError(f"Unsupported image provider: {provider}")


def encode_multipart_form(fields, file_field, file_paths):
    boundary = f"----wechatComic{uuid.uuid4().hex}"
    body = bytearray()

    def add_text(name, value):
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for name, value in fields.items():
        if value is not None and value != "":
            add_text(name, value)

    for raw_path in file_paths:
        path = Path(raw_path).expanduser()
        if not path.is_file():
            raise ValueError(f"Reference image not found: {path}")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{file_field}"; filename="{path.name}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(path.read_bytes())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def provider_label(provider):
    provider_name = normalize_provider(provider)
    if provider_name == "agnes":
        return "Agnes Image API"
    if provider_name == "seedream":
        return "Seedream API"
    if provider_name == "breakout":
        return "Breakout API"
    return "Image API"


RETRYABLE_HTTP_STATUS_CODES = {429, 502, 503, 504}


class ImageRequestError(RuntimeError):
    def __init__(self, message, status_code=None, request_id=""):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id

    @property
    def retryable(self):
        return self.status_code in RETRYABLE_HTTP_STATUS_CODES


def get_request_id(headers):
    if not headers:
        return ""
    for name in ("x-request-id", "x-oneapi-request-id", "request-id"):
        value = headers.get(name)
        if value:
            return str(value)
    return ""


def request_image(
    provider,
    api_url,
    api_key,
    model,
    prompt,
    size,
    response_format,
    timeout,
    watermark,
    reference_images=(),
    quality="auto",
    edit_api_url="",
):
    provider_name = normalize_provider(provider)
    if provider_name == "breakout" and reference_images:
        body, content_type = encode_multipart_form(
            {"model": model, "prompt": prompt, "quality": quality},
            "image",
            reference_images,
        )
        request_url = edit_api_url or DEFAULT_BREAKOUT_EDIT_API_URL
    else:
        payload = build_api_payload(provider_name, model, prompt, size, response_format, watermark)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        content_type = "application/json"
        request_url = api_url
    request = urllib.request.Request(
        request_url,
        data=body,
        headers={
            "Content-Type": content_type,
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
        request_id = get_request_id(exc.headers)
        request_id_detail = f"\nServer request ID: {request_id}" if request_id else ""
        raise ImageRequestError(
            f"{provider_label(provider_name)} error {exc.code}: {label}{request_id_detail}{guidance}",
            status_code=exc.code,
            request_id=request_id,
        ) from exc


def request_image_with_retries(*args, retries=0, retry_delay=30.0, **kwargs):
    """Retry only explicitly requested transient HTTP failures.

    A gateway timeout can occur after the upstream service started work, so the
    CLI defaults to zero retries to avoid an unrequested duplicate generation.
    """
    for attempt in range(retries + 1):
        try:
            return request_image(*args, **kwargs)
        except ImageRequestError as exc:
            if not exc.retryable or attempt >= retries:
                raise
            print(
                f"Transient HTTP {exc.status_code}; retrying in {retry_delay:g}s "
                f"({attempt + 1}/{retries}).",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(retry_delay)


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
        description="Generate WeChat comic panel images with Agnes Image (default), Volcengine Ark Seedream, or Breakout API.",
        parents=[pre_parser],
    )
    parser.add_argument("--provider", default=os.environ.get("COMIC_IMAGE_PROVIDER", DEFAULT_PROVIDER), help="Image provider: agnes/gnes (default), seedream/doubao/ark, or breakout/wenwen")
    parser.add_argument("--prompts", required=True, help="JSON or text file containing panel prompts")
    parser.add_argument("--out-dir", required=True, help="Output directory for panel PNG files")
    parser.add_argument("--style", default="", help='Style name, alias, or JSON profile stem in --styles-dir; omit to use the profile marked "default": true')
    parser.add_argument("--style-profile", default="", help="Explicit JSON style profile to use")
    parser.add_argument("--styles-dir", default=str(DEFAULT_STYLES_DIR), help="Directory containing reusable JSON style profiles")
    parser.add_argument("--model", default="", help="Override provider default model")
    parser.add_argument("--api-url", default="", help="Override provider default API URL")
    parser.add_argument("--api-key-env", default="", help="Environment variable containing the selected provider API key")
    parser.add_argument("--size", default="", help="Output size. Agnes default: 1024x768. Seedream default: 2304x1728. Breakout default: 1536x1024")
    parser.add_argument("--response-format", default="b64_json", choices=["b64_json", "url"])
    parser.add_argument("--reference-image", action="append", default=[], help="Reference image for Breakout image edits; repeat this option to upload multiple images as the image field")
    parser.add_argument("--quality", default="auto", choices=["auto", "low", "medium", "high"], help="Breakout image-edit quality; ignored by other providers")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--retries", type=int, default=0, choices=range(0, 4), help="Explicit retries for HTTP 429/502/503/504; default: 0 to avoid duplicate billed generations")
    parser.add_argument("--retry-delay", type=float, default=30.0, help="Seconds to wait before an explicit retry (default: 30)")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to wait between requests")
    parser.add_argument("--watermark", action="store_true", help="Ask Seedream API to add watermark; ignored by Agnes")
    args = parser.parse_args()

    try:
        provider_config = resolve_provider_config(args.provider, args.model, args.api_url, args.api_key_env)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.reference_image and provider_config["provider"] != "breakout":
        print("--reference-image is only supported with --provider breakout.", file=sys.stderr)
        return 2
    for raw_path in args.reference_image:
        path = Path(raw_path).expanduser()
        if not path.is_file():
            print(f"Reference image not found: {path}", file=sys.stderr)
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
        "api_url": (
            provider_config.get("edit_api_url", DEFAULT_BREAKOUT_EDIT_API_URL)
            if args.reference_image
            else provider_config["api_url"]
        ),
        "model": provider_config["model"],
        "style": style_name,
        "requested_style": args.style,
        "style_source": style_source,
        "text_policy": text_policy,
        "size": args.size,
        "response_format": args.response_format,
        "watermark": args.watermark,
        "api_key_env": api_key_env,
        "generation_mode": "image-edit" if args.reference_image else "text-to-image",
        "reference_images": [str(Path(path).expanduser()) for path in args.reference_image],
        "quality": args.quality if args.reference_image else "",
        "retries": args.retries,
        "retry_delay": args.retry_delay if args.retries else 0,
        "panels": [],
    }

    for index, prompt in enumerate(prompts, start=1):
        render_text_in_model = uses_model_rendered_text(text_policy)
        clean_prompt = sanitize_prompt(prompt, preserve_quotes=render_text_in_model)
        if args.reference_image:
            full_prompt = build_image_edit_prompt(clean_prompt, text_policy)
        else:
            full_prompt = build_full_prompt(style_name, clean_prompt, style_prompt, text_policy)
        out_path = out_dir / f"panel-{index:02d}.png"
        print(f"[{index}/{len(prompts)}] generating {out_path}", flush=True)
        try:
            response = request_image_with_retries(
                provider_config["provider"],
                provider_config["api_url"],
                api_key,
                provider_config["model"],
                full_prompt,
                args.size,
                args.response_format,
                args.timeout,
                args.watermark,
                args.reference_image,
                args.quality,
                provider_config.get("edit_api_url", ""),
                retries=args.retries,
                retry_delay=args.retry_delay,
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
