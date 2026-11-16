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


KEYFRAME_SETTLE_SECONDS = 0.5


def save_keyframe(directory: Path, frame: np.ndarray, result: TrackingResult, stage: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stage}_frame_{result.frame_index:04d}.jpg"
    if not cv2.imwrite(str(path), frame):
        raise OSError(f"Cannot write keyframe screenshot: {path}")


def write_outputs(
    items: Iterable[tuple[np.ndarray, TrackingResult]], fps: float, directory: Path
) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    keyframes = directory / "keyframes"
    settle_frames = max(1, round(fps * KEYFRAME_SETTLE_SECONDS))
    writer = None
    count = 0
    previous_status = None
    lost_frames = 0
    pending_lost: tuple[np.ndarray, TrackingResult] | None = None
    try:
        with (directory / "tracking.csv").open("w", encoding="utf-8", newline="") as output:
            log = csv.writer(output)
            log.writerow(("frame", "time_s", "status", "center_x", "center_y", "radius"))
            for frame, result in items:
                marked = annotate(frame, result)
                status = result.status
                if status == "visible":
                    if previous_status is None:
                        save_keyframe(keyframes, marked, result, "visible")
                    elif previous_status == "lost":
                        if pending_lost is not None:
                            save_keyframe(keyframes, *pending_lost, "lost")
                            pending_lost = None
                        save_keyframe(keyframes, marked, result, "reentry")
                    lost_frames = 0
                else:
                    lost_frames += 1
                    # Let the ball clear the frame before recording the lost stage.
                    if lost_frames == settle_frames:
                        save_keyframe(keyframes, marked, result, "lost")
                        pending_lost = None
                    elif lost_frames < settle_frames:
                        pending_lost = (marked, result)
                previous_status = status

                if writer is None:
                    writer = open_writer(directory / "annotated.mp4", fps, marked)
                writer.write(marked)

                ball = result.ball
                coordinates = ("", "", "") if ball is None else (ball.x, ball.y, ball.radius)
                log.writerow((result.frame_index, f"{result.time_seconds:.3f}", result.status, *coordinates))
                count += 1
            if pending_lost is not None:
                save_keyframe(keyframes, *pending_lost, "lost")
    finally:
        if writer is not None:
            writer.release()
    return count
