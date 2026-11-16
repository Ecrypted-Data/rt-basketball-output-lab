"""Choose one representative frame per tracking phase."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from .tracking import TrackingResult

STAGES = ("visible", "lost", "reentry")


@dataclass(frozen=True)
class Keyframe:
    stage: str
    frame_index: int


def _runs(results: Sequence[TrackingResult]) -> Iterator[tuple[int, int]]:
    """Yield [start, end) spans of consecutive frames sharing one status."""
    start = 0
    for index in range(1, len(results) + 1):
        if index == len(results) or results[index].status != results[start].status:
            yield start, index
            start = index


def select_keyframes(results: Sequence[TrackingResult]) -> list[Keyframe]:
    """Pick the middle of the longest visible and lost runs, plus the first re-entry.

    Re-entry is the first visible frame that directly follows a lost run, so the
    three screenshots read as: ball tracked normally, ball fully out of frame,
    ball back in frame after the gap.
    """
    runs = list(_runs(results))
    picks: dict[str, int] = {}

    visible = [run for run in runs if results[run[0]].status == "visible"]
    if visible:
        start, end = max(visible, key=lambda run: run[1] - run[0])
        picks["visible"] = start + (end - start) // 2

    lost = [run for run in runs if results[run[0]].status == "lost"]
    if lost:
        start, end = max(lost, key=lambda run: run[1] - run[0])
        picks["lost"] = start + (end - start) // 2

    for previous, current in zip(runs, runs[1:]):
        if results[previous[0]].status == "lost" and results[current[0]].status == "visible":
            picks["reentry"] = current[0]
            break

    return [Keyframe(stage, picks[stage]) for stage in STAGES if stage in picks]
