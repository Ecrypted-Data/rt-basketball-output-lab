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
- `keyframes/` 存关键帧截图：每个连续状态段的首帧与末帧，外加 `lost` 段中点（球完全出画）。
  文件名形如 `keyframe_out-of-frame_frame0178.png`；阶段按连续段命名，首段可见为 `normal-visible`、
  丢失段为 `out-of-frame`、之后重新可见的段为 `re-entering`。绘制方式与 `annotated.mp4` 一致，
  便于核对篮球出现、丢失和重新出现的位置。

## 模块

| 模块 | 职责 |
| --- | --- |
| `video.py` | 读取视频帧及初始化视频写入器 |
| `detection.py` | 从单帧定位篮球并返回坐标和半径 |
| `tracking.py` | 将单帧检测整理为带帧号、时间和状态的结果 |
| `output.py` | 用结果绘制标注并写出 CSV 和视频 |
| `keyframes.py` | 切分状态阶段并落盘关键帧截图 |
| `__main__.py` | 解析参数和串联处理流程 |

## 提交

先在 GitHub 上 Fork 本仓库，在自己的 Fork 里创建工作分支。完成后从该分支向原仓库的 `main` 发起 PR，并将 PR 链接填入飞书问卷。组长在 PR 中验收和反馈，验收后关闭 PR。

保留原有视频和 CSV，复用已有检测结果，并输出正常可见、完全出画和重新进入画面三个阶段的截图。截图和复测记录按飞书问卷中的题目提交。
