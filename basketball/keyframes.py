"""关键帧截图：挑选覆盖三个阶段的帧，复用主流程检测结果输出带标记的 PNG。"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2

from .output import annotate
from .tracking import TrackingResult
from .video import frames, open_video


@dataclass(frozen=True)
class Keyframe:
    stage: str  # 短标识，用于截图文件名
    label: str  # 画在截图上的英文阶段说明（cv2 位图字体只支持 ASCII）
    result: TrackingResult


def _status_runs(results: Sequence[TrackingResult]) -> list[tuple[str, int, int]]:
    """把逐帧结果切成连续同状态的段，返回 (status, start, end)，端点含自身。"""
    runs: list[tuple[str, int, int]] = []
    start = 0
    for i in range(1, len(results) + 1):
        # 到末尾或状态切换时收束当前段（比较对象是段首状态，start 不会越界）
        if i == len(results) or results[i].status != results[start].status:
            runs.append((results[start].status, start, i - 1))
            start = i
    return runs


def select_keyframes(results: Sequence[TrackingResult]) -> list[Keyframe]:
    """挑选关键帧，覆盖正常可见、完全出画、重新进入画面三个阶段。

    - normal-visible：第一段可见段的中点（正常可见）
    - out-of-frame：最长丢失段的中点（完全出画）
    - re-entering：丢失段之后重新可见的第一帧（重新进入画面）
    """
    if not results:
        return []

    runs = _status_runs(results)
    picked: list[Keyframe] = []

    # 1) 正常可见：视频开头第一段可见段
    first_visible = next((run for run in runs if run[0] == "visible"), None)
    if first_visible is not None:
        _, start, end = first_visible
        mid = (start + end) // 2
        picked.append(Keyframe("normal-visible", "KEYFRAME: NORMAL VISIBLE", results[mid]))

    # 2) 完全出画：取最长丢失段（并列取最早），段内中点最具代表性
    lost_runs = [run for run in runs if run[0] == "lost"]
    if lost_runs:
        _, start, end = max(lost_runs, key=lambda run: (run[2] - run[1], -run[1]))
        mid = (start + end) // 2
        picked.append(Keyframe("out-of-frame", "KEYFRAME: OUT OF FRAME", results[mid]))
        # 3) 重新进入画面：丢失段结束后重新可见的第一帧
        if end + 1 < len(results) and results[end + 1].status == "visible":
            picked.append(Keyframe("re-entering", "KEYFRAME: RE-ENTERING", results[end + 1]))

    # 同一帧只保留一张，避免重复截图
    unique: list[Keyframe] = []
    seen: set[int] = set()
    for key in picked:
        if key.result.frame_index not in seen:
            seen.add(key.result.frame_index)
            unique.append(key)
    return unique


def _draw_keyframe(frame, key: Keyframe):
    """在 annotate 的检测标记之上补画阶段说明与坐标，方便核对位置。"""
    marked = annotate(frame, key.result)  # 复用原有标注：检测圈 + Frame N | 状态
    ball = key.result.ball
    info = f"ball=({ball.x}, {ball.y}) r={ball.radius}" if ball else "ball: no detection"
    for text, y in ((key.label, 52), (info, 76)):
        # 与 annotate 相同的描边画法，保证浅色背景上也可读
        cv2.putText(marked, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (15, 15, 15), 3)
        cv2.putText(marked, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (250, 250, 250), 1)
    return marked


def save_keyframes(
    input_path: Path, results: Sequence[TrackingResult], directory: Path
) -> list[Path]:
    """按帧号回读输入视频像素，套用主流程已产出的检测结果生成关键帧截图。

    只重新解码像素、不重新检测：截图上的检测标记与 tracking.csv / annotated.mp4 同源。
    """
    selected = select_keyframes(results)
    if not selected:
        return []

    by_index = {key.result.frame_index: key for key in selected}
    last_needed = max(by_index)
    directory = directory / "keyframes"
    directory.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    reader = open_video(input_path)
    try:
        for index, frame in enumerate(frames(reader)):
            if index > last_needed:
                break  # 所需帧已取完，提前结束解码
            key = by_index.get(index)
            if key is None:
                continue
            marked = _draw_keyframe(frame, key)
            # 文件名注明帧号，与画面左上角的 Frame N 对应
            path = directory / f"keyframe_{key.stage}_frame{index:04d}.png"
            if not cv2.imwrite(str(path), marked):
                raise OSError(f"Cannot write keyframe image: {path}")
            saved.append(path)
    finally:
        reader.release()
    return saved
