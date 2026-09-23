# K230 车牌检测/识别 HTTP 协议

## 概述

K230 板载服务提供车牌检测和识别能力，PC 端通过 HTTP API 调用。

- **K230 服务端口**: 8080
- **通信协议**: HTTP POST + JSON
- **图像编码**: Base64 (JPEG)

## 接口列表

### 1. 健康检查
`GET /health`

**响应**:
```json
{"success": true, "status": "ok"}
```

### 2. 服务状态
`GET /status`

**响应**:
```json
{
  "success": true,
  "models_loaded": true,
  "det_model": "/sdcard/kmodel/LPD_640.kmodel",
  "rec_model": "/sdcard/kmodel/licence_reco.kmodel"
}
```

### 3. 车牌检测
`POST /detect_plate`

**请求**:
```json
{
  "path": "/detect_plate",
  "image": "<base64 JPEG>"
}
```

**响应**:
```json
{
  "success": true,
  "detections": [
    {"bbox": [100, 200, 300, 250], "confidence": 0.85}
  ]
}
```

### 4. 车牌识别
`POST /recognize_plate`

**请求**:
```json
{
  "path": "/recognize_plate",
  "image": "<base64 JPEG 车牌裁剪图>"
}
```

**响应**:
```json
{
  "success": true,
  "plate_number": "京A12345",
  "confidence": 0.92
}
```

### 5. 检测+识别（一步完成）
`POST /detect_and_recognize`

**请求**:
```json
{
  "path": "/detect_and_recognize",
  "image": "<base64 JPEG 完整图>"
}
```

**响应**:
```json
{
  "success": true,
  "plate_number": "京A12345",
  "confidence": 0.78,
  "bbox": [100, 200, 300, 250]
}
```

## 错误码

| HTTP Status | 含义 | 处理方式 |
|-------------|------|---------|
| 200 | 成功 | - |
| 400 | 请求格式错误 | 检查 JSON 格式 |
| 500 | 服务内部错误 | 检查 K230 模型是否加载 |
| 连接超时 | K230 未启动 | PC 端自动降级跳过 |

## PC 端降级策略

当 K230 不可达时：
1. `detect_via_k230()` 返回空列表 `[]`
2. `recognize_via_k230()` 返回 `{'plate_number': '', 'confidence': 0.0}`
3. `detect_and_recognize()` 返回空结构
4. 不抛异常，不阻塞主流程

## K230 端部署

1. 将 `plate_server.py` 拷贝到 K230 的 `/sdcard/` 目录
2. 确保 `/sdcard/kmodel/LPD_640.kmodel` 和 `/sdcard/kmodel/licence_reco.kmodel` 存在
3. 确保 `/sdcard/libs/` 目录包含 PipeLine.py, AIBase.py, AI2D.py 等依赖
4. 运行: `python plate_server.py`
5. K230 WiFi 需与 PC 在同一网段

## 模型信息

| 模型 | 文件 | 输入尺寸 | 用途 |
|------|------|---------|------|
| LPD_640 | LPD_640.kmodel | 640x640 | 车牌定位 |
| licence_reco | licence_reco.kmodel | 220x32 | 车牌字符识别 |

字符字典包含：34 个省份/特殊字 + 10 个数字 + 24 个字母(I/O 不含) + 2 个特殊符
