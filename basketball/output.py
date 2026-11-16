import csv
from collections.abc import Iterable, Sequence
from pathlib import Path

import cv2
import numpy as np

from .keyframes import Keyframe
from .tracking import TrackingResult
from .video import frames, open_video, open_writer


def annotate(frame: np.ndarray, result: TrackingResult) -> np.ndarray:
    marked = frame.copy()
    if result.ball is not None:
        ball = result.ball
        cv2.circle(marked, (ball.x, ball.y), ball.radius, (65, 235, 90), 2)
        cv2.circle(marked, (ball.x, ball.y), 2, (65, 235, 90), -1)

    label = f"Frame {result.frame_index} | {result.status.upper()}"
    cv2.putText(marked, label, (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (15, 15, 15), 3)
    cv2.putText(marked, label, (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (250, 250, 250), 1)
    return marked


def write_outputs(
    items: Iterable[tuple[np.ndarray, TrackingResult]], fps: float, directory: Path
) -> list[TrackingResult]:
    """Write the annotated video and CSV, returning the per-frame results."""
    directory.mkdir(parents=True, exist_ok=True)
    writer = None
    records: list[TrackingResult] = []
    try:
        with (directory / "tracking.csv").open("w", encoding="utf-8", newline="") as output:
            log = csv.writer(output)
            log.writerow(("frame", "time_s", "status", "center_x", "center_y", "radius"))
            for frame, result in items:
                marked = annotate(frame, result)
                if writer is None:
                    writer = open_writer(directory / "annotated.mp4", fps, marked)
                writer.write(marked)

                ball = result.ball
                coordinates = ("", "", "") if ball is None else (ball.x, ball.y, ball.radius)
                log.writerow((result.frame_index, f"{result.time_seconds:.3f}", result.status, *coordinates))
                records.append(result)
    finally:
        if writer is not None:
            writer.release()
    return records


def write_screenshots(
    input_path: Path,
    records: Sequence[TrackingResult],
    keyframes: Sequence[Keyframe],
    directory: Path,
) -> list[Path]:
    """Save annotated stills for the selected keyframes, reusing the recorded results."""
    if not keyframes:
        return []

    directory.mkdir(parents=True, exist_ok=True)
    wanted = {keyframe.frame_index: keyframe for keyframe in keyframes}
    last_index = max(wanted)
    written: list[Path] = []

    reader = open_video(input_path)
    try:
        for index, frame in enumerate(frames(reader)):
            keyframe = wanted.get(index)
            if keyframe is not None:
                path = directory / f"{keyframe.stage}.jpg"
                marked = annotate(frame, records[index])
                if not cv2.imwrite(str(path), marked, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    raise OSError(f"Cannot write screenshot: {path}")
                written.append(path)
            if index == last_index:
                break
        else:
            raise OSError(f"Input video ended before frame {last_index}: {input_path}")
    finally:
        reader.release()
    return written
