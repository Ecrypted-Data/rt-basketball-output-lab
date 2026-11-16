import argparse
import math
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from .detection import detect_ball
from .keyframes import select_keyframes
from .output import write_outputs, write_screenshots
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
    args = parser.parse_args()

    input_path = args.input
    try:
        reader = open_video(input_path)
        try:
            fps = reader.get(cv2.CAP_PROP_FPS)
            if not math.isfinite(fps) or fps <= 0:
                parser.error(f"Invalid frame rate in {input_path}")
            records = write_outputs(track_video(reader, fps), fps, args.output_dir)
            if not records:
                parser.error(f"No frames could be decoded from {input_path}")
        finally:
            reader.release()
    except OSError as error:
        parser.exit(1, f"{error}\n")

    keyframes = select_keyframes(records)
    try:
        screenshots = write_screenshots(
            input_path, records, keyframes, args.output_dir / "keyframes"
        )
    except OSError as error:
        parser.exit(1, f"{error}\n")

    print(f"{len(records)} frames -> {args.output_dir / 'tracking.csv'} and {args.output_dir / 'annotated.mp4'}")
    for keyframe, path in zip(keyframes, screenshots):
        print(f"{keyframe.stage} frame {keyframe.frame_index} -> {path}")


if __name__ == "__main__":
    main()
