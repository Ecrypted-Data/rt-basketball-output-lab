# 任务二实际验收

日期：2026-11-16；基线提交 0d3c5830d7a43fc247a824657068524f6153d103。
环境：Ubuntu 26.04.1，Python 3.12.15，NumPy 2.2.6，opencv-python-headless 4.11.0.86；依赖严格使用仓库 requirements.txt。

基线（改动代码前）：`python -m basketball --output-dir runs/baseline`。
改动后：`python -m basketball --output-dir runs/after --keyframes 0 175 240`。
两次输入均为仓库 samples/basketball.mp4，SHA-256 f244ae13c9472ebb047d0c09caaaf41b947cad22decb66333c97fb82aff171a2。分辨率 360×640，FPS 60.014442，共 302 帧。

## 关键帧与模块边界

| 阶段 | 帧号（从0开始） | 时间/秒 | 状态 | 坐标 |
|---|---:|---:|---|---|
| 正常可见 | 0 | 0.000 | visible | (174,286), r=54 |
| 完全出画 | 175 | 2.916 | lost | 空 |
| 重新进入 | 240 | 3.999 | visible | 见 after-tracking.csv |

截图经过实际目视检查。已有检测器在边缘仍可能部分可见时就输出 lost：第143帧开始丢失，第215帧重新检出；这不等于整个丢失区间都完全出画，因此验收选用区间内部第175帧。没有改动检测算法来掩盖该限制。

截图复用 `output.annotate(frame,result)` 已为视频生成的图像，圆心半径来自 `TrackingResult.ball`；新增功能不导入或重复调用检测器。

## 原有输出核对

- tracking.csv：前后均 302 条数据、同一表头，每一字节完全一致。
- annotated.mp4：前后文件哈希一致；另分别逐帧解码，302 帧的尺寸和全部像素逐帧相等。
- 完整 SHA-256 和对照结论保存在 evidence/comparison.json；前后 CSV 及三个原尺寸 PNG 也保存在 evidence/。

## 自动测试

`python -m unittest discover -s tests -v`：4 个测试通过，覆盖实拍视频三阶段截图、开启/关闭截图后的原 CSV 和视频一致性、使用已给出的检测坐标及保持原帧不变、无效帧号与 PNG 写入失败。
