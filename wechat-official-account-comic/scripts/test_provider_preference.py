import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("provider_preference.py")
SPEC = importlib.util.spec_from_file_location("provider_preference", MODULE_PATH)
provider_preference = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(provider_preference)


class ProviderPreferenceTests(unittest.TestCase):
    def test_missing_preference_returns_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preference.json"
            self.assertIsNone(provider_preference.load_preference(path))

    def test_save_and_load_preference(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nested" / "preference.json"
            saved = provider_preference.save_preference(path, "codex-imagegen")
            loaded = provider_preference.load_preference(path)
            self.assertEqual(saved["provider"], "codex-imagegen")
            self.assertEqual(loaded["provider"], "codex-imagegen")
            self.assertEqual(json.loads(path.read_text())["version"], 1)

    def test_chinese_and_legacy_aliases_are_normalized(self):
        self.assertEqual(provider_preference.normalize_provider("破局问问"), "pojuwenwen")
        self.assertEqual(provider_preference.normalize_provider("breakout"), "pojuwenwen")

    def test_invalid_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            provider_preference.normalize_provider("unknown")

    def test_explicit_store_overrides_runtime_path(self):
        expected = Path("/tmp/provider-preference-test.json")
        actual = provider_preference.preference_path("codex", str(expected))
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
