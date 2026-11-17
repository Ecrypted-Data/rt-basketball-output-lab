import csv
from collections.abc import Iterable
from pathlib import Path

import cv2
import numpy as np

from .tracking import TrackingResult
from .video import open_writer


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
    items: Iterable[tuple[np.ndarray, TrackingResult]],
    fps: float,
    directory: Path,
    *,
    snapshot_frames: set[int] | None = None,
) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    writer = None
    count = 0
    try:
        with (directory / "tracking.csv").open("w", encoding="utf-8", newline="") as output:
            log = csv.writer(output)
            log.writerow(("frame", "time_s", "status", "center_x", "center_y", "radius"))
            for frame, result in items:
                marked = annotate(frame, result)
                if snapshot_frames is not None and result.frame_index in snapshot_frames:
                    cv2.imwrite(
                        str(directory / f"snapshot_frame_{result.frame_index:05d}.png"), marked
                    )
                if writer is None:
                    writer = open_writer(directory / "annotated.mp4", fps, marked)
                writer.write(marked)

                ball = result.ball
                coordinates = ("", "", "") if ball is None else (ball.x, ball.y, ball.radius)
                log.writerow((result.frame_index, f"{result.time_seconds:.3f}", result.status, *coordinates))
                count += 1
    finally:
        if writer is not None:
            writer.release()
    return count
