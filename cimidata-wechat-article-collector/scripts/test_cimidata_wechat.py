from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("cimidata_wechat.py")
SPEC = importlib.util.spec_from_file_location("cimidata_wechat", MODULE_PATH)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = collector
SPEC.loader.exec_module(collector)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class CimidataWechatTests(unittest.TestCase):
    def test_cost_gate_requires_confirmation_and_respects_total_cap(self) -> None:
        guard = collector.CostGuard(max_cost=0.20, confirmed=False, dry_run=False)
        with self.assertRaisesRegex(collector.CimidataError, "--confirm-paid"):
            guard.require_plan([collector.OPERATIONS["account-search"]])

        capped = collector.CostGuard(max_cost=0.08, confirmed=True, dry_run=False)
        with self.assertRaisesRegex(collector.CimidataError, "超过 --max-cost"):
            capped.require_plan([collector.OPERATIONS["account-history"], collector.OPERATIONS["article-full"], collector.OPERATIONS["article-metrics"]])

    def test_collect_dry_run_is_bounded_and_needs_no_credentials(self) -> None:
        args = collector.build_parser().parse_args(
            ["collect", "--wxid", "gh_example", "--limit", "1", "--with-metrics", "--max-cost", "0.30", "--dry-run"]
        )
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as exited:
            collector.run_collect(args)
        self.assertEqual(exited.exception.code, 0)
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["estimated_cost_yuan"], 0.09)
        self.assertEqual([item["operation"] for item in plan["calls"]], ["account-history", "article-full", "article-metrics"])

    def test_nickname_collection_budgets_for_account_resolution(self) -> None:
        args = collector.build_parser().parse_args(
            ["collect", "--nickname", "示例账号", "--limit", "1", "--max-cost", "0.16", "--dry-run"]
        )
        plan = collector.collect_plan(args)
        self.assertEqual([operation.name for operation in plan], ["account-search", "account-history", "article-full"])
        self.assertEqual(sum(operation.price_yuan for operation in plan), 0.16)

    def test_client_uses_json_token_then_access_token_query_without_cookie(self) -> None:
        guard = collector.CostGuard(max_cost=0.10, confirmed=True, dry_run=False)
        client = collector.CimidataClient("app-id", "app-secret", timeout=3, guard=guard)
        with mock.patch.object(
            collector.urllib.request,
            "urlopen",
            side_effect=[FakeResponse({"code": 200, "data": {"access_token": "session-token"}}), FakeResponse({"code": 200, "data": {"html": "<p>正文</p>"}})],
        ) as urlopen:
            response = client.call(collector.OPERATIONS["article-full"], {"url": "https://mp.weixin.qq.com/s/example"})

        self.assertEqual(response["data"]["html"], "<p>正文</p>")
        token_request = urlopen.call_args_list[0].args[0]
        article_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(json.loads(token_request.data.decode("utf-8")), {"app_id": "app-id", "app_secret": "app-secret"})
        self.assertIn("access_token=session-token", article_request.full_url)
        self.assertEqual(article_request.get_header("Content-type"), "application/json")
        self.assertIsNone(article_request.get_header("Cookie"))
        self.assertEqual(guard.spent, 0.01)

    def test_article_body_uses_cheapest_body_endpoint_and_cover_uses_info(self) -> None:
        body_args = collector.build_parser().parse_args(["article-body", "--url", "https://example/article"])
        operation, body = collector.operation_for_args(body_args)
        self.assertEqual(operation.name, "article-full")
        self.assertEqual(body, {"url": "https://example/article"})

        cover_args = collector.build_parser().parse_args(["article-cover", "--url", "https://example/article"])
        cover_operation, cover_body = collector.operation_for_args(cover_args)
        self.assertEqual(cover_operation.name, "article-info")
        self.assertEqual(cover_body, body)

    def test_comments_are_deidentified_sorted_and_capped(self) -> None:
        result = collector.project_comments(
            {
                "data": {
                    "comments": [
                        {"content": "低赞", "like_num": 9, "nick_name": "不应出现"},
                        {"content": "第二", "like_num": 12, "logo_url": "不应出现"},
                        {"content": "第一", "like_num": 30, "content_id": "不应出现"},
                    ]
                }
            },
            minimum_likes=10,
            limit=1,
        )
        self.assertEqual(result, [{"content": "第一", "like_count": 30}])

    def test_html_conversion_removes_script_and_preserves_image(self) -> None:
        markdown = collector.html_to_markdown(
            '<div><script>secret()</script><h2>标题</h2><p>正文 <strong>加粗</strong></p><img data-src="//img.example/a.jpg"></div>'
        )
        self.assertIn("## 标题", markdown)
        self.assertIn("正文 **加粗**", markdown)
        self.assertIn("![图片](https://img.example/a.jpg)", markdown)
        self.assertNotIn("secret", markdown)

    def test_setup_writes_private_external_config_only_after_free_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "credentials.env"
            args = collector.build_parser().parse_args(
                [
                    "setup",
                    "--config-file",
                    str(config_file),
                    "--app-id",
                    "app-id-value",
                    "--app-secret",
                    "secret-value",
                ]
            )
            with mock.patch.object(collector.CimidataClient, "token", return_value="verified-token"):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(collector.run_setup(args), 0)

            self.assertTrue(config_file.exists())
            self.assertEqual(config_file.stat().st_mode & 0o777, 0o600)
            self.assertIn("CIMIDATA_APP_ID=app-id-value", config_file.read_text(encoding="utf-8"))
            self.assertNotIn("secret-value", output.getvalue())
            result = json.loads(output.getvalue())
            self.assertTrue(result["credentials_verified"])

    def test_default_config_file_is_agent_independent(self) -> None:
        path = collector.default_config_file()
        self.assertEqual(path.name, ".env")
        self.assertEqual(path.parent, MODULE_PATH.parent.parent)
        self.assertNotIn("application support", str(path).lower())

    def test_status_never_echoes_stored_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "credentials.env"
            config_file.write_text("CIMIDATA_APP_ID=visible-id\nCIMIDATA_APP_SECRET=secret-value\n", encoding="utf-8")
            args = collector.build_parser().parse_args(["status", "--config-file", str(config_file)])
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(collector.run_status(args), 0)
            rendered = output.getvalue()
            self.assertIn('"configured": true', rendered)
            self.assertNotIn("visible-id", rendered)
            self.assertNotIn("secret-value", rendered)

    def test_collect_output_contains_manifest_csv_and_markdown(self) -> None:
        article = {
            "title": "示例文章",
            "article_url": "https://mp.weixin.qq.com/s/example",
            "publish_time": "2026-08-19T10:00:00",
            "account": "示例账号",
            "author": "作者",
            "digest": "摘要",
            "markdown": "正文",
            "read_count": 1,
            "like_count": 2,
            "watching_count": 3,
            "comment_count": 4,
            "share_count": 5,
            "comments": [{"content": "高赞评论", "like_count": 10}],
        }
        with tempfile.TemporaryDirectory() as directory:
            collector.write_collect_output(Path(directory), [article], {"status": "success"})
            output = Path(directory) / "示例账号"
            self.assertTrue((output / "文章数据.csv").exists())
            self.assertTrue((output / "manifest.json").exists())
            markdown_files = list(output.glob("*.md"))
            self.assertEqual(len(markdown_files), 1)
            rendered = markdown_files[0].read_text(encoding="utf-8")
            self.assertIn("高赞一级评论", rendered)
            self.assertNotIn("nick_name", rendered)

    def test_date_window_includes_the_whole_end_date(self) -> None:
        start, end = collector.parse_date_window("2021-01-01", "2021-12-31")
        self.assertEqual(end - start, 365 * 24 * 60 * 60)

    def test_range_dry_run_reports_a_bounded_maximum_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = collector.build_parser().parse_args(
                [
                    "collect-range",
                    "--wxid",
                    "gh_example",
                    "--start-date",
                    "2021-01-01",
                    "--end-date",
                    "2021-12-31",
                    "--max-pages",
                    "2",
                    "--max-articles",
                    "3",
                    "--max-cost",
                    "0.13",
                    "--state-file",
                    str(Path(directory) / "index.sqlite3"),
                    "--dry-run",
                ]
            )
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(collector.run_collect_range(args), 0)

        plan = json.loads(output.getvalue())
        self.assertEqual(plan["status"], "dry_run")
        self.assertEqual(plan["estimated_max_cost_yuan"], 0.10)
        self.assertEqual(plan["breakdown"]["history_pages"], 2)
        self.assertEqual(plan["breakdown"]["article_bodies"], 0)

    def test_range_metadata_phase_does_not_budget_or_buy_article_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = collector.build_parser().parse_args(
                [
                    "collect-range",
                    "--wxid",
                    "gh_example",
                    "--start-date",
                    "2021-01-01",
                    "--end-date",
                    "2021-12-31",
                    "--max-pages",
                    "2",
                    "--max-articles",
                    "500",
                    "--metadata-only",
                    "--max-cost",
                    "0.10",
                    "--state-file",
                    str(Path(directory) / "index.sqlite3"),
                    "--dry-run",
                ]
            )
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(collector.run_collect_range(args), 0)

        plan = json.loads(output.getvalue())
        self.assertEqual(plan["estimated_max_cost_yuan"], 0.10)
        self.assertEqual(plan["breakdown"]["article_bodies"], 0)

    def test_range_scan_resumes_then_reuses_cached_body_without_api_calls(self) -> None:
        recent_page = {
            "code": 200,
            "data": {
                "items": [
                    {
                        "title": "新文章",
                        "content_url": "https://mp.weixin.qq.com/s/new",
                        "published_at": "2026-08-21T10:00:00",
                    }
                ],
                "last_id": "cursor-1",
            },
        }
        target_page = {
            "code": 200,
            "data": {
                "items": [
                    {
                        "title": "目标文章",
                        "content_url": "https://mp.weixin.qq.com/s/target",
                        "published_at": "2021-06-01T10:00:00",
                    },
                    {
                        "title": "更早文章",
                        "content_url": "https://mp.weixin.qq.com/s/older",
                        "published_at": "2020-12-31T10:00:00",
                    },
                ],
                "last_id": "cursor-2",
            },
        }
        body_payload = {"code": 200, "data": {"html": "<p>目标正文</p>"}}

        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "index.sqlite3"
            output_dir = Path(directory) / "archive"
            base = [
                "collect-range",
                "--wxid",
                "gh_example",
                "--nickname",
                "示例号",
                "--start-date",
                "2021-01-01",
                "--end-date",
                "2021-12-31",
                "--state-file",
                str(state_file),
                "--output-dir",
                str(output_dir),
                "--confirm-paid",
            ]

            first_args = collector.build_parser().parse_args(
                [*base, "--max-pages", "1", "--max-articles", "10", "--max-cost", "0.05"]
            )
            first_output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", return_value=("app", "secret")),
                mock.patch.object(collector.CimidataClient, "call", return_value=recent_page) as first_call,
                redirect_stdout(first_output),
            ):
                self.assertEqual(collector.run_collect_range(first_args), 0)
            first_result = json.loads(first_output.getvalue())
            self.assertEqual(first_result["status"], "partial")
            self.assertEqual(first_result["reason"], "budget_exhausted")
            self.assertEqual(first_call.call_count, 1)

            second_args = collector.build_parser().parse_args(
                [*base, "--max-pages", "2", "--max-articles", "10", "--max-cost", "0.10"]
            )
            second_output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", return_value=("app", "secret")),
                mock.patch.object(collector.CimidataClient, "call", return_value=target_page) as second_call,
                redirect_stdout(second_output),
            ):
                self.assertEqual(collector.run_collect_range(second_args), 0)
            second_result = json.loads(second_output.getvalue())
            self.assertEqual(second_result["status"], "metadata_ready")
            self.assertEqual(second_result["article_count"], 1)
            self.assertEqual(second_call.call_args_list[0].args[1]["last_id"], "cursor-1")

            body_args = collector.build_parser().parse_args(
                [*base, "--max-pages", "2", "--max-articles", "10", "--max-cost", "0.01"]
            )
            body_output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", return_value=("app", "secret")),
                mock.patch.object(collector.CimidataClient, "call", return_value=body_payload) as body_call,
                redirect_stdout(body_output),
            ):
                self.assertEqual(collector.run_collect_range(body_args), 0)
            body_result = json.loads(body_output.getvalue())
            self.assertEqual(body_result["status"], "success")
            self.assertEqual(body_call.call_args_list[0].args[0].name, "article-full")

            cached_args = collector.build_parser().parse_args(
                [*base, "--max-pages", "2", "--max-articles", "10", "--max-cost", "0"]
            )
            cached_output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", side_effect=AssertionError("credentials should not be read")),
                mock.patch.object(collector.CimidataClient, "call", side_effect=AssertionError("API should not be called")),
                redirect_stdout(cached_output),
            ):
                self.assertEqual(collector.run_collect_range(cached_args), 0)
            cached_result = json.loads(cached_output.getvalue())
            self.assertEqual(cached_result["status"], "success")
            self.assertEqual(cached_result["estimated_cost_yuan"], 0.0)

    def test_range_scan_stops_on_repeated_page_without_buying_bodies(self) -> None:
        first_page = {
            "code": 200,
            "data": {
                "items": [
                    {
                        "title": "第一页",
                        "content_url": "https://mp.weixin.qq.com/s/first",
                        "published_at": "2026-08-21T10:00:00",
                    },
                    {
                        "title": "已证明覆盖边界",
                        "content_url": "https://mp.weixin.qq.com/s/proven-boundary",
                        "published_at": "2025-08-21T10:00:00",
                    }
                ],
                "last_id": "same-cursor",
            },
        }
        stuck_page = {
            "code": 200,
            "data": {
                "items": [
                    {
                        "title": "已付费但游标未前进",
                        "content_url": "https://mp.weixin.qq.com/s/stuck",
                        "published_at": "2020-12-31T10:00:00",
                    }
                ],
                "last_id": "same-cursor",
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            args = collector.build_parser().parse_args(
                [
                    "collect-range",
                    "--wxid",
                    "gh_example",
                    "--start-date",
                    "2021-01-01",
                    "--end-date",
                    "2021-12-31",
                    "--max-pages",
                    "2",
                    "--max-articles",
                    "10",
                    "--max-cost",
                    "0.20",
                    "--state-file",
                    str(Path(directory) / "index.sqlite3"),
                    "--output-dir",
                    str(Path(directory) / "archive"),
                    "--confirm-paid",
                ]
            )
            output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", return_value=("app", "secret")),
                mock.patch.object(collector.CimidataClient, "call", side_effect=[first_page, stuck_page]) as api_call,
                redirect_stdout(output),
            ):
                self.assertEqual(collector.run_collect_range(args), 0)

            blocked_output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", side_effect=AssertionError("blocked scan should not read credentials")),
                mock.patch.object(collector.CimidataClient, "call", side_effect=AssertionError("blocked scan should not call API")),
                redirect_stdout(blocked_output),
            ):
                self.assertEqual(collector.run_collect_range(args), 0)

            cached_args = collector.build_parser().parse_args(
                [
                    "collect-range",
                    "--wxid",
                    "gh_example",
                    "--start-date",
                    "2025-08-22",
                    "--end-date",
                    "2026-08-21",
                    "--max-pages",
                    "1",
                    "--max-articles",
                    "0",
                    "--metadata-only",
                    "--max-cost",
                    "0",
                    "--state-file",
                    str(Path(directory) / "index.sqlite3"),
                ]
            )
            cached_output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", side_effect=AssertionError("covered range should not read credentials")),
                mock.patch.object(collector.CimidataClient, "call", side_effect=AssertionError("covered range should not call API")),
                redirect_stdout(cached_output),
            ):
                self.assertEqual(collector.run_collect_range(cached_args), 0)

        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["reason"], "repeated_page")
        self.assertTrue(result["oldest_reached"].startswith("2025-08-21"))
        self.assertEqual(api_call.call_count, 2)
        blocked_result = json.loads(blocked_output.getvalue())
        self.assertEqual(blocked_result["reason"], "repeated_page")
        self.assertEqual(blocked_result["pages_used"], 0)
        cached_result = json.loads(cached_output.getvalue())
        self.assertEqual(cached_result["status"], "metadata_ready")
        self.assertEqual(cached_result["estimated_cost_yuan"], 0.0)

    def test_range_state_location_is_stable_across_output_directories(self) -> None:
        first = collector.build_parser().parse_args(
            [
                "collect-range",
                "--wxid",
                "gh_example",
                "--start-date",
                "2021-01-01",
                "--end-date",
                "2021-12-31",
                "--output-dir",
                "/tmp/archive-one",
            ]
        )
        second = collector.build_parser().parse_args(
            [
                "collect-range",
                "--wxid",
                "gh_example",
                "--start-date",
                "2021-01-01",
                "--end-date",
                "2021-12-31",
                "--output-dir",
                "/tmp/archive-two",
            ]
        )
        self.assertEqual(collector.range_state_path(first), collector.range_state_path(second))

    def test_range_exact_nickname_uses_lower_cost_account_detail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = collector.build_parser().parse_args(
                [
                    "collect-range",
                    "--nickname",
                    "示例号",
                    "--start-date",
                    "2021-01-01",
                    "--end-date",
                    "2021-12-31",
                    "--max-pages",
                    "2",
                    "--metadata-only",
                    "--max-cost",
                    "0.14",
                    "--state-file",
                    str(Path(directory) / "index.sqlite3"),
                    "--dry-run",
                ]
            )
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(collector.run_collect_range(args), 0)

        plan = json.loads(output.getvalue())
        self.assertEqual(plan["estimated_max_cost_yuan"], 0.14)
        self.assertEqual(plan["breakdown"]["account_resolution_operation"], "account-info")

    def test_range_history_error_reports_cost_and_saved_progress(self) -> None:
        def fail_after_charging(client, operation, body):
            del body
            client.guard.start(operation)
            raise collector.CimidataError("上游暂时失败")

        with tempfile.TemporaryDirectory() as directory:
            args = collector.build_parser().parse_args(
                [
                    "collect-range",
                    "--wxid",
                    "gh_example",
                    "--start-date",
                    "2021-01-01",
                    "--end-date",
                    "2021-12-31",
                    "--max-pages",
                    "1",
                    "--max-articles",
                    "0",
                    "--metadata-only",
                    "--max-cost",
                    "0.05",
                    "--state-file",
                    str(Path(directory) / "index.sqlite3"),
                    "--confirm-paid",
                ]
            )
            output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", return_value=("app", "secret")),
                mock.patch.object(collector.CimidataClient, "call", new=fail_after_charging),
                redirect_stdout(output),
            ):
                self.assertEqual(collector.run_collect_range(args), 2)

        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["reason"], "history_failed")
        self.assertEqual(result["estimated_cost_yuan"], 0.05)
        self.assertTrue(result["resume_saved"])

    def test_range_invalid_page_is_saved_and_not_bought_again(self) -> None:
        invalid_page = {"code": 200, "data": {"items": [], "last_id": "unexpected-next"}}
        with tempfile.TemporaryDirectory() as directory:
            args = collector.build_parser().parse_args(
                [
                    "collect-range",
                    "--wxid",
                    "gh_example",
                    "--start-date",
                    "2021-01-01",
                    "--end-date",
                    "2021-12-31",
                    "--max-pages",
                    "1",
                    "--max-articles",
                    "0",
                    "--metadata-only",
                    "--max-cost",
                    "0.05",
                    "--state-file",
                    str(Path(directory) / "index.sqlite3"),
                    "--confirm-paid",
                ]
            )
            first_output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", return_value=("app", "secret")),
                mock.patch.object(collector.CimidataClient, "call", return_value=invalid_page) as first_call,
                redirect_stdout(first_output),
            ):
                self.assertEqual(collector.run_collect_range(args), 0)

            blocked_output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", side_effect=AssertionError("blocked scan should not read credentials")),
                mock.patch.object(collector.CimidataClient, "call", side_effect=AssertionError("invalid page should not be repurchased")),
                redirect_stdout(blocked_output),
            ):
                self.assertEqual(collector.run_collect_range(args), 0)

        self.assertEqual(first_call.call_count, 1)
        self.assertEqual(json.loads(first_output.getvalue())["reason"], "invalid_page")
        blocked = json.loads(blocked_output.getvalue())
        self.assertEqual(blocked["reason"], "invalid_page")
        self.assertEqual(blocked["pages_used"], 0)

    def test_range_ending_today_can_complete_before_midnight(self) -> None:
        today = collector.dt.datetime.now(collector.SHANGHAI_TZ).date()
        yesterday = today - collector.dt.timedelta(days=1)
        page = {
            "code": 200,
            "data": {
                "items": [
                    {
                        "title": "今天",
                        "content_url": "https://mp.weixin.qq.com/s/today",
                        "published_at": f"{today.isoformat()}T10:00:00",
                    },
                    {
                        "title": "昨天",
                        "content_url": "https://mp.weixin.qq.com/s/yesterday",
                        "published_at": f"{yesterday.isoformat()}T10:00:00",
                    },
                ],
                "last_id": "next-page",
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            args = collector.build_parser().parse_args(
                [
                    "collect-range",
                    "--wxid",
                    "gh_example",
                    "--start-date",
                    today.isoformat(),
                    "--end-date",
                    today.isoformat(),
                    "--max-pages",
                    "1",
                    "--max-articles",
                    "0",
                    "--metadata-only",
                    "--max-cost",
                    "0.05",
                    "--state-file",
                    str(Path(directory) / "index.sqlite3"),
                    "--confirm-paid",
                ]
            )
            output = io.StringIO()
            with (
                mock.patch.object(collector, "load_credentials", return_value=("app", "secret")),
                mock.patch.object(collector.CimidataClient, "call", return_value=page),
                redirect_stdout(output),
            ):
                self.assertEqual(collector.run_collect_range(args), 0)

        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "metadata_ready")
        self.assertEqual(result["article_count"], 1)


if __name__ == "__main__":
    unittest.main()
