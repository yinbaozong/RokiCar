import sys
import unittest
from pathlib import Path

FIRMWARE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIRMWARE))

from omni_core import (
    GAIN_MAX,
    MSG_DRIVE,
    MSG_MOTOR_MODEL,
    MSG_MOTOR_TEST,
    MSG_QUERY_CONFIG,
    SquareRunner,
    decode_command,
    encode_command,
    gains_as_float,
    is_newer_sequence,
    linearize_motor_command,
    normalize_wheels,
    validate_wheel_map,
    validate_wheel_test,
    validate_gains,
)


class OmniCoreTests(unittest.TestCase):
    def test_forward_uses_the_two_front_wheels_equally(self):
        w1, w2, w3 = normalize_wheels(0, 1, 0, 0.75, (1, 1, 1))
        self.assertAlmostEqual(w1, -w2, places=6)
        self.assertAlmostEqual(w3, 0, places=6)

    def test_gain_is_normalized_with_other_wheels(self):
        wheels = normalize_wheels(1, 0, 0, 0.75, (1.3, 1.0, 1.0))
        self.assertLessEqual(max(abs(value) for value in wheels), 1.0)
        self.assertAlmostEqual(wheels[2], 1.0, places=6)

    def test_invalid_gains_restore_safe_defaults(self):
        self.assertEqual(validate_gains((700, 1000, GAIN_MAX)), (700, 1000, GAIN_MAX))
        self.assertEqual(validate_gains((699, 1000, 1000)), (1000, 1000, 1000))
        self.assertEqual(gains_as_float((1000, 1100, 900)), (1.0, 1.1, 0.9))

    def test_wheel_map_requires_every_physical_port_once(self):
        self.assertEqual(validate_wheel_map((1, -2, 3)), (1, -2, 3))
        self.assertEqual(validate_wheel_map((1, 1, 3)), (1, 2, 3))
        self.assertEqual(validate_wheel_map((0, 2, 3)), (1, 2, 3))

    def test_wheel_test_accepts_five_seconds_and_clamps_speed(self):
        self.assertEqual(validate_wheel_test(3, 500, 5000), (2, 300, 5000))
        self.assertIsNone(validate_wheel_test(4, 200, 5000))
        self.assertIsNone(validate_wheel_test(1, 200, 5001))

    def test_positive_rotation_is_right_turn(self):
        left = normalize_wheels(0, 0, -1, 0.75, (1, 1, 1))
        right = normalize_wheels(0, 0, 1, 0.75, (1, 1, 1))
        self.assertEqual(tuple(-value for value in left), right)

    def test_sequence_rejects_replayed_commands_and_accepts_wrap(self):
        self.assertTrue(is_newer_sequence(1, None))
        self.assertTrue(is_newer_sequence(11, 10))
        self.assertFalse(is_newer_sequence(10, 10))
        self.assertFalse(is_newer_sequence(9, 10))
        self.assertTrue(is_newer_sequence(0, 0xffffffff))

    def test_command_binary_protocol_round_trips(self):
        payload = encode_command(MSG_DRIVE, 42, 500, -250, 0)
        self.assertEqual(decode_command(payload), (MSG_DRIVE, 42, 500, -250, 0))
        self.assertIsNone(decode_command(payload[:-1]))

    def test_square_runs_forward_right_back_left_then_stops(self):
        square = SquareRunner(leg_ms=10, pause_ms=2, speed=550)
        square.start(0)
        self.assertEqual(square.update(0), (0, 550, 0, True))
        self.assertEqual(square.update(10), (0, 0, 0, True))
        self.assertEqual(square.update(12), (550, 0, 0, True))
        self.assertEqual(square.update(24), (0, -550, 0, True))
        self.assertEqual(square.update(36), (-550, 0, 0, True))
        self.assertEqual(square.update(48), (0, 0, 0, False))

    def test_square_has_zero_ideal_displacement_and_rotation(self):
        legs = ((0, 550, 0), (550, 0, 0),
                (0, -550, 0), (-550, 0, 0))
        self.assertEqual(tuple(sum(leg[axis] for leg in legs) for axis in range(3)),
                         (0, 0, 0))
        for vx, vy, rot in legs:
            wheels = normalize_wheels(vx / 1000, vy / 1000, rot, 0.75, (1, 1, 1))
            self.assertLessEqual(max(abs(value) for value in wheels), 1.0)

    def test_square_can_be_cancelled_immediately(self):
        square = SquareRunner()
        square.start(0)
        square.stop()
        self.assertEqual(square.update(1), (0, 0, 0, False))

    def test_protocol_reserves_motor_calibration_messages(self):
        self.assertEqual((MSG_MOTOR_TEST, MSG_MOTOR_MODEL, MSG_QUERY_CONFIG), (9, 10, 11))

    def test_motor_command_compensates_static_deadzone(self):
        self.assertEqual(linearize_motor_command(0, 0.14, 0.45), 0)
        self.assertAlmostEqual(linearize_motor_command(0.5, 0.14, 0.45), 0.295)
        self.assertAlmostEqual(linearize_motor_command(-1, 0.14, 0.45), -0.45)

    def test_reversed_rear_wheel_turns_lateral_command_into_rotation(self):
        desired = normalize_wheels(-1, 0, 0, 0.75, (1, 1, 1))
        physical = (desired[0], desired[1], -desired[2])
        actual_rot = -(physical[0] + physical[1] + physical[2]) / (3 * 0.75)
        self.assertGreater(abs(actual_rot), 0.5)


if __name__ == "__main__":
    unittest.main()
