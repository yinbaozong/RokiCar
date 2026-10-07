from pathlib import Path
import unittest
from unittest.mock import patch


class BootStartupTest(unittest.TestCase):
    def test_boot_returns_without_launching_application(self):
        boot = Path(__file__).resolve().parents[1] / "boot.py"
        source = boot.read_text(encoding="utf-8-sig")
        with patch("builtins.open", side_effect=RuntimeError("boot must return before main starts")):
            exec(compile(source, str(boot), "exec"), {})


if __name__ == "__main__":
    unittest.main()
