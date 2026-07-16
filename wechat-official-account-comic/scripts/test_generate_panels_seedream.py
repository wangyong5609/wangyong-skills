import base64
import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPT_PATH = Path(__file__).with_name("generate_panels_seedream.py")
LEGACY_STYLE_NAMES = {
    "\u98ce\u683c\u4e00",
    "\u98ce\u683c\u4e8c",
    "\u98ce\u683c\u4e09",
    "\u767d\u5e95\u79d1\u666e\u6f2b\u753b",
    "\u84dd\u6761\u5fc3\u7406\u53d9\u4e8b",
    "\u7eff\u5e95\u804c\u573a\u5bf9\u6bd4",
}


def load_module():
    spec = importlib.util.spec_from_file_location("generate_panels_seedream", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PromptWrappingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_no_production_style_prompt_table_in_script(self):
        self.assertFalse(hasattr(self.module, "STYLE_PROMPTS"))
        self.assertFalse(hasattr(self.module, "BUILTIN_TEXT_POLICIES"))

    def test_generation_script_does_not_branch_on_named_styles(self):
        source = SCRIPT_PATH.read_text(encoding="utf-8")

        for literal in ["暖白手绘漫画", "蓝栏柔彩漫画", "绿底粗线漫画", "小林生活讽刺", "小林诗意治愈", "小林奇想涂鸦"]:
            with self.subTest(literal=literal):
                self.assertNotIn(literal, source)

    def test_empty_style_resolves_from_default_profile(self):
        styles_dir = SCRIPT_PATH.parents[1] / "styles"

        style_name, style_prompt, text_policy, style_source = self.module.resolve_style_settings(
            "",
            "",
            styles_dir,
        )

        self.assertEqual(style_name, "暖白手绘漫画")
        self.assertTrue(style_prompt)
        self.assertEqual(text_policy, "wordless")
        self.assertTrue(style_source.endswith("warm-white-handdrawn.json"))

    def test_default_styles_resolve_from_style_profiles(self):
        styles_dir = SCRIPT_PATH.parents[1] / "styles"

        expected = {
            "暖白手绘漫画": "warm-white-handdrawn.json",
            "蓝栏柔彩漫画": "blue-bar-soft-color.json",
            "绿底粗线漫画": "green-bold-line.json",
        }
        for style, source_name in expected.items():
            with self.subTest(style=style):
                style_name, style_prompt, text_policy, style_source = self.module.resolve_style_settings(
                    style,
                    "",
                    styles_dir,
                )

                self.assertEqual(style_name, style)
                self.assertTrue(style_prompt)
                self.assertIn(text_policy, {"wordless", "model-rendered"})
                self.assertTrue(style_source.endswith(source_name))

        self.assertTrue(LEGACY_STYLE_NAMES.isdisjoint(expected))

    def test_green_bold_line_keeps_workplace_prompt_wrapper(self):
        prompt = '黑色标题条写"上班第一年"，人物在加班'

        full_prompt = self.module.build_full_prompt(
            "绿底粗线漫画",
            prompt,
            "粗黑线条，职场公众号漫画风格",
            "model-rendered",
        )

        self.assertIn("根据风格 profile", full_prompt)
        self.assertIn("职场公众号漫画风格", full_prompt)
        self.assertIn('"上班第一年"', full_prompt)

    def test_trained_model_rendered_style_uses_generic_prompt_wrapper(self):
        prompt = '红色标签写"春天来了"，手绘植物贴纸'

        full_prompt = self.module.build_full_prompt(
            "手帐贴纸风格",
            prompt,
            "松弛手帐贴纸风格，透明水彩，圆角标签",
            "model-rendered",
        )

        self.assertIn("只有场景提示中被引号包住的文字可以写进画面", full_prompt)
        self.assertIn('"春天来了"', full_prompt)
        self.assertNotIn("职场", full_prompt)

    def test_xiaolin_trained_style_uses_source_image_prompt_wrapper(self):
        prompt = '夸张的中年人坐在沙发上，Text to render exactly: "当我累了" "我只想安静一会"'

        full_prompt = self.module.build_full_prompt(
            "小林生活讽刺",
            prompt,
            "白底水彩人物小品，黑色手写中文 caption",
            "model-rendered",
        )

        self.assertIn("根据风格 profile", full_prompt)
        self.assertIn("白底水彩人物小品", full_prompt)
        self.assertIn('"当我累了"', full_prompt)

    def test_image_edit_prompt_preserves_reference_text_without_wordless_wrapper(self):
        prompt = "把人物加入封面右侧，保留封面的核心中文标题"

        edit_prompt = self.module.build_image_edit_prompt(prompt, "wordless")

        self.assertIn("Preserve readable text", edit_prompt)
        self.assertIn(prompt, edit_prompt)
        self.assertNotIn("Create a wordless illustration only", edit_prompt)
        self.assertNotIn("Style and constraints", edit_prompt)

    def test_xiaolin_life_satire_profile_alias_resolves(self):
        styles_dir = SCRIPT_PATH.parents[1] / "styles"

        style_name, style_prompt, text_policy, style_source = self.module.resolve_style_settings(
            "小林风格2",
            "",
            styles_dir,
        )

        self.assertEqual(style_name, "小林生活讽刺")
        self.assertIn("watercolor caricature", style_prompt)
        self.assertEqual(text_policy, "model-rendered")
        self.assertTrue(style_source.endswith("xiaolin-life-satire.json"))

    def test_xiaolin_poetic_healing_profile_alias_resolves(self):
        styles_dir = SCRIPT_PATH.parents[1] / "styles"

        style_name, style_prompt, text_policy, style_source = self.module.resolve_style_settings(
            "小林诗意治愈",
            "",
            styles_dir,
        )

        self.assertEqual(style_name, "小林诗意治愈")
        self.assertIn("quiet healing watercolor", style_prompt)
        self.assertEqual(text_policy, "model-rendered")
        self.assertTrue(style_source.endswith("xiaolin-healing.json"))

    def test_xiaolin_whimsy_doodle_profile_alias_resolves(self):
        styles_dir = SCRIPT_PATH.parents[1] / "styles"

        style_name, style_prompt, text_policy, style_source = self.module.resolve_style_settings(
            "小林漫画3",
            "",
            styles_dir,
        )

        self.assertEqual(style_name, "小林奇想涂鸦")
        self.assertIn("whimsical watercolor doodle", style_prompt)
        self.assertEqual(text_policy, "model-rendered")
        self.assertTrue(style_source.endswith("xiaolin-whimsy-doodle.json"))


class ImageProviderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_default_provider_is_agnes(self):
        config = self.module.resolve_provider_config("agnes", "", "", "")

        self.assertEqual(config["provider"], "agnes")
        self.assertEqual(config["api_url"], self.module.DEFAULT_AGNES_API_URL)
        self.assertEqual(config["model"], self.module.DEFAULT_AGNES_MODEL)
        self.assertEqual(config["api_key_envs"], ["AGNES_API_KEY", "GNES_API_KEY", "AGNESAI_API_KEY"])

    def test_agnes_api_key_takes_priority_over_seedream_keys(self):
        config = self.module.resolve_provider_config("agnes", "", "", "")

        with patch.dict(os.environ, {"AGNES_API_KEY": "agnes-key", "DOUBAO_API_KEY": "doubao-key"}, clear=True):
            api_key, api_key_env = self.module.resolve_api_key(config["api_key_envs"])

        self.assertEqual(api_key, "agnes-key")
        self.assertEqual(api_key_env, "AGNES_API_KEY")

    def test_gnes_alias_is_accepted_for_agnes_api_key(self):
        config = self.module.resolve_provider_config("gnes", "", "", "")

        with patch.dict(os.environ, {"GNES_API_KEY": "gnes-key"}, clear=True):
            api_key, api_key_env = self.module.resolve_api_key(config["api_key_envs"])

        self.assertEqual(config["provider"], "agnes")
        self.assertEqual(api_key, "gnes-key")
        self.assertEqual(api_key_env, "GNES_API_KEY")

    def test_breakout_provider_uses_verified_defaults_and_key_name(self):
        config = self.module.resolve_provider_config("breakout", "", "", "")

        self.assertEqual(config["provider"], "breakout")
        self.assertEqual(config["api_url"], self.module.DEFAULT_BREAKOUT_API_URL)
        self.assertEqual(config["edit_api_url"], self.module.DEFAULT_BREAKOUT_EDIT_API_URL)
        self.assertEqual(config["model"], "gpt-image-2")
        self.assertEqual(config["api_key_envs"], ["BREAKOUT_API_KEY"])

    def test_pojuwenwen_name_and_default_concurrency_are_supported(self):
        config = self.module.resolve_provider_config("破局问问", "", "", "")

        self.assertEqual(config["provider"], "breakout")
        self.assertEqual(config["label"], "破局问问 GPT Image")
        self.assertEqual(self.module.resolve_worker_count("破局问问"), 2)
        self.assertEqual(self.module.resolve_worker_count("pojuwenwen"), 2)
        self.assertEqual(self.module.resolve_worker_count("agnes"), 1)
        self.assertEqual(self.module.resolve_worker_count("破局问问", 3), 3)

    def test_bounded_jobs_run_at_most_two_panels_concurrently(self):
        lock = threading.Lock()
        state = {"active": 0, "peak": 0}

        def worker(job):
            with lock:
                state["active"] += 1
                state["peak"] = max(state["peak"], state["active"])
            self.module.time.sleep(0.02)
            with lock:
                state["active"] -= 1
            return job

        results, failures, submitted = self.module.run_bounded_jobs(range(4), 2, worker)

        self.assertEqual(sorted(results), [0, 1, 2, 3])
        self.assertEqual(failures, [])
        self.assertEqual(submitted, 4)
        self.assertEqual(state["peak"], 2)

    def test_bounded_jobs_stop_submitting_after_first_failure(self):
        second_started = threading.Event()

        def worker(job):
            if job == 1:
                second_started.wait(timeout=1)
                raise RuntimeError("panel failed")
            if job == 2:
                second_started.set()
                self.module.time.sleep(0.05)
            return job

        results, failures, submitted = self.module.run_bounded_jobs([1, 2, 3, 4], 2, worker)

        self.assertEqual(results, [2])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][0], 1)
        self.assertEqual(submitted, 2)

    def test_breakout_api_key_is_isolated_from_other_provider_keys(self):
        config = self.module.resolve_provider_config("breakout", "", "", "")

        with patch.dict(os.environ, {"BREAKOUT_API_KEY": "breakout-key", "AGNES_API_KEY": "agnes-key"}, clear=True):
            api_key, api_key_env = self.module.resolve_api_key(config["api_key_envs"])

        self.assertEqual(api_key, "breakout-key")
        self.assertEqual(api_key_env, "BREAKOUT_API_KEY")

    def test_agnes_payload_uses_extra_body_for_response_format(self):
        payload = self.module.build_api_payload(
            "agnes",
            "agnes-image-2.0-flash",
            "画一张公众号漫画分镜",
            "1024x768",
            "url",
            False,
        )

        self.assertEqual(payload["model"], "agnes-image-2.0-flash")
        self.assertEqual(payload["extra_body"]["response_format"], "url")
        self.assertNotIn("response_format", payload)
        self.assertNotIn("watermark", payload)

    def test_seedream_payload_keeps_seedream_specific_fields(self):
        payload = self.module.build_api_payload(
            "seedream",
            "doubao-seedream-4-5-251128",
            "画一张公众号漫画分镜",
            "2304x1728",
            "b64_json",
            True,
        )

        self.assertEqual(payload["response_format"], "b64_json")
        self.assertTrue(payload["watermark"])
        self.assertEqual(payload["sequential_image_generation"], "disabled")

    def test_breakout_text_to_image_payload_uses_native_images_schema(self):
        payload = self.module.build_api_payload(
            "breakout",
            "gpt-image-2",
            "画一张公众号漫画分镜",
            "1536x1024",
            "b64_json",
            False,
        )

        self.assertEqual(
            payload,
            {
                "model": "gpt-image-2",
                "prompt": "画一张公众号漫画分镜",
                "size": "1536x1024",
            },
        )

    def test_breakout_image_edit_encodes_repeated_image_file_parts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            first = Path(tmp_dir) / "cover.png"
            second = Path(tmp_dir) / "person.png"
            first.write_bytes(b"cover-bytes")
            second.write_bytes(b"person-bytes")

            body, content_type = self.module.encode_multipart_form(
                {"model": "gpt-image-2", "prompt": "把人物加到封面", "quality": "low"},
                "image",
                [first, second],
            )

        self.assertTrue(content_type.startswith("multipart/form-data; boundary="))
        self.assertEqual(body.count(b'name="image"; filename="'), 2)
        self.assertIn(b'filename="cover.png"', body)
        self.assertIn(b'filename="person.png"', body)
        self.assertIn(b"cover-bytes", body)
        self.assertIn(b"person-bytes", body)

    def test_gateway_timeouts_are_retryable_but_other_client_errors_are_not(self):
        self.assertTrue(self.module.ImageRequestError("timeout", 504).retryable)
        self.assertTrue(self.module.ImageRequestError("overloaded", 503).retryable)
        self.assertFalse(self.module.ImageRequestError("bad request", 400).retryable)

    def test_explicit_retry_retries_a_gateway_timeout_once(self):
        expected = {"data": [{"b64_json": "abc"}]}

        with patch.object(
            self.module,
            "request_image",
            side_effect=[self.module.ImageRequestError("timeout", 504), expected],
        ) as request_image, patch.object(self.module.time, "sleep") as sleep:
            result = self.module.request_image_with_retries("breakout", retries=1, retry_delay=12)

        self.assertEqual(result, expected)
        self.assertEqual(request_image.call_count, 2)
        sleep.assert_called_once_with(12)

    def test_request_id_prefers_standard_header(self):
        self.assertEqual(
            self.module.get_request_id({"x-oneapi-request-id": "fallback", "x-request-id": "primary"}),
            "primary",
        )

    def test_download_host_matching_allows_only_api_host_and_subdomains(self):
        self.assertTrue(
            self.module.download_hosts_match(
                "https://breakout.wenwen-ai.com/files/panel.png",
                "https://breakout.wenwen-ai.com/v1/images/generations",
            )
        )
        self.assertTrue(
            self.module.download_hosts_match(
                "https://img.breakout.wenwen-ai.com/files/panel.png",
                "https://breakout.wenwen-ai.com/v1/images/generations",
            )
        )
        self.assertFalse(
            self.module.download_hosts_match(
                "https://example-cdn.invalid/files/panel.png",
                "https://breakout.wenwen-ai.com/v1/images/generations",
            )
        )

    def test_same_host_download_retries_403_with_authorization(self):
        first_error = urllib.error.HTTPError(
            "https://breakout.wenwen-ai.com/files/panel.png",
            403,
            "Forbidden",
            None,
            None,
        )
        self.addCleanup(first_error.close)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"image-bytes"
        opener = MagicMock()
        opener.open.side_effect = [first_error, response]

        with patch.object(self.module.urllib.request, "build_opener", return_value=opener):
            result = self.module.download_image_url(
                "https://breakout.wenwen-ai.com/files/panel.png",
                30,
                "secret-key",
                "https://breakout.wenwen-ai.com/v1/images/generations",
            )

        self.assertEqual(result, b"image-bytes")
        self.assertEqual(opener.open.call_count, 2)
        first_request = opener.open.call_args_list[0].args[0]
        second_request = opener.open.call_args_list[1].args[0]
        self.assertIsNone(first_request.get_header("Authorization"))
        self.assertEqual(second_request.get_header("Authorization"), "Bearer secret-key")
        self.assertTrue(first_request.get_header("User-agent"))

    def test_cross_host_download_never_forwards_api_key(self):
        download_error = urllib.error.HTTPError(
            "https://example-cdn.invalid/files/panel.png",
            403,
            "Forbidden",
            None,
            None,
        )
        self.addCleanup(download_error.close)
        opener = MagicMock()
        opener.open.side_effect = download_error
        with patch.object(self.module.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(self.module.ImageDownloadError) as caught:
                self.module.download_image_url(
                    "https://example-cdn.invalid/files/panel.png",
                    30,
                    "secret-key",
                    "https://breakout.wenwen-ai.com/v1/images/generations",
                )

        self.assertEqual(opener.open.call_count, 1)
        request = opener.open.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))
        self.assertIn("API key was not forwarded", str(caught.exception))

    def test_cross_host_redirect_strips_authorization(self):
        handler = self.module.SafeDownloadRedirectHandler(
            "https://breakout.wenwen-ai.com/v1/images/generations"
        )
        original = self.module.urllib.request.Request(
            "https://breakout.wenwen-ai.com/files/panel.png",
            headers={"Authorization": "Bearer secret-key"},
        )

        redirected = handler.redirect_request(
            original,
            None,
            302,
            "Found",
            {},
            "https://example-cdn.invalid/files/panel.png",
        )

        self.assertIsNotNone(redirected)
        self.assertIsNone(redirected.get_header("Authorization"))

    def test_pending_response_is_private_and_loadable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pending = Path(tmp_dir) / "panel-02-pending-response.json"
            payload = {"data": [{"url": "https://example.invalid/panel.png"}]}

            self.module.write_pending_response(pending, payload)
            loaded, item = self.module.load_pending_response(pending)

            self.assertEqual(loaded, payload)
            self.assertEqual(item, payload["data"][0])
            self.assertEqual(pending.stat().st_mode & 0o777, 0o600)

    def test_main_recovers_pending_response_without_new_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompts = root / "prompts.json"
            out_dir = root / "panels"
            out_dir.mkdir()
            prompts.write_text(json.dumps({"prompts": ["draw one panel"]}), encoding="utf-8")
            pending = out_dir / "panel-01-pending-response.json"
            pending.write_text(
                json.dumps({"data": [{"b64_json": base64.b64encode(b"image-bytes").decode("ascii")}]}),
                encoding="utf-8",
            )

            argv = [
                str(SCRIPT_PATH),
                "--provider",
                "breakout",
                "--prompts",
                str(prompts),
                "--out-dir",
                str(out_dir),
                "--style",
                "暖白手绘漫画",
            ]
            with patch.dict(os.environ, {"BREAKOUT_API_KEY": "test-key"}, clear=True), patch.object(
                sys, "argv", argv
            ), patch.object(self.module, "request_image_with_retries") as request_image:
                exit_code = self.module.main()

            self.assertEqual(exit_code, 0)
            request_image.assert_not_called()
            self.assertEqual((out_dir / "panel-01.png").read_bytes(), b"image-bytes")
            self.assertFalse(pending.exists())

    def test_main_uses_two_workers_and_records_timings_for_pojuwenwen(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompts = root / "prompts.json"
            out_dir = root / "panels"
            prompts.write_text(
                json.dumps({"prompts": ["panel one", "panel two", "panel three", "panel four"]}),
                encoding="utf-8",
            )
            lock = threading.Lock()
            state = {"active": 0, "peak": 0}

            def fake_request(*args, **kwargs):
                with lock:
                    state["active"] += 1
                    state["peak"] = max(state["peak"], state["active"])
                self.module.time.sleep(0.02)
                with lock:
                    state["active"] -= 1
                return {"data": [{"b64_json": base64.b64encode(b"image-bytes").decode("ascii")}]}

            argv = [
                str(SCRIPT_PATH),
                "--provider",
                "破局问问",
                "--prompts",
                str(prompts),
                "--out-dir",
                str(out_dir),
                "--style",
                "暖白手绘漫画",
            ]
            with patch.dict(os.environ, {"BREAKOUT_API_KEY": "test-key"}, clear=True), patch.object(
                sys, "argv", argv
            ), patch.object(self.module, "request_image_with_retries", side_effect=fake_request):
                exit_code = self.module.main()

            manifest = json.loads((out_dir / "breakout-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(state["peak"], 2)
            self.assertEqual(manifest["provider_label"], "破局问问 GPT Image")
            self.assertEqual(manifest["workers"], 2)
            self.assertEqual(manifest["submitted_generations"], 4)
            self.assertGreater(manifest["elapsed_seconds"], 0)
            self.assertEqual([item["index"] for item in manifest["panels"]], [1, 2, 3, 4])
            self.assertTrue(all(item["duration_seconds"] > 0 for item in manifest["panels"]))


if __name__ == "__main__":
    unittest.main()
