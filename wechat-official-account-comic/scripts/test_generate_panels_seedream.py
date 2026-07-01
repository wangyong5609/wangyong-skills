import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


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


if __name__ == "__main__":
    unittest.main()
