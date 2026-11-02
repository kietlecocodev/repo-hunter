import json
import os
import tempfile
import unittest

from _path import *  # noqa: F401,F403
from rh.config import DEFAULTS, load_config


class ConfigTest(unittest.TestCase):
    def test_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_config(d), DEFAULTS)

    def test_nested_override_keeps_other_keys(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"threshold": 300, "weights": {"dev": 0.8}}, f)
            cfg = load_config(d)
            self.assertEqual(cfg["threshold"], 300)
            self.assertEqual(cfg["weights"], {"product": 1.5, "design": 1.2, "dev": 0.8})
            self.assertEqual(cfg["cooldown_days"], 14)

    def test_defaults_not_mutated(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"weights": {"dev": 0.1}}, f)
            load_config(d)
            self.assertEqual(DEFAULTS["weights"]["dev"], 1.0)


if __name__ == "__main__":
    unittest.main()
