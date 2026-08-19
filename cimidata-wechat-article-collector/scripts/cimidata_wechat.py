#!/usr/bin/env python3
"""Cost-bounded client and local archive workflow for Cimidata WeChat APIs."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import getpass
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


API_BASE = "https://api.cimidata.com"
DEFAULT_OUTPUT_DIR = Path.cwd() / "output" / "cimidata-wechat"
COMMENT_MIN_LIKES = 10
COMMENT_LIMIT = 10
CONFIG_FILE_NAME = ".env"


@dataclass(frozen=True)
class Operation:
    name: str
    path: str
    price_yuan: float
    description: str
    min_interval_seconds: float = 0.0


OPERATIONS = {
    "account-search": Operation("account-search", "/api/v3/accounts/search", 0.10, "关键词搜索公众号"),
    "account-info": Operation("account-info", "/api/v2/accounts/detail", 0.04, "获取公众号基本信息"),
    "account-day": Operation("account-day", "/api/v2/articles/current", 0.04, "获取公众号当天发文"),
    "account-history": Operation("account-history", "/api/v2/articles/history", 0.05, "获取公众号历史文章"),
    "article-full": Operation("article-full", "/api/v2/articles/detail", 0.01, "获取完整文章 HTML"),
    "article-info": Operation("article-info", "/api/v2/articles/info", 0.02, "获取文章与所属账号信息", 0.5),
    "article-metrics": Operation("article-metrics", "/api/v2/articles/data2", 0.03, "获取完整互动指标", 3.0),
    "article-metrics-basic": Operation("article-metrics-basic", "/api/v2/articles/data", 0.02, "获取基础互动指标", 3.0),
    "article-comments": Operation("article-comments", "/api/v3/articles/comments", 0.03, "获取一级评论"),
    "article-search-db": Operation("article-search-db", "/api/v2/articles/search", 0.02, "数据库关键词搜文"),
    "article-search-wechat": Operation("article-search-wechat", "/api/v3/articles/search", 0.05, "微信搜一搜关键词搜文"),
    "wechat-hot": Operation("wechat-hot", "/api/v2/hot/articles", 0.10, "获取微信爆文"),
    "wechat-100k-hot": Operation("wechat-100k-hot", "/api/v2/10w/articles", 0.10, "获取 10w+ 爆文"),
}


class CimidataError(RuntimeError):
    """An API or local processing failure with credentials removed."""


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            os.environ[key] = value


def default_config_file() -> Path:
    """Keep credentials in the installed Skill root, independent of the Agent product."""
    skill_dir = Path(__file__).absolute().parent.parent
    return skill_dir / CONFIG_FILE_NAME


def config_file_for(args: argparse.Namespace) -> Path:
    configured = getattr(args, "config_file", "")
    if configured:
        return Path(configured).expanduser()
    env_file = getattr(args, "env_file", "")
    if env_file:
        return Path(env_file).expanduser()
    return default_config_file()


def write_credentials_file(path: Path, app_id: str, app_secret: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        f"CIMIDATA_APP_ID={app_id}\nCIMIDATA_APP_SECRET={app_secret}\n",
        encoding="utf-8",
    )
    if os.name != "nt":
        os.chmod(temporary, 0o600)
    temporary.replace(path)


def redact(value: Any, secrets: Iterable[str] = ()) -> str:
    text = str(value or "")
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(access_token|app_secret|app_id)=([^&\s]+)", r"\1=[REDACTED]", text, flags=re.I)
    return " ".join(text.split())[:300]


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def sanitize_filename(value: str, max_len: int = 80) -> str:
    value = re.sub(r'[\\/:*?"<>|#\n\r\t]', " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value or "未命名")[:max_len]


def normalize_url(value: Any) -> str:
    url = html.unescape(str(value or "").strip())
    if url.startswith("//"):
        return "https:" + url
    return url


class HtmlToMarkdown(HTMLParser):
    """Small dependency-free conversion suitable for article reading output."""

    block_tags = {"p", "div", "section", "article", "blockquote", "li", "br"}
    skip_tags = {"script", "style", "head", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_tag = ""
        self.href_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip_tag:
            return
        if tag in self.skip_tags:
            self.skip_tag = tag
            return
        attrs_dict = dict(attrs)
        if tag in self.block_tags:
            self.parts.append("\n")
        elif re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n" + "#" * int(tag[1]) + " ")
        elif tag == "img":
            source = normalize_url(attrs_dict.get("data-src") or attrs_dict.get("src") or "")
            if source:
                self.parts.append(f"\n![{attrs_dict.get('alt') or '图片'}]({source})\n")
        elif tag == "a":
            self.href_stack.append(normalize_url(attrs_dict.get("href") or ""))
        elif tag in {"strong", "b"}:
            self.parts.append("**")

    def handle_endtag(self, tag: str) -> None:
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_tag = ""
            return
        if tag in self.block_tags or re.fullmatch(r"h[1-6]", tag or ""):
            self.parts.append("\n")
        elif tag == "a":
            href = self.href_stack.pop() if self.href_stack else ""
            if href:
                self.parts.append(f"({href})")
        elif tag in {"strong", "b"}:
            self.parts.append("**")

    def handle_data(self, data: str) -> None:
        if self.skip_tag:
            return
        raw_value = html.unescape(data)
        if not raw_value.strip():
            return
        leading_space = raw_value[0].isspace()
        trailing_space = raw_value[-1].isspace()
        value = " ".join(raw_value.split())
        if leading_space:
            value = " " + value
        if trailing_space:
            value += " "
        if self.href_stack:
            self.parts.append(f"[{value}]")
        else:
            self.parts.append(value)

    def markdown(self) -> str:
        value = "".join(self.parts)
        value = re.sub(r"[ \t]+\n", "\n", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()


def html_to_markdown(value: str) -> str:
    parser = HtmlToMarkdown()
    parser.feed(value or "")
    return parser.markdown()


def project_comments(payload: dict[str, Any], minimum_likes: int, limit: int) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    values = data.get("comments") if isinstance(data, dict) else []
    if not isinstance(values, list):
        values = []
    projected = []
    for item in values:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or "").strip()
        like_count = as_int(item.get("like_num"))
        if content and like_count >= minimum_likes:
            projected.append({"content": content, "like_count": like_count})
    return sorted(projected, key=lambda item: item["like_count"], reverse=True)[:limit]


def pick_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "articles", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def metric_projection(payload: dict[str, Any]) -> dict[str, int]:
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    return {
        "read_count": as_int(data.get("read_num")),
        "like_count": as_int(data.get("old_like_num")),
        "watching_count": as_int(data.get("like_num")),
        "comment_count": as_int(data.get("comment_count")),
        "share_count": as_int(data.get("share_num")),
    }


@dataclass
class CostGuard:
    max_cost: float
    confirmed: bool
    dry_run: bool
    spent: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)

    def require_plan(self, operations: list[Operation]) -> float:
        total = round(sum(operation.price_yuan for operation in operations), 2)
        if self.dry_run:
            emit_json(
                {
                    "status": "dry_run",
                    "estimated_cost_yuan": total,
                    "max_cost_yuan": self.max_cost,
                    "calls": [
                        {"operation": operation.name, "path": operation.path, "price_yuan": operation.price_yuan}
                        for operation in operations
                    ],
                }
            )
            raise SystemExit(0)
        if total > self.max_cost + 1e-9:
            raise CimidataError(f"预计 ¥{total:.2f} 超过 --max-cost ¥{self.max_cost:.2f}")
        if total > 0 and not self.confirmed:
            raise CimidataError("这是计费请求。先运行 --dry-run 并获得确认，再加入 --confirm-paid")
        return total

    def start(self, operation: Operation) -> None:
        if self.spent + operation.price_yuan > self.max_cost + 1e-9:
            raise CimidataError("实际调用将超过 --max-cost，已停止")
        self.spent = round(self.spent + operation.price_yuan, 2)
        self.calls.append(
            {"operation": operation.name, "path": operation.path, "price_yuan": operation.price_yuan}
        )


class CimidataClient:
    def __init__(self, app_id: str, app_secret: str, timeout: int, guard: CostGuard) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout = timeout
        self.guard = guard
        self.access_token = ""
        self.last_called_at: dict[str, float] = {}

    @property
    def protected_values(self) -> tuple[str, str, str]:
        return self.app_id, self.app_secret, self.access_token

    def request_json(
        self,
        path: str,
        *,
        body: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = API_BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        request = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "cimidata-wechat-article-collector/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise CimidataError(f"HTTP {exc.code}: {redact(raw, self.protected_values)}") from exc
        except urllib.error.URLError as exc:
            raise CimidataError(f"网络请求失败，未自动重试：{redact(exc, self.protected_values)}") from exc
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CimidataError(f"接口返回不是 JSON: {redact(raw, self.protected_values)}") from exc
        if not isinstance(result, dict):
            raise CimidataError("接口返回不是 JSON 对象")
        return result

    def token(self) -> str:
        if self.access_token:
            return self.access_token
        payload = self.request_json("/api/v2/token", body={"app_id": self.app_id, "app_secret": self.app_secret})
        data = payload.get("data") or {}
        token = data.get("access_token") if isinstance(data, dict) else ""
        if payload.get("code") != 200 or not isinstance(token, str) or not token:
            raise CimidataError(f"获取 token 失败: {redact(payload.get('msg'), self.protected_values)}")
        self.access_token = token
        return token

    def call(self, operation: Operation, body: dict[str, Any]) -> dict[str, Any]:
        previous = self.last_called_at.get(operation.path, 0.0)
        wait_seconds = operation.min_interval_seconds - (time.monotonic() - previous)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        self.guard.start(operation)
        payload = self.request_json(operation.path, body=body, params={"access_token": self.token()})
        self.last_called_at[operation.path] = time.monotonic()
        if payload.get("code") != 200:
            raise CimidataError(
                f"{operation.description}失败: code={payload.get('code')}, msg={redact(payload.get('msg'), self.protected_values)}"
            )
        if "balance" in payload:
            self.guard.calls[-1]["reported_balance"] = payload.get("balance")
        self.guard.calls[-1]["success"] = True
        return payload


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str, str]:
    app_id = getattr(args, "app_id", "") or os.getenv("CIMIDATA_APP_ID", "")
    app_secret = getattr(args, "app_secret", "") or os.getenv("CIMIDATA_APP_SECRET", "")
    if app_id and app_secret:
        return app_id, app_secret, "环境变量"
    credential_file = config_file_for(args)
    load_dotenv(credential_file)
    app_id = os.getenv("CIMIDATA_APP_ID", "")
    app_secret = os.getenv("CIMIDATA_APP_SECRET", "")
    if app_id and app_secret:
        return app_id, app_secret, f"配置文件：{credential_file}"
    raise CimidataError(
        "还没有完成次幂设置。请设置环境变量 CIMIDATA_APP_ID、CIMIDATA_APP_SECRET，"
        "或让 Agent 用 setup 在用户配置目录创建一个凭据文件。"
    )


def load_credentials(args: argparse.Namespace) -> tuple[str, str]:
    app_id, app_secret, _ = resolve_credentials(args)
    return app_id, app_secret


def emit_json(value: dict[str, Any], output_file: str = "") -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output_file:
        destination = Path(output_file).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)


def operation_for_args(args: argparse.Namespace) -> tuple[Operation, dict[str, Any]]:
    command = args.command
    if command == "account-search":
        return OPERATIONS[command], {"keyword": args.keyword}
    if command == "account-info":
        return OPERATIONS[command], {key: value for key, value in {"biz": args.biz, "nickname": args.nickname}.items() if value}
    if command == "account-day":
        return OPERATIONS[command], {key: value for key, value in {"wxid": args.wxid, "nickname": args.nickname}.items() if value}
    if command == "account-history":
        return OPERATIONS[command], {key: value for key, value in {"wxid": args.wxid, "nickname": args.nickname}.items() if value}
    if command in {"article-full", "article-metrics", "article-comments", "article-search-db"}:
        key = "keyword" if command == "article-search-db" else "url"
        return OPERATIONS[command], {key: getattr(args, key)}
    if command == "article-search-wechat":
        body: dict[str, Any] = {"keyword": args.keyword}
        if args.page:
            body["page"] = args.page
        return OPERATIONS[command], body
    if command in {"article-info", "article-body", "article-cover"}:
        return OPERATIONS["article-info"], {"url": args.url}
    if command in {"wechat-hot", "wechat-100k-hot"}:
        body = {
            key: value
            for key, value in {
                "category": args.category,
                "read_num": args.min_read,
                "published_at": args.since,
                "last_id": args.last_id,
            }.items()
            if value not in (None, "", 0)
        }
        if command == "wechat-100k-hot":
            body.pop("read_num", None)
        return OPERATIONS[command], body
    raise CimidataError(f"不支持的命令: {command}")


def run_single(args: argparse.Namespace) -> int:
    operation, body = operation_for_args(args)
    guard = CostGuard(args.max_cost, args.confirm_paid, args.dry_run)
    guard.require_plan([operation])
    app_id, app_secret = load_credentials(args)
    client = CimidataClient(app_id, app_secret, args.timeout, guard)
    payload = client.call(operation, body)
    result: dict[str, Any] = {
        "operation": args.command,
        "estimated_cost_yuan": guard.spent,
        "calls": guard.calls,
        "data": payload.get("data"),
    }
    if args.command == "article-body":
        article = payload.get("data") or {}
        body_html = article.get("body") if isinstance(article, dict) else ""
        result["data"] = {"html": body_html or "", "markdown": html_to_markdown(str(body_html or ""))}
    elif args.command == "article-cover":
        article = (payload.get("data") or {}).get("article") if isinstance(payload.get("data"), dict) else {}
        result["data"] = {"cover": article.get("cover") if isinstance(article, dict) else ""}
    elif args.command == "article-comments":
        result["data"] = {
            "comments": project_comments(payload, args.comment_min_likes, args.comment_limit),
            "has_more": bool(isinstance(payload.get("data"), dict) and payload["data"].get("buffer")),
        }
    elif args.command == "article-metrics":
        result["data"] = metric_projection(payload)
    emit_json(result, args.output_file)
    return 0


def run_status(args: argparse.Namespace) -> int:
    try:
        app_id, app_secret, storage = resolve_credentials(args)
        configured = True
        setup_error = ""
    except CimidataError as exc:
        app_id = app_secret = ""
        storage = str(config_file_for(args))
        configured = False
        setup_error = str(exc)
    result: dict[str, Any] = {
        "configured": configured,
        "credential_file": storage,
        "next_step": "可以直接说：采集某公众号最近 1 篇文章。" if configured else "请说：带我开通次幂。",
    }
    if setup_error:
        result["setup_hint"] = setup_error
    if configured and args.verify:
        client = CimidataClient(app_id, app_secret, args.timeout, CostGuard(0.0, True, False))
        client.token()
        result["credentials_verified"] = True
    emit_json(result)
    return 0


def run_setup(args: argparse.Namespace) -> int:
    credential_file = config_file_for(args)
    if credential_file.exists() and not args.overwrite:
        raise CimidataError(f"本机已经配置次幂凭据：{credential_file}。如确认更新，请加入 --overwrite。")
    if getattr(args, "dry_run", False):
        emit_json(
            {
                "status": "dry_run",
                "credential_file": str(credential_file),
                "would_prompt_for": ["App ID", "App Secret（隐藏输入）"],
                "would_verify_token": True,
            }
        )
        return 0
    app_id = getattr(args, "app_id", "") or ""
    app_secret = getattr(args, "app_secret", "") or ""
    if not app_id or not app_secret:
        if not sys.stdin.isatty():
            raise CimidataError("当前无法输入 App ID 和 App Secret。请在本机终端运行 setup，或把两个值发给 AI 帮你保存。")
        sys.stdout.write(
            "次幂本地设置（不会写入仓库，也不会显示 App Secret）\n"
            "请先在次幂后台完成开通/充值，并进入 API 凭据页面。\n"
        )
        app_id = input("粘贴 App ID：").strip()
        app_secret = getpass.getpass("粘贴 App Secret（输入不会显示）：").strip()
    if not app_id or not app_secret:
        raise CimidataError("App ID 和 App Secret 均不能为空。")
    client = CimidataClient(app_id, app_secret, args.timeout, CostGuard(0.0, True, False))
    client.token()
    write_credentials_file(credential_file, app_id, app_secret)
    storage = f"配置文件：{credential_file}"
    emit_json(
        {
            "status": "configured",
            "credential_file": storage,
            "credentials_verified": True,
            "next_step": "现在可以说：采集某公众号最近 1 篇文章。",
        }
    )
    return 0


def collect_plan(args: argparse.Namespace) -> list[Operation]:
    if args.article_url:
        operations = [OPERATIONS["article-info"], OPERATIONS["article-full"]]
    else:
        operations = []
        if not args.wxid:
            operations.append(OPERATIONS["account-search"])
        operations.extend([OPERATIONS["account-history"], *[OPERATIONS["article-full"]] * args.limit])
    if args.with_metrics:
        operations.extend([OPERATIONS["article-metrics"]] * args.limit)
    if args.with_comments:
        operations.extend([OPERATIONS["article-comments"]] * args.limit)
    return operations


def article_from_info(payload: dict[str, Any], fallback_url: str) -> dict[str, Any]:
    data = payload.get("data") or {}
    article = data.get("article") if isinstance(data, dict) else {}
    account = data.get("account") if isinstance(data, dict) else {}
    article = article if isinstance(article, dict) else {}
    account = account if isinstance(account, dict) else {}
    return {
        "article_url": fallback_url,
        "title": article.get("title") or "未命名文章",
        "publish_time": article.get("published_at") or "",
        "account": account.get("nickname") or "",
        "author": article.get("author") or "",
        "digest": article.get("digest") or "",
        "cover": article.get("cover") or "",
    }


def article_from_history(item: dict[str, Any], fallback_account: str) -> dict[str, Any]:
    return {
        "article_url": normalize_url(item.get("content_url") or item.get("url") or ""),
        "title": str(item.get("title") or "未命名文章"),
        "publish_time": str(item.get("published_at") or item.get("post_time") or ""),
        "account": fallback_account,
        "author": "",
        "digest": str(item.get("digest") or ""),
        "cover": normalize_url(item.get("cover") or ""),
    }


def image_extension(content_type: str, source: str) -> str:
    media = content_type.split(";", 1)[0].lower()
    by_media = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if media in by_media:
        return by_media[media]
    suffix = Path(urllib.parse.urlparse(source).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def download_images(markdown: str, asset_dir: Path, timeout: int) -> tuple[str, int, list[str]]:
    sources = re.findall(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", markdown)
    replacements: dict[str, str] = {}
    failures: list[str] = []
    for source in dict.fromkeys(sources):
        if re.search(r"(?:wx_fmt=gif|\.gif(?:$|\?))", source, flags=re.I):
            continue
        try:
            request = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://mp.weixin.qq.com/"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content = response.read(20 * 1024 * 1024 + 1)
                content_type = response.headers.get("Content-Type", "")
            if len(content) > 20 * 1024 * 1024 or content.startswith((b"GIF87a", b"GIF89a")):
                continue
            asset_dir.mkdir(parents=True, exist_ok=True)
            destination = asset_dir / f"{len(replacements) + 1:03d}{image_extension(content_type, source)}"
            destination.write_bytes(content)
            replacements[source] = (Path("assets") / asset_dir.name / destination.name).as_posix()
        except (OSError, urllib.error.URLError) as exc:
            failures.append(f"{source}: {type(exc).__name__}")
    for source, local_path in replacements.items():
        markdown = markdown.replace(source, local_path)
    return markdown, len(replacements), failures


def write_collect_output(output_dir: Path, articles: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    account_name = sanitize_filename(articles[0].get("account") or "公众号") if articles else "公众号"
    account_dir = output_dir / account_name
    account_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "title", "article_url", "publish_time", "account", "author", "digest", "read_count", "like_count",
        "watching_count", "comment_count", "share_count",
    ]
    with (account_dir / "文章数据.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(articles)
    for article in articles:
        article_path = account_dir / f"{sanitize_filename(str(article.get('publish_time') or '未知日期'), 18)}-{sanitize_filename(str(article['title']))}.md"
        metrics = "｜".join(
            f"{label} {article.get(key, 0)}"
            for label, key in (("阅读", "read_count"), ("点赞", "like_count"), ("在看", "watching_count"), ("评论", "comment_count"), ("分享", "share_count"))
        )
        lines = [
            f"# {article['title']}",
            "",
            f"- 公众号：{article.get('account') or '未知'}",
            f"- 发布时间：{article.get('publish_time') or '未知'}",
            f"- 原文：{article.get('article_url') or ''}",
            f"- 互动：{metrics}",
        ]
        if article.get("digest"):
            lines.extend(["", f"> {article['digest']}"])
        if article.get("cover"):
            lines.extend(["", f"![封面]({article['cover']})"])
        lines.extend(["", "## 正文", "", article.get("markdown") or "（正文为空）"])
        comments = article.get("comments") or []
        if comments:
            lines.extend(["", "## 高赞一级评论", ""])
            for comment in comments:
                lines.extend([f"> {comment['content']}", ">", f"> 点赞：{comment['like_count']}", ""])
        article_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    (account_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_collect(args: argparse.Namespace) -> int:
    if not any((args.wxid, args.nickname, args.article_url)):
        raise CimidataError("collect 必须提供 --wxid、--nickname 或 --article-url")
    if args.limit < 1:
        raise CimidataError("--limit 至少为 1")
    guard = CostGuard(args.max_cost, args.confirm_paid, args.dry_run)
    guard.require_plan(collect_plan(args))
    app_id, app_secret = load_credentials(args)
    client = CimidataClient(app_id, app_secret, args.timeout, guard)
    if args.article_url:
        info_payload = client.call(OPERATIONS["article-info"], {"url": args.article_url})
        articles = [article_from_info(info_payload, args.article_url)]
    else:
        wxid = args.wxid
        account_name = args.nickname
        if not wxid:
            searched = client.call(OPERATIONS["account-search"], {"keyword": args.nickname})
            accounts = (searched.get("data") or {}).get("accounts") if isinstance(searched.get("data"), dict) else []
            exact = [item for item in accounts if isinstance(item, dict) and item.get("nickname") == args.nickname]
            if len(exact) != 1 or not exact[0].get("wxid"):
                candidates = [
                    {"nickname": item.get("nickname"), "wxid": item.get("wxid"), "username": item.get("username")}
                    for item in accounts[:5]
                    if isinstance(item, dict)
                ]
                raise CimidataError(
                    "未能唯一确定公众号。请从候选中确认目标后，使用 wxid 重试："
                    + json.dumps(candidates, ensure_ascii=False)
                )
            wxid = str(exact[0]["wxid"])
            account_name = str(exact[0].get("nickname") or args.nickname)
        history = client.call(OPERATIONS["account-history"], {"wxid": wxid})
        selected = [article_from_history(item, account_name) for item in pick_items(history)]
        articles = [item for item in selected if item["article_url"]][: args.limit]
        if not articles:
            raise CimidataError("历史列表未返回可用文章链接")
    for article in articles:
        details = client.call(OPERATIONS["article-full"], {"url": article["article_url"]})
        detail_data = details.get("data") or {}
        full_html = detail_data.get("html") if isinstance(detail_data, dict) else ""
        if not isinstance(full_html, str) or not full_html.strip():
            raise CimidataError(f"文章正文为空：{article['title']}")
        article["markdown"] = html_to_markdown(full_html)
        article.update({"read_count": 0, "like_count": 0, "watching_count": 0, "comment_count": 0, "share_count": 0})
        article["comments"] = []
        if args.with_metrics:
            article.update(metric_projection(client.call(OPERATIONS["article-metrics"], {"url": article["article_url"]})))
        if args.with_comments:
            comments = client.call(OPERATIONS["article-comments"], {"url": article["article_url"]})
            article["comments"] = project_comments(comments, args.comment_min_likes, args.comment_limit)
        if args.download_images:
            asset_dir = Path(args.output_dir).expanduser() / sanitize_filename(article.get("account") or "公众号") / "assets" / sanitize_filename(article["title"])
            article["markdown"], _, failures = download_images(article["markdown"], asset_dir, args.timeout)
            if failures:
                article["image_failures"] = failures
    manifest = {
        "status": "partial_success" if any(item.get("image_failures") for item in articles) else "success",
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "article_count": len(articles),
        "with_metrics": args.with_metrics,
        "with_comments": args.with_comments,
        "download_images": args.download_images,
        "estimated_cost_yuan": guard.spent,
        "max_cost_yuan": args.max_cost,
        "calls": guard.calls,
    }
    write_collect_output(Path(args.output_dir).expanduser(), articles, manifest)
    emit_json({"status": manifest["status"], "article_count": len(articles), "estimated_cost_yuan": guard.spent, "calls": guard.calls, "output_dir": str(Path(args.output_dir).expanduser())})
    return 0


def run_provider_call(args: argparse.Namespace) -> int:
    try:
        body = json.loads(args.body_json)
    except json.JSONDecodeError as exc:
        raise CimidataError("--body-json 必须是 JSON 对象") from exc
    if not isinstance(body, dict) or not args.path.startswith("/api/"):
        raise CimidataError("--path 必须以 /api/ 开头，--body-json 必须是 JSON 对象")
    operation = Operation("provider-call", args.path, args.price, "按当前 ShowDoc 文档调用辅助接口")
    guard = CostGuard(args.max_cost, args.confirm_paid, args.dry_run)
    guard.require_plan([operation])
    app_id, app_secret = load_credentials(args)
    client = CimidataClient(app_id, app_secret, args.timeout, guard)
    payload = client.call(operation, body)
    emit_json({"operation": "provider-call", "estimated_cost_yuan": guard.spent, "calls": guard.calls, "data": payload.get("data")}, args.output_file)
    return 0


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env-file", default="", help="指定包含 App ID 和 App Secret 的 .env 文件")
    parser.add_argument("--config-file", default="", help="指定本地凭据文件；默认使用用户配置目录")
    parser.add_argument("--app-id", default="", help=argparse.SUPPRESS)
    parser.add_argument("--app-secret", default="", help=argparse.SUPPRESS)
    parser.add_argument("--max-cost", type=float, default=0.0, help="本次最高允许消耗的人民币金额")
    parser.add_argument("--confirm-paid", action="store_true", help="已获得用户对本次范围和金额的明确确认")
    parser.add_argument("--dry-run", action="store_true", help="只输出调用与成本计划，不读取凭据或调用 API")
    parser.add_argument("--timeout", type=int, default=30, help="单次网络请求超时秒数")
    parser.add_argument("--output-file", default="", help="可选：把 JSON 结果同步写入该文件")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    add_common_arguments(common)
    parser = argparse.ArgumentParser(description="以明确成本上限调用次幂微信公众号接口", parents=[common])
    subparsers = parser.add_subparsers(dest="command", required=True)

    def command(name: str, help_text: str) -> argparse.ArgumentParser:
        return subparsers.add_parser(name, help=help_text, parents=[common])

    def simple_command(name: str, help_text: str) -> argparse.ArgumentParser:
        return subparsers.add_parser(name, help=help_text)

    item = simple_command("status", "检查次幂是否已完成本地设置")
    item.add_argument("--env-file", default="", help="指定包含 App ID 和 App Secret 的 .env 文件")
    item.add_argument("--config-file", default="", help="指定本地凭据文件；默认使用用户配置目录")
    item.add_argument("--timeout", type=int, default=30, help="免费校验 token 的超时秒数")
    item.add_argument("--verify", action="store_true", help="免费校验当前凭据能否获取 token")
    item = simple_command("setup", "用本机隐藏输入完成次幂设置")
    item.add_argument("--env-file", default="", help="指定包含 App ID 和 App Secret 的 .env 文件")
    item.add_argument("--config-file", default="", help="指定本地凭据文件；默认使用用户配置目录")
    item.add_argument("--timeout", type=int, default=30, help="免费校验 token 的超时秒数")
    item.add_argument("--app-id", default="", help=argparse.SUPPRESS)
    item.add_argument("--app-secret", default="", help=argparse.SUPPRESS)
    item.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    item.add_argument("--overwrite", action="store_true", help="确认覆盖已有本机凭据")
    item = command("account-search", "关键词搜索公众号")
    item.add_argument("--keyword", required=True)
    item = command("account-info", "获取公众号基本信息")
    item.add_argument("--biz", default="")
    item.add_argument("--nickname", default="")
    item = command("account-day", "获取公众号当天发文")
    item.add_argument("--wxid", default="")
    item.add_argument("--nickname", default="")
    item = command("account-history", "获取公众号历史文章")
    item.add_argument("--wxid", default="")
    item.add_argument("--nickname", default="")
    for name, help_text in (("article-full", "获取完整文章 HTML"), ("article-body", "提取文章纯正文"), ("article-info", "获取文章与账号基础信息"), ("article-cover", "获取文章封面地址"), ("article-metrics", "获取完整互动指标"), ("article-comments", "获取脱敏高赞一级评论")):
        item = command(name, help_text)
        item.add_argument("--url", required=True)
        if name == "article-comments":
            item.add_argument("--comment-min-likes", type=int, default=COMMENT_MIN_LIKES)
            item.add_argument("--comment-limit", type=int, default=COMMENT_LIMIT)
    item = command("article-search-db", "数据库关键词搜索文章")
    item.add_argument("--keyword", required=True)
    item = command("article-search-wechat", "微信搜一搜关键词搜索文章")
    item.add_argument("--keyword", required=True)
    item.add_argument("--page", type=int, default=0, choices=range(0, 6))
    for name, help_text in (("wechat-hot", "获取微信爆文"), ("wechat-100k-hot", "获取 10w+ 爆文")):
        item = command(name, help_text)
        item.add_argument("--category", default="")
        item.add_argument("--min-read", type=int, default=0)
        item.add_argument("--since", default="")
        item.add_argument("--last-id", type=int, default=0)
    item = command("provider-call", "按最新 ShowDoc 调用未固化的辅助接口")
    item.add_argument("--path", required=True)
    item.add_argument("--body-json", required=True)
    item.add_argument("--price", type=float, required=True)
    item = command("collect", "归档指定公众号的文章")
    item.add_argument("--wxid", default="")
    item.add_argument("--nickname", default="")
    item.add_argument("--article-url", default="")
    item.add_argument("--limit", type=int, default=1)
    item.add_argument("--with-metrics", action="store_true")
    item.add_argument("--with-comments", action="store_true")
    item.add_argument("--comment-min-likes", type=int, default=COMMENT_MIN_LIKES)
    item.add_argument("--comment-limit", type=int, default=COMMENT_LIMIT)
    item.add_argument("--download-images", action="store_true")
    item.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "status":
            return run_status(args)
        if args.command == "setup":
            return run_setup(args)
        if args.command == "collect":
            return run_collect(args)
        if args.command == "provider-call":
            return run_provider_call(args)
        return run_single(args)
    except CimidataError as exc:
        emit_json({"status": "failed", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
