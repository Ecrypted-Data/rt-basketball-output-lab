from pathlib import Path

import cv2
import numpy as np

from .tracking import TrackingResult

NORMAL_VISIBLE = "normal-visible"
OUT_OF_FRAME = "out-of-frame"
RE_ENTERING = "re-entering"


def keyframe_filename(frame_index: int, phase: str) -> str:
    return f"keyframe_{phase}_frame{frame_index:04d}.png"


class KeyframeWriter:
    """Save the first and last annotated frame of every contiguous status run."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self._status: str | None = None
        self._phase = ""
        self._run_count = 0
        self._run_bounds: list[tuple[str, int, int]] = []
        self._start = 0
        self._frames = 0
        self._last: np.ndarray | None = None
        self._last_result: TrackingResult | None = None

    def add(self, marked: np.ndarray, result: TrackingResult) -> None:
        if result.status != self._status:
            self._close_run()
            self._status = result.status
            self._run_count += 1
            self._phase = self._phase_for(result.status)
            self._start = result.frame_index
            self._save(marked, result)

        self._frames += 1
        self._last = marked
        self._last_result = result

    def close(self) -> None:
        self._close_run()

    @property
    def lost_midpoints(self) -> list[tuple[int, str]]:
        """Frame number and filename for the middle of each fully-absent run."""
        return [
            (middle, keyframe_filename(middle, OUT_OF_FRAME))
            for status, start, end in self._run_bounds
            if status == "lost" and start < (middle := (start + end) // 2) < end
        ]

    def _phase_for(self, status: str) -> str:
        if status == "lost":
            return OUT_OF_FRAME
        return NORMAL_VISIBLE if self._run_count == 1 else RE_ENTERING

    def _close_run(self) -> None:
        if self._frames == 0 or self._last_result is None:
            return
        if self._frames > 1 and self._last is not None:
            self._save(self._last, self._last_result)
        self._run_bounds.append((str(self._status), self._start, self._last_result.frame_index))
        self._frames = 0
        self._last = None
        self._last_result = None

    def _save(self, marked: np.ndarray, result: TrackingResult) -> None:
        path = self.directory / keyframe_filename(result.frame_index, self._phase)
        if not cv2.imwrite(str(path), marked):
            raise OSError(f"Cannot write keyframe image: {path}")
