# TASK-014 GPU环境修复 - 问题清单

**生成时间**: 2026-07-21  
**任务编号**: TASK-014  
**任务名称**: GPU环境修复 + GitHub资源下载 + 模型训练继续  

---

## 问题统计概览

| 优先级 | 数量 | 类型 |
|--------|------|------|
| 🔴 P0 | 2 | 阻塞性问题 |
| 🟠 P1 | 2 | 重要问题 |
| 🟡 P2 | 1 | 一般问题 |

---

## 详细问题清单

### 🔴 P0-001: PyTorch CUDA版本安装失败 - 哈希不匹配

**问题描述**:  
尝试通过pip安装CUDA版本的PyTorch时，下载完成后出现SHA256哈希校验失败，导致安装被中断。

**发生场景**:  
执行命令 `python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124` 时

**错误表现**:  
```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE.
    unknown package:
        Expected sha256 3313061c1fec4c7310cf47944e84513dcd27b6173b72a349bb7ca68d0ee6e9c0
             Got        fa01d256756f045ee55bda033a033bbfc8f4bdebfc2b8d873a569c950ec01605
```

**已尝试的解决方法**:  
1. ✗ 添加 `--no-cache-dir` 参数 → 仍然失败  
2. ✗ 添加 `--trusted-host` 参数 → 仍然失败  
3. ✗ 指定具体版本号 (2.4.0, 2.5.1, 2.6.0) → 仍然失败  
4. ✗ 使用清华镜像源 → 下载了CPU版本而非CUDA版本  
5. ✗ 添加 `--timeout 600` 和 `--retries 3` → 仍然失败  
6. ✗ 直接使用curl下载whl文件 → 下载超时  

**可能原因**:  
- PyTorch官方下载服务器的metadata与实际文件不同步  
- 网络传输过程中文件损坏  
- 国内网络环境导致下载内容被篡改  

**影响范围**:  
- 无法启用GPU加速训练  
- 后续所有模型训练任务无法执行  

**建议解决方案**:  
1. 使用conda安装（需先找到conda路径）  
2. 手动下载whl文件后离线安装  
3. 使用NVIDIA NGC提供的PyTorch镜像  
4. 安装CUDA Toolkit后从源码编译  

---

### 🔴 P0-002: CUDA Toolkit未安装

**问题描述**:  
系统中缺少NVIDIA CUDA Toolkit，仅有GPU驱动。

**发生场景**:  
执行 `nvcc --version` 时提示命令不存在  

**错误表现**:  
```
nvcc : The term 'nvcc' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

**已尝试的解决方法**:  
1. ✗ 搜索 `C:\Program Files\NVIDIA GPU Computing Toolkit` → 目录不存在  
2. ✗ 检查环境变量 `CUDA_PATH` → 未设置  

**系统环境信息**:  
- GPU型号: NVIDIA GeForce RTX 4060  
- GPU驱动版本: 566.07  
- CUDA驱动版本: 12.7  
- Python版本: 3.12.10  

**影响范围**:  
- 无法编译CUDA代码  
- PyTorch可能无法正确加载CUDA运行时  

**建议解决方案**:  
1. 下载并安装CUDA Toolkit 12.x版本（与驱动兼容）  
2. 设置环境变量 `CUDA_PATH` 和 `PATH`  

---

### 🟠 P1-003: Conda环境无法找到

**问题描述**:  
任务通知中要求使用 `conda activate zhitong-gpu` 激活环境，但系统中无法找到conda命令。

**发生场景**:  
执行 `conda activate zhitong-gpu` 或查找conda.exe时  

**错误表现**:  
```
conda : The term 'conda' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

**已尝试的解决方法**:  
1. ✗ 搜索 `C:\Users\ROG\.anaconda` → 目录存在但无conda.exe  
2. ✗ 搜索 `C:\Users\ROG\.conda` → 目录存在但无conda.exe  
3. ✗ 搜索全系统 `conda.exe` → 无结果  

**影响范围**:  
- 无法使用预配置的zhitong-gpu环境  
- 需要在系统Python环境中安装所有依赖  

**建议解决方案**:  
1. 安装Anaconda或Miniconda  
2. 手动创建虚拟环境并安装依赖  
3. 如果zhitong-gpu环境已存在，找到其Python路径直接使用  

---

### 🟠 P1-004: 网络下载超时

**问题描述**:  
下载大文件（如PyTorch 2.5GB）时经常超时。

**发生场景**:  
通过pip或curl下载大文件时  

**错误表现**:  
```
pip._vendor.urllib3.exceptions.ReadTimeoutError: HTTPSConnectionPool(host='download-r2.pytorch.org', port=443): Read timed out.
```

**已尝试的解决方法**:  
1. ✗ 增加超时时间到600秒 → 仍然超时  
2. ✗ 使用国内镜像源 → 清华源无CUDA版本  

**影响范围**:  
- 无法下载CUDA版本PyTorch  
- 无法下载GitHub上的大型模型文件  

**建议解决方案**:  
1. 使用代理服务器  
2. 使用下载工具（如IDM）分段下载  
3. 从国内镜像源（如阿里云、豆瓣）下载  

---

### 🟡 P2-005: 头盔模型精度未达标

**问题描述**:  
之前训练的头盔检测模型mAP50=0.621，未达到目标值>0.80。

**发生场景**:  
TASK-013任务中训练头盔检测模型后  

**错误表现**:  
```
Results saved to runs\train\helmet_exp2
mAP50: 0.621
```

**已尝试的解决方法**:  
1. ✓ 数据增强（水平翻转、旋转、亮度调整等）  
2. ✓ 归一化类别索引（3→0, 4→1）  
3. ✗ 增加epochs（30→100）→ 未执行（等待GPU环境）  

**计划优化方案**:  
1. 使用GPU加速训练更多epochs（100）  
2. 使用更大模型（YOLOv8n → YOLOv8s）  
3. 从GitHub下载现成头盔检测模型  

---

## 问题依赖关系图

```
P0-002 (CUDA Toolkit未安装)
    ↓
P0-001 (PyTorch CUDA安装失败)
    ↓
P2-005 (头盔模型精度未达标)
    ↓
[所有后续训练任务]

P1-003 (Conda环境无法找到)
    ↓
[环境配置困难]

P1-004 (网络下载超时)
    ↓
P0-001 (PyTorch下载失败)
```

---

## 当前任务状态

| 阶段 | 任务 | 状态 |
|------|------|------|
| 第零阶段 | GitHub资源下载 | ✅ 已完成 |
| 第一阶段 | 激活GPU环境并验证CUDA | ❌ 阻塞中 |
| 第二阶段 | 训练高精度车辆检测模型 | ⏸️ 等待GPU环境 |
| 第二阶段 | 优化头盔检测模型 | ⏸️ 等待GPU环境 |
| 第三阶段 | 模型性能对比测试 | ⏸️ 等待训练完成 |
| 第三阶段 | 替换系统中的fallback模型 | ⏸️ 等待训练完成 |

---

## 相关任务文件

| 文件 | 路径 |
|------|------|
| 任务通知单 | [TASK-014_RESUME_GPU_TRAINING_MCP_INTEGRATION_NOTICE.md](file:///e:/output/TASK-014_RESUME_GPU_TRAINING_MCP_INTEGRATION_NOTICE.md) |
| 能力评估报告 | [TASK-013_CAPABILITY_ASSESSMENT_REPORT.md](file:///e:/output/TASK-013_CAPABILITY_ASSESSMENT_REPORT.md) |
| 工作进展报告 | [TASK-013_WORK_PROGRESS_REPORT.md](file:///e:/output/TASK-013_WORK_PROGRESS_REPORT.md) |
| 训练脚本 | [train.py](file:///e:/output/1/zhitong/training/train.py) |
| 项目根目录 | [zhitong](file:///e:/output/1/zhitong/) |

---

## 紧急处理建议

1. **优先解决P0-002**: 安装CUDA Toolkit 12.x
2. **同步解决P0-001**: 使用conda安装或手动下载whl
3. **解决P1-003**: 安装/定位conda环境
4. **解决P1-004**: 配置网络代理或使用国内镜像
5. **恢复训练**: 完成环境配置后继续车辆和头盔模型训练