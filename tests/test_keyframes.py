import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from basketball.detection import Ball
from basketball.output import write_outputs
from basketball.tracking import TrackingResult

ROOT = Path(__file__).resolve().parents[1]


class KeyframeTests(unittest.TestCase):
    def run_cli(self, directory, *options):
        return subprocess.run(
            [sys.executable, '-m', 'basketball', '--output-dir', str(directory), *options],
            cwd=ROOT, capture_output=True, text=True,
        )

    def test_sample_exports_and_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain, extra = Path(tmp)/'plain', Path(tmp)/'extra'
            for directory, options in [(plain, ()), (extra, ('--keyframes', '0', '175', '240'))]:
                result = self.run_cli(directory, *options)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((plain/'tracking.csv').read_bytes(), (extra/'tracking.csv').read_bytes())
            with (extra/'tracking.csv').open() as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 302)
            self.assertEqual([rows[i]['status'] for i in (0, 175, 240)], ['visible', 'lost', 'visible'])
            for i, status in [(0, 'visible'), (175, 'lost'), (240, 'visible')]:
                image = cv2.imread(str(extra/'keyframes'/f'frame_{i:06d}_{status}.png'))
                self.assertIsNotNone(image)
                self.assertEqual(image.shape, (640, 360, 3))
            self.assertFalse((plain/'keyframes').exists())
            readers = [cv2.VideoCapture(str(d/'annotated.mp4')) for d in (plain, extra)]
            try:
                count = 0
                while True:
                    a, b = readers[0].read(), readers[1].read()
                    self.assertEqual(a[0], b[0])
                    if not a[0]:
                        break
                    np.testing.assert_array_equal(a[1], b[1])
                    count += 1
                self.assertEqual(count, 302)
            finally:
                for reader in readers:
                    reader.release()

    def test_reuses_supplied_detection_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            result = TrackingResult(7, 0.7, Ball(50, 70, 12))
            write_outputs([(frame, result)], 10, Path(tmp), [7])
            image = cv2.imread(str(Path(tmp)/'keyframes/frame_000007_visible.png'))
            np.testing.assert_array_equal(image[70, 50], [65, 235, 90])
            self.assertFalse(np.any(frame))
            with (Path(tmp)/'tracking.csv').open() as file:
                row = next(csv.DictReader(file))
            self.assertEqual((row['center_x'], row['center_y']), ('50', '70'))

    def test_invalid_requested_frame_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            for index in ('-1', '9999'):
                result = self.run_cli(Path(tmp)/index, '--keyframes', index)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('keyframes', result.stderr)

    def test_failed_png_write_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp, patch('basketball.output.cv2.imwrite', return_value=False):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            with self.assertRaisesRegex(OSError, 'Cannot write keyframe'):
                write_outputs([(frame, TrackingResult(0, 0.0, None))], 10, Path(tmp), [0])


if __name__ == '__main__':
    unittest.main()
