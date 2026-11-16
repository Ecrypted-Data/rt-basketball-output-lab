import argparse
import math
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from .detection import detect_ball
from .output import write_outputs
from .tracking import Tracker, TrackingResult
from .video import frames, open_video


def track_video(reader: cv2.VideoCapture, fps: float) -> Iterator[tuple[np.ndarray, TrackingResult]]:
    tracker = Tracker()
    for index, frame in enumerate(frames(reader)):
        detection = detect_ball(frame)
        yield frame, tracker.update(index, fps, detection)


def main() -> None:
    parser = argparse.ArgumentParser(description="Track the basketball in a video.")
    default_video = Path(__file__).resolve().parents[1] / "samples" / "basketball.mp4"
    parser.add_argument(
        "--input", type=Path, default=default_video,
        help="Path to the input video (default: bundled samples/basketball.mp4).",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("runs/tracking"))
    parser.add_argument(
        "--keyframes", type=int, nargs="+", default=[], metavar="FRAME",
        help="Also export annotated PNGs for these zero-based frame indices.",
    )
    args = parser.parse_args()
    if any(index < 0 for index in args.keyframes):
        parser.error("--keyframes must contain non-negative frame indices")

    input_path = args.input
    try:
        reader = open_video(input_path)
        try:
            fps = reader.get(cv2.CAP_PROP_FPS)
            if not math.isfinite(fps) or fps <= 0:
                parser.error(f"Invalid frame rate in {input_path}")
            count = write_outputs(track_video(reader, fps), fps, args.output_dir, args.keyframes)
            if count == 0:
                parser.error(f"No frames could be decoded from {input_path}")
        finally:
            reader.release()
    except OSError as error:
        parser.exit(1, f"{error}\n")

    print(f"{count} frames -> {args.output_dir / 'tracking.csv'} and {args.output_dir / 'annotated.mp4'}")


if __name__ == "__main__":
    main()
