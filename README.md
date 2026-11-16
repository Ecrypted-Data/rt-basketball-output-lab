# 篮球追踪输出练习

对应《技术选型与原型》任务二。项目逐帧检测橙色篮球，生成带标记的视频和逐帧 CSV。你需要在这个基础上增加关键帧截图。

## 运行

在 Ubuntu 或 WSL 的仓库根目录执行以下命令。使用 Python 3.10–3.13。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m basketball --output-dir runs/baseline
```

仓库自带实拍验收视频 `samples/basketball.mp4`，覆盖篮球正常可见、完全出画和重新进入画面三个阶段。上述命令会直接读取它。试跑其他视频时，可以加 `--input 视频路径`。

- `tracking.csv` 每帧一行，含帧号、时间、追踪状态和位置。帧号从 0 开始；未检测到时状态为 `lost`，坐标留空。
- `annotated.mp4` 画出已检测到的篮球并标明当前帧号及状态。

## 模块

| 模块 | 职责 |
| --- | --- |
| `video.py` | 读取视频帧及初始化视频写入器 |
| `detection.py` | 从单帧定位篮球并返回坐标和半径 |
| `tracking.py` | 将单帧检测整理为带帧号、时间和状态的结果 |
| `output.py` | 用结果绘制标注并写出 CSV 和视频 |
| `__main__.py` | 解析参数和串联处理流程 |

## 提交

先在 GitHub 上 Fork 本仓库，在自己的 Fork 里创建工作分支。完成后从该分支向原仓库的 `main` 发起 PR，并将 PR 链接填入飞书问卷。组长在 PR 中验收和反馈，验收后关闭 PR。

保留原有视频和 CSV，复用已有检测结果，并输出正常可见、完全出画和重新进入画面三个阶段的截图。截图和复测记录按飞书问卷中的题目提交。

## 关键帧截图（任务二）

```bash
python -m basketball --output-dir runs/after --keyframes 0 175 240
python -m unittest discover -s tests -v
```

`--keyframes` 使用从 0 开始的帧号，重复帧号只保存一次；不传该参数时保留原运行方式。截图在 `keyframes/frame_<六位帧号>_<visible或lost>.png`，与原图同尺寸，带检测圆、圆心以及帧号/状态。无检测结果的帧标注 LOST，不画旧位置。负帧号、视频外帧号或 PNG 写入失败会明确报错。建议写入新的输出目录，以免混入以前运行的截图。

三个实拍验收帧：0（0.000 秒，正常可见）、175（2.916 秒，完全出画）、240（3.999 秒，重新进入）。PNG 直接使用 output.py 中为原标注视频生成的同一份 `marked` 图像，数据来自 track_video 的 detect_ball → Tracker.update → TrackingResult.ball，未重新运行检测。

只修改 output.py 的输出写入逻辑和 __main__.py 的参数传递；检测、追踪和视频读取模块未变。原 CSV 字段、视频标注方式、默认命令保持兼容。

对照结果：同一 samples/basketball.mp4，原基线与新增截图版本均为 302 帧；tracking.csv 字节完全相同，annotated.mp4 文件 SHA-256 相同，逐帧解码后的全部像素也相同。4 个测试全部通过。详见 [实际验收](docs/verification.md) 和 [对照数据](docs/evidence/comparison.json)。
