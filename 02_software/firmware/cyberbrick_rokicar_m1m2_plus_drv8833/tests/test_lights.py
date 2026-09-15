"""Exercise the actual command handler without initializing physical motors."""
import ast
import json
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import rokicar_core


class LightTests(unittest.TestCase):
    def setUp(self):
        source = pathlib.Path(__file__).resolve().parents[1] / 'main.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'handle_command')
        self.env = dict(vars(rokicar_core))
        self.env.update(MSG_LIGHT=12, accessory_rgb=(0, 0, 0), accessory_led=Mock(),
                        state={'dropped': 0, 'last_cmd': 123}, json=json,
                        time=SimpleNamespace(ticks_ms=lambda: 456), ws_send=Mock())
        exec(compile(ast.Module(body=[handler], type_ignores=[]), str(source), 'exec'), self.env)

    def test_rgb_and_off_leave_motor_deadline_unchanged(self):
        for rgb in ((25, 80, 0), (0, 0, 0)):
            self.env['handle_command'](rokicar_core.encode_command(12, 1, *rgb))
            self.env['accessory_led'].fill.assert_called_with(rgb)
            self.assertEqual(self.env['accessory_rgb'], rgb)
            self.assertEqual(self.env['state']['last_cmd'], 123)
            self.assertEqual(json.loads(self.env['ws_send'].call_args.args[1])['light'], list(rgb))

    def test_out_of_range_does_not_write(self):
        self.env['handle_command'](rokicar_core.encode_command(12, 2, 256, -1, 0))
        self.env['accessory_led'].write.assert_not_called()
        self.assertTrue(json.loads(self.env['ws_send'].call_args.args[1])['lightError'])
