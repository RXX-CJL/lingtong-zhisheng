# 车牌识别技术选型方案（开源复用调研）

> 生成日期：2026-09-27 · 执行者：DSH
> 触发原因：项目当前 **未安装 `paddleocr`**，车牌识别处于降级状态（`license_plate_recognizer.py` 里 `PADDLEOCR_AVAILABLE = False`），而"检测→车牌识别→违规记录"是项目三大创新点之二的核心链路。
> 依据用户规则：**优先复用开源，踩在巨人的肩膀上**。

---

## 一、结论先行

**推荐方案 A：改用 `hyperlpr3` 作为车牌 OCR 引擎**（保留现有 YOLO 定位器）

理由一句话：**一条 pip 即可装、零 numpy 冲突、专为中文车牌设计**，而现有代码里 YOLO 车牌定位器（`license_plate` 模型）已经能跑。

---

## 二、候选对比（均为 GitHub 实测可达，非搜索摘要）

| 项目 | HEAD（实测） | 定位 | 依赖 | 落地成本 | 判断 |
|---|---|---|---|---|---|
| **`szad670401/HyperLPR`**（HyperLPR3） | `9307450f7b` | 高性能**中文**车牌识别框架 | `opencv-python, onnxruntime, tqdm, requests, fastapi, uvicorn, python-multipart, loguru`（**不含 numpy**） | **低**：`pip install hyperlpr3`，纯 Python wheel，Windows 可用 | ⭐ **首选** |
| `sirius-ai/LPRNet_Pytorch` | `7c976664b3` | 轻量车牌识别（蓝牌/绿牌） | `pytorch>=1.0.0, opencv-python 3.x` | 中：需权重文件 + 自己接推理 | 备选（我们已有 torch，但需额外训练/权重管理） |
| `we0091234/Chinese_license_plate_detection_recognition` | `670b765c09` | 中文车牌检测识别（YOLO 系列） | requirements 里含 `matplotlib/ipykernel/jupyter` 等**研究型依赖** | 中高：依赖散、偏 notebook 项目 | 参考其方案，不直接引入 |
| `beita6969/-` | `617edcae8f` | 智能车牌识别管理系统（YOLOv8x + YOLOv11 + HyperLPR3 + EasyOCR） | 仓库名异常（`-`） | 高 | 仅作架构参考：它也用 HyperLPR3 |
| `maruthisaiteja/smart-traffic-violation-detection-using-YOLOv8` | `95246664a6` | YOLOv8 违规检测（未戴头盔/闯红灯） | — | 低但功能重叠 | 参考（我们已有同类能力） |

---

## 三、事实依据 / 我的判断 / 风险

### 事实依据
1. `hyperlpr3` 在 PyPI 上 **latest = 0.1.3，上传于 2023-02-28**，仅 1 个版本，wheel 为 `hyperlpr3-0.1.3-py3-none-any.whl`（纯 Python，Windows 可用）。
2. 其 `requires_dist` **不含 numpy**，走 `onnxruntime` → 与本机现有 `numpy 2.0.1` 无冲突（这是关键：PaddleOCR 路线的主要风险点就是 numpy 版本）。
3. 官方 README 用法极简：`catcher = lpr3.LicensePlateCatcher()`。
4. 项目现有 GPU 环境 `C:\miniconda\envs\zhitong-gpu`（Python 3.11.15）已有 `torch 2.5.1 / ultralytics 8.4.103 / opencv 5.0.0`；车牌**定位**由 `zhitong/training/models/lane.pt` 同级的 YOLO 车牌模型负责（启动日志显示 `license_plate` 走 fallback yolov8s）。
5. 代码侧已具备降级开关：`license_plate_recognizer.py:26-32` 用 `try: from paddleocr import PaddleOCR / except ImportError: PADDLEOCR_AVAILABLE = False`。

### 我的判断
- 现有链路只缺"**把车牌图 → 文字**"这一步。YOLO 定位已经在跑，因此**不需要整套替换**，只需换 OCR 引擎。
- HyperLPR3 的依赖与现有环境重叠度高（opencv/onnxruntime/requests/fastapi/uvicorn 均已具备或极易满足），**新增成本远低于 PaddlePaddle**。
- 因此建议：**新增 HyperLPR3 作为主 OCR，PaddleOCR 保留为可选次选**（代码里做引擎优先级，而非二选一硬绑）。

### 风险
| # | 风险 | 缓解 |
|---|---|---|
| 1 | **停更 3 年（2023-02）**，仅 1 个版本 → 出问题无版本回退 | 先在 GPU 环境隔离验证（不写死代码），通过后再接 |
| 2 | `onnxruntime` 与 Python 3.11 / 平台 wheel 的匹配未知 | 安装时先 `pip index versions onnxruntime` 确认，或用 `--only-binary` |
| 3 | 项目现有 `license_plate_recognizer.py` 是按 PaddleOCR 的结果结构写的 | 改造点为**小范围**：增加一个 OCR 后端适配层，统一输出（车牌号 + 置信度） |
| 4 | 依赖里带 `fastapi/uvicorn/python-multipart`（HyperLPR3 自带 demo 服务） | 我们已装同款，无冲突；但其版本约束可能收紧，需留意 |

---

## 四、建议执行步骤（待用户批准，属环境变更）

1. **只读核实**：`pip index versions onnxruntime`，确认 Python 3.11 + Windows 的可用 wheel。
2. **隔离试装**（不动项目代码）：在 GPU 环境 `pip install hyperlpr3`，跑官方最小示例对一张测试车牌图出结果。
3. **通过后改代码**（小范围）：
   - `license_plate_recognizer.py` 增加 HyperLPR3 分支，优先使用；PaddleOCR 作为回退。
   - 统一返回结构，保持 `image_recognizer.py:969` 等调用点不变。
4. **验证**：用项目现有测试图做端到端（违规图 → 车牌号），三级证据（截图/接口返回）。
5. **登记**：更新 `PROJECT_HANDOVER_REPORT.md` 的技术栈表与已知坑。

---

## 五、对"先跑通"的意义

- 目前**跑通不依赖它**（后端已起、前端已渲染、事件视频历史上也产出过）。
- 但它决定"**车牌识别**"这一核心卖点能否真实演示。建议排在"跑通基线"之后、答辩材料之前。
