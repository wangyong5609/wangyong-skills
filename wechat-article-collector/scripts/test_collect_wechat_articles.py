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


class CollectorTests(unittest.TestCase):
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
            collector.write_tables(account_dir, [article], [comment])
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
            collector.write_tables(account_dir, [first, second], comments)
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
