from collections.abc import Iterable, Iterator
from pathlib import Path

import cv2
import numpy as np


def open_video(path: Path) -> cv2.VideoCapture:
    reader = cv2.VideoCapture(str(path))
    if not reader.isOpened():
        reader.release()
        raise OSError(f"Cannot open input video: {path}")
    return reader


def frames(reader: cv2.VideoCapture) -> Iterator[np.ndarray]:
    while True:
        success, frame = reader.read()
        if not success:
            return
        yield frame


def read_frames_at(path: Path, indices: Iterable[int]) -> Iterator[tuple[int, np.ndarray]]:
    """Yield ``(index, frame)`` for ascending indices, decoding forward only."""
    wanted = sorted(set(indices))
    if not wanted:
        return

    reader = open_video(path)
    try:
        position = 0
        for index in wanted:
            while position < index:
                if not reader.grab():
                    return
                position += 1
            success, frame = reader.read()
            if not success:
                return
            position += 1
            yield index, frame
    finally:
        reader.release()


def open_writer(path: Path, fps: float, frame: np.ndarray) -> cv2.VideoWriter:
    height, width = frame.shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        writer.release()
        raise OSError(f"Cannot open output video: {path}")
    return writer
