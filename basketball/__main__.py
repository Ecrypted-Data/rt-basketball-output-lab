import argparse
import math
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from .detection import detect_ball
from .keyframes import save_keyframes
from .output import write_outputs
from .tracking import Tracker, TrackingResult
from .video import frames, open_video


def track_video(reader: cv2.VideoCapture, fps: float) -> Iterator[tuple[np.ndarray, TrackingResult]]:
    tracker = Tracker()
    for index, frame in enumerate(frames(reader)):
        detection = detect_ball(frame)
        yield frame, tracker.update(index, fps, detection)


def collect_results(
    items: Iterator[tuple[np.ndarray, TrackingResult]], sink: list[TrackingResult]
) -> Iterator[tuple[np.ndarray, TrackingResult]]:
    """透传 (frame, result) 流，同时把轻量结果存入 sink，供关键帧截图复用。"""
    for frame, result in items:
        sink.append(result)
        yield frame, result


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
    results: list[TrackingResult] = []
    try:
        reader = open_video(input_path)
        try:
            fps = reader.get(cv2.CAP_PROP_FPS)
            if not math.isfinite(fps) or fps <= 0:
                parser.error(f"Invalid frame rate in {input_path}")
            count = write_outputs(collect_results(track_video(reader, fps), results), fps, args.output_dir)
            if count == 0:
                parser.error(f"No frames could be decoded from {input_path}")
        finally:
            reader.release()
        # 关键帧截图复用本次运行的检测结果，原有 CSV / 视频输出保持不变
        keyframe_paths = save_keyframes(input_path, results, args.output_dir)
    except OSError as error:
        parser.exit(1, f"{error}\n")

    print(f"{count} frames -> {args.output_dir / 'tracking.csv'} and {args.output_dir / 'annotated.mp4'}")
    for path in keyframe_paths:
        print(f"keyframe -> {path}")


if __name__ == "__main__":
    main()
