from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("collect_wechat_articles.py")
SPEC = importlib.util.spec_from_file_location("collect_wechat_articles", MODULE_PATH)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = collector
SPEC.loader.exec_module(collector)


class FakeResponse:
    def __init__(self, data: bytes, content_type: str = "image/jpeg") -> None:
        self.data = data
        self.headers = {"Content-Type": content_type}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback

    def read(self) -> bytes:
        return self.data


class FakeCommentClient:
    def __init__(self) -> None:
        self.buffers: list[str] = []

    def comments(self, article_url: str, buffer: str):
        self.buffers.append(buffer)
        if not buffer:
            return {
                "code": 0,
                "total": 2,
                "buffer": "next-page",
                "data": [
                    {
                        "content_id": "one",
                        "content": "第一条",
                        "like_num": 3,
                        "is_top": 1,
                        "province_name": "广东",
                        "nick_name": "不应输出",
                        "new_reply_list": [{"content": "不应输出回复"}],
                    }
                ],
            }
        return {
            "code": 0,
            "total": 2,
            "buffer": "",
            "data": [
                {
                    "content_id": "two",
                    "content": "第二条",
                    "like_num": 0,
                    "is_top": 0,
                    "province_name": "四川",
                    "logo_url": "不应输出",
                }
            ],
        }


class FakeCollectorClient:
    def __init__(self) -> None:
        self.comment_calls = 0

    def history(self, account: str, *, offset: str = "", ghid: str = "", url: str = ""):
        del account, offset, ghid, url
        return {
            "code": 0,
            "is_end": 1,
            "data": [
                {
                    "url": "https://mp.weixin.qq.com/s/example",
                    "title": "示例文章",
                    "post_time": "2026-08-05 10:00:00",
                }
            ],
        }

    def article_html(self, article_url: str):
        del article_url
        return {"code": 0, "data": {"title": "示例文章", "nickname": "示例账号", "html": "<p>正文</p>"}}

    def metrics(self, article_url: str):
        del article_url
        return {
            "code": 0,
            "data": {"read": 1, "zan": 2, "looking": 3, "share_num": 4, "collect_num": 5, "comment_count": 6},
        }

    def comments(self, article_url: str, buffer: str):
        del article_url, buffer
        self.comment_calls += 1
        return {"code": 0, "data": [], "total": 0, "buffer": ""}


class CollectorTests(unittest.TestCase):
    def test_api_request_does_not_send_cookie_header(self) -> None:
        client = collector.DajialaClient(api_key="secret", verifycode="verify")
        with mock.patch.object(
            collector.urllib.request,
            "urlopen",
            return_value=FakeResponse(b'{"code": 0}'),
        ) as urlopen:
            response = client.request_json("POST", "/test", body={"key": "secret", "verifycode": "verify"})

        self.assertEqual(response["code"], 0)
        request = urlopen.call_args.args[0]
        self.assertNotIn("Cookie", request.headers)

    def test_history_uses_current_nickname_and_offset_contract(self) -> None:
        client = collector.DajialaClient(api_key="secret", verifycode="verify")
        with mock.patch.object(client, "request_json", return_value={"code": 0}) as request_json:
            client.history("示例账号", offset="cursor-2")

        body = request_json.call_args.kwargs["body"]
        self.assertEqual(body["nickname"], "示例账号")
        self.assertEqual(body["offset"], "cursor-2")
        self.assertNotIn("name", body)
        self.assertNotIn("page", body)

        with mock.patch.object(client, "request_json", return_value={"code": 0}) as request_json:
            client.history("", ghid="gh_example")
        ghid_body = request_json.call_args.kwargs["body"]
        self.assertEqual(ghid_body["ghid"], "gh_example")
        self.assertNotIn("nickname", ghid_body)

    def test_pick_metrics_maps_official_pro_fields(self) -> None:
        metrics = collector.pick_metrics(
            {
                "code": 0,
                "data": {
                    "read": 101,
                    "zan": 12,
                    "looking": 13,
                    "share_num": 14,
                    "collect_num": 15,
                    "comment_count": -1,
                },
            }
        )
        self.assertEqual(
            metrics,
            {"read": 101, "like": 12, "looking": 13, "share": 14, "collect": 15, "comment_count": -1},
        )

    def test_write_tables_skips_comments_by_default(self) -> None:
        article = {key: "" for key in collector.ARTICLE_FIELDS}
        article.update({"title": "不采评论", "article_url": "https://example/article"})
        comment = {
            "article_url": article["article_url"],
            "content": "不应被写入",
            "like_num": 1,
            "is_top": 0,
            "province_name": "广东",
        }
        with tempfile.TemporaryDirectory() as directory:
            account_dir = Path(directory)
            collector.write_tables(account_dir, [article], [comment])
            self.assertTrue((account_dir / "文章数据.csv").exists())
            self.assertFalse((account_dir / "评论").exists())

    def test_parser_comments_are_opt_in(self) -> None:
        args = collector.build_parser().parse_args(["--account", "示例账号"])
        self.assertFalse(args.include_comments)
        enabled = collector.build_parser().parse_args(["--account", "示例账号", "--include-comments"])
        self.assertTrue(enabled.include_comments)

    def test_collect_calls_comment_api_only_when_enabled(self) -> None:
        for include_comments in (False, True):
            with self.subTest(include_comments=include_comments), tempfile.TemporaryDirectory() as directory:
                fake_client = FakeCollectorClient()
                args_list = [
                    "--account",
                    "示例账号",
                    "--api-key",
                    "test-key",
                    "--output-dir",
                    directory,
                    "--limit",
                    "1",
                    "--delay",
                    "0",
                ]
                if include_comments:
                    args_list.append("--include-comments")
                args = collector.build_parser().parse_args(args_list)
                localizer = mock.Mock(downloaded=0, failures=[], skipped_gifs=0)
                with mock.patch.object(collector, "DajialaClient", return_value=fake_client), mock.patch.object(
                    collector, "write_article", return_value=(Path(directory) / "article.md", localizer)
                ), mock.patch.object(collector, "write_tables") as write_tables:
                    self.assertEqual(collector.collect(args), 0)

                self.assertEqual(fake_client.comment_calls, int(include_comments))
                self.assertEqual(write_tables.call_args.kwargs["include_comments"], include_comments)

    def test_transient_api_response_retries_with_backoff(self) -> None:
        client = collector.DajialaClient(api_key="secret", api_retries=2, retry_backoff=2)
        with mock.patch.object(
            client,
            "request_json",
            side_effect=[{"code": 106, "msg": "too fast"}, {"code": 0, "data": {"read": 1}}],
        ), mock.patch.object(collector.time, "sleep") as sleep:
            response = client.metrics("https://mp.weixin.qq.com/s/example")

        self.assertEqual(response["code"], 0)
        sleep.assert_called_once_with(2)

    def test_static_images_are_local_and_gifs_are_skipped(self) -> None:
        jpeg = b"\xff\xd8\xff" + b"same-image-data"
        with tempfile.TemporaryDirectory() as directory:
            account_dir = Path(directory)
            localizer = collector.ImageLocalizer(
                asset_dir=account_dir / "assets" / "article",
                relative_asset_dir=Path("assets") / "article",
                referer="https://mp.weixin.qq.com/s/example",
            )
            source = """
            <html><head><style>ignored css</style></head><body>
            <p>正文内容</p>
            <img data-src="//img.example/a?wx_fmt=jpeg">
            <img src="https://img.example/b.png">
            <img data-type="gif" src="https://img.example/animation">
            </body></html>
            """
            with mock.patch.object(
                collector.urllib.request,
                "urlopen",
                side_effect=[FakeResponse(jpeg), FakeResponse(jpeg)],
            ) as urlopen:
                markdown = collector.html_to_markdown(source, localizer.resolve)

            self.assertEqual(urlopen.call_count, 2)
            self.assertEqual(localizer.downloaded, 1)
            self.assertEqual(localizer.skipped_gifs, 1)
            self.assertNotIn("gif", markdown.lower())
            self.assertNotIn("https://img.example", markdown)
            self.assertEqual(markdown.count("assets/article/001.jpg"), 2)
            self.assertEqual(len(list((account_dir / "assets" / "article").glob("*"))), 1)
            self.assertEqual(collector.html_to_text(source), "正文内容")

    def test_existing_assets_survive_article_render_failure(self) -> None:
        article = {
            "title": "示例文章",
            "date": "2026-07-11",
            "account": "示例账号",
            "author": "",
            "article_url": "https://mp.weixin.qq.com/s/example",
            "publish_time": "2026-07-11 10:00:00",
            "digest": "",
            "read": 1,
            "like": 2,
            "looking": 3,
            "share": 4,
            "collect": 5,
            "comment_count": 6,
            "content": "正文",
            "_html": '<img src="https://img.example/new.jpg">',
            "_cover_url": "",
        }
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            asset_dir = output_dir / "示例账号" / "assets" / "2026-07-11-示例文章"
            asset_dir.mkdir(parents=True)
            old_asset = asset_dir / "old.jpg"
            old_asset.write_bytes(b"old")
            with mock.patch.object(collector, "html_to_markdown", side_effect=RuntimeError("render failed")):
                with self.assertRaises(RuntimeError):
                    collector.write_article(output_dir, article, timeout=1)
            self.assertEqual(old_asset.read_bytes(), b"old")

    def test_first_level_comments_paginate_and_project_exact_fields(self) -> None:
        client = FakeCommentClient()
        comments = collector.collect_first_level_comments(client, "https://mp.weixin.qq.com/s/example")
        self.assertEqual(client.buffers, ["", "next-page"])
        self.assertEqual(len(comments), 2)
        self.assertEqual(set(comments[0]), set(collector.COMMENT_FIELDS))
        self.assertNotIn("nick_name", comments[0])
        self.assertNotIn("new_reply_list", comments[0])

    def test_csv_headers_are_exact(self) -> None:
        article = {key: f"article-{key}" for key in collector.ARTICLE_FIELDS}
        comment = {key: f"comment-{key}" for key in collector.COMMENT_FIELDS}
        article["publish_time"] = "2026-07-11 10:00:00"
        comment["article_url"] = article["article_url"]
        with tempfile.TemporaryDirectory() as directory:
            account_dir = Path(directory)
            (account_dir / "评论数据.csv").write_text("旧汇总文件", encoding="utf-8")
            collector.write_tables(account_dir, [article], [comment], include_comments=True)
            with (account_dir / "文章数据.csv").open(encoding="utf-8-sig", newline="") as file:
                article_rows = list(csv.DictReader(file))
            comment_path = account_dir / "评论" / f"{article['title']}.csv"
            with comment_path.open(encoding="utf-8-sig", newline="") as file:
                comment_rows = list(csv.DictReader(file))

            self.assertEqual(list(article_rows[0]), collector.ARTICLE_FIELDS)
            self.assertEqual(list(comment_rows[0]), collector.COMMENT_FIELDS)
            self.assertEqual(set(article_rows[0]), set(collector.ARTICLE_FIELDS))
            self.assertEqual(set(comment_rows[0]), set(collector.COMMENT_FIELDS))
            self.assertFalse((account_dir / "评论数据.csv").exists())

    def test_each_article_gets_its_own_named_comment_file(self) -> None:
        first = {key: "" for key in collector.ARTICLE_FIELDS}
        first.update({"title": "第一篇文章", "article_url": "https://example/one", "publish_time": "2026-07-11"})
        second = {key: "" for key in collector.ARTICLE_FIELDS}
        second.update({"title": "第二篇文章", "article_url": "https://example/two", "publish_time": "2026-07-10"})
        comments = [
            {
                "article_url": "https://example/two",
                "content": "第二篇的评论",
                "like_num": 1,
                "is_top": 0,
                "province_name": "广东",
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            account_dir = Path(directory)
            collector.write_tables(account_dir, [first, second], comments, include_comments=True)
            first_path = account_dir / "评论" / "第一篇文章.csv"
            second_path = account_dir / "评论" / "第二篇文章.csv"
            self.assertTrue(first_path.exists())
            self.assertTrue(second_path.exists())
            with first_path.open(encoding="utf-8-sig", newline="") as file:
                self.assertEqual(len(list(csv.DictReader(file))), 0)
            with second_path.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[0]["content"], "第二篇的评论")

    def test_image_failure_keeps_remote_reference_and_records_partial_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            account_dir = Path(directory)
            localizer = collector.ImageLocalizer(
                asset_dir=account_dir / "assets" / "article",
                relative_asset_dir=Path("assets") / "article",
                referer="https://mp.weixin.qq.com/s/example",
            )
            with mock.patch.object(collector.urllib.request, "urlopen", side_effect=OSError("offline")), mock.patch.object(
                collector.time, "sleep"
            ):
                result = localizer.resolve("https://img.example/missing.jpg", {})

            self.assertEqual(result, "https://img.example/missing.jpg")
            self.assertEqual(len(localizer.failures), 1)
            self.assertEqual(localizer.downloaded, 0)


if __name__ == "__main__":
    unittest.main()
