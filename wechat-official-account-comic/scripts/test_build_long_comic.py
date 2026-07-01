import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
BUILD_SCRIPT = SCRIPT_DIR / "build_long_comic.py"
TEMPLATES_DIR = SKILL_DIR / "templates"


def load_module():
    spec = importlib.util.spec_from_file_location("build_long_comic", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_panel_paths(blocks):
    paths = []
    for block in blocks:
        if isinstance(block, dict):
            if block.get("type") in {"image", "framed_image"} and block.get("path"):
                paths.append(block["path"])
            for value in block.values():
                if isinstance(value, list):
                    paths.extend(collect_panel_paths(value))
                elif isinstance(value, dict):
                    paths.extend(collect_panel_paths([value]))
    return paths


def walk_blocks(blocks):
    for block in blocks:
        if isinstance(block, dict):
            yield block
            for value in block.values():
                if isinstance(value, list):
                    yield from walk_blocks(value)
                elif isinstance(value, dict):
                    yield from walk_blocks([value])


class LayoutTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_article_templates_build_with_placeholder_panels(self):
        for template_path in sorted(TEMPLATES_DIR.glob("article-template*.json")):
            if template_path.name == "style-profile-template.json":
                continue
            with self.subTest(template=template_path.name):
                template = json.loads(template_path.read_text(encoding="utf-8"))
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_dir = Path(tmp)
                    spec_path = tmp_dir / "article.json"
                    for rel_path in set(collect_panel_paths(template.get("blocks", []))):
                        panel_path = tmp_dir / rel_path
                        panel_path.parent.mkdir(parents=True, exist_ok=True)
                        image = Image.new("RGB", (800, 600), "#f5ead9")
                        draw = ImageDraw.Draw(image)
                        draw.rectangle((32, 32, 768, 568), outline="#222222", width=6)
                        draw.text((64, 64), panel_path.name, fill="#222222")
                        image.save(panel_path)
                    spec_path.write_text(json.dumps(template, ensure_ascii=False), encoding="utf-8")
                    out_path = tmp_dir / "out.png"

                    self.module.build(spec_path, out_path)

                    self.assertTrue(out_path.exists())
                    with Image.open(out_path) as output:
                        self.assertEqual(output.width, int(template.get("canvas_width", 600)))
                        self.assertGreater(output.height, 0)

    def test_article_templates_do_not_add_in_panel_text_overlays(self):
        for template_path in sorted(TEMPLATES_DIR.glob("article-template*.json")):
            template = json.loads(template_path.read_text(encoding="utf-8"))
            with self.subTest(template=template_path.name):
                for block in walk_blocks(template.get("blocks", [])):
                    if block.get("type") in {"image", "framed_image"}:
                        self.assertNotIn("speech_bubbles", block)
                    if block.get("type") == "framed_image":
                        self.assertNotIn("header", block)

    def test_article_templates_do_not_include_article_title_blocks(self):
        for template_path in sorted(TEMPLATES_DIR.glob("article-template*.json")):
            template = json.loads(template_path.read_text(encoding="utf-8"))
            with self.subTest(template=template_path.name):
                for block in walk_blocks(template.get("blocks", [])):
                    self.assertNotEqual(block.get("type"), "title")

    def test_layout_rejects_speech_bubble_overlays(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            panel_path = tmp_dir / "panel.png"
            Image.new("RGB", (320, 240), "#ffffff").save(panel_path)
            spec_path = tmp_dir / "article.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "canvas_width": 420,
                        "blocks": [
                            {
                                "type": "image",
                                "path": "panel.png",
                                "speech_bubbles": [{"text": "后期气泡"}],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "speech_bubbles"):
                self.module.build(spec_path, tmp_dir / "out.png")

    def test_layout_rejects_framed_image_header_overlays(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            panel_path = tmp_dir / "panel.png"
            Image.new("RGB", (320, 240), "#ffffff").save(panel_path)
            spec_path = tmp_dir / "article.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "canvas_width": 420,
                        "blocks": [
                            {
                                "type": "framed_image",
                                "path": "panel.png",
                                "header": "后期标题条",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "framed_image.header"):
                self.module.build(spec_path, tmp_dir / "out.png")

    def test_layout_rejects_article_title_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            spec_path = tmp_dir / "article.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "canvas_width": 420,
                        "blocks": [
                            {
                                "type": "title",
                                "text": "公众号文章标题不要进长图",
                            },
                            {
                                "type": "paragraph",
                                "text": "从正文第一句开始。",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "article title"):
                self.module.build(spec_path, tmp_dir / "out.png")


if __name__ == "__main__":
    unittest.main()
