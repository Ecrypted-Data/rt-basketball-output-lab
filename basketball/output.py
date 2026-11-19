import csv
from collections.abc import Iterable
from pathlib import Path

import cv2
import numpy as np

from .tracking import TrackingResult
from .video import open_video, open_writer


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
    directory.mkdir(parents=True, exist_ok=True)
    writer = None
    results: list[TrackingResult] = []
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
                results.append(result)
    finally:
        if writer is not None:
            writer.release()
    return results


def _phase_frames(results: list[TrackingResult]) -> list[tuple[str, TrackingResult]]:
    """Pick the first visible frame, the middle of the longest absence and the re-entry frame."""
    picks: list[tuple[str, TrackingResult]] = []
    first_visible = next((result for result in results if result.ball is not None), None)
    if first_visible is not None:
        picks.append(("visible", first_visible))

    runs: list[tuple[int, int]] = []
    start = None
    last_lost = None
    for result in results:
        if result.ball is None:
            start = result.frame_index if start is None else start
            last_lost = result.frame_index
        elif start is not None:
            runs.append((start, last_lost))
            start = None
    if start is not None:
        runs.append((start, last_lost))

    if runs:
        by_index = {result.frame_index: result for result in results}
        absent_start, absent_end = max(runs, key=lambda run: run[1] - run[0])
        picks.append(("absent", by_index[(absent_start + absent_end) // 2]))
        reentry = by_index.get(absent_end + 1)
        if reentry is not None and reentry.ball is not None:
            picks.append(("reentry", reentry))
    return picks


def write_screenshots(input_path: Path, results: list[TrackingResult], directory: Path) -> None:
    """Save one annotated screenshot per phase, reusing the tracking results."""
    screenshots = directory / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    reader = open_video(input_path)
    try:
        for phase, result in _phase_frames(results):
            reader.set(cv2.CAP_PROP_POS_FRAMES, result.frame_index)
            success, frame = reader.read()
            if not success:
                raise OSError(f"Cannot read frame {result.frame_index} from {input_path}")
            path = screenshots / f"{phase}_frame{result.frame_index:04d}.png"
            if not cv2.imwrite(str(path), annotate(frame, result)):
                raise OSError(f"Cannot write screenshot: {path}")
    finally:
        reader.release()
