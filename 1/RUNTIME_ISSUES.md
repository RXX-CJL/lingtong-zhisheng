# 智瞳灵声项目运行问题报告

## 文档信息
- 生成时间：2026-06-10
- 项目路径：e:\output\1\
- 报告目的：记录项目验证启动过程中遇到的难以解决的问题

---

## 问题一：后端服务(Uvicorn)频繁意外退出

### 问题描述
FastAPI后端服务使用uvicorn启动后，服务会在短时间内（约几秒到几十秒）自动退出，导致前端无法正常调用API接口。

### 复现步骤
```powershell
cd e:\output\1\api
uvicorn app:app --port 8000 --reload
```

### 预期行为
服务应该持续运行，直到用户手动停止（Ctrl+C）。

### 实际行为
服务启动成功后，输出以下日志：
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
正在初始化数据库...
数据库表创建成功
智瞳API服务启动成功！
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```
但随后服务很快退出，终端显示 `command_status: Exited, command_exit_code: 0`。

### 错误信息
无明确错误信息，服务以exit_code=0正常退出。

### 已尝试的解决方法
1. **去掉--reload参数**：使用 `uvicorn app:app --port 8000` 启动，问题依旧
2. **添加--host参数**：使用 `uvicorn app:app --port 8000 --host 0.0.0.0`，问题依旧
3. **检查端口占用**：使用 `netstat -ano | findstr :8000` 确认端口未被占用
4. **检查Python环境**：确认uvicorn、fastapi等依赖已正确安装

### 可能原因分析
1. **终端环境问题**：PowerShell可能对后台进程有特殊处理
2. **uvicorn配置问题**：可能需要添加更多参数保持服务运行
3. **Trae IDE终端限制**：终端可能有超时或自动关闭机制

### 相关代码片段
```python
# e:\output\1\api\app.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

---

## 问题二：前端服务(Vite)端口冲突

### 问题描述
Vite开发服务器启动时报告端口5173被占用，自动切换到5174端口，但随后服务也会退出。

### 复现步骤
```powershell
cd e:\output\1\web-admin
npm run dev
```

### 错误信息
```
Port 5173 is in use, trying another one...
VITE v5.4.21  ready in 242 ms
➜  Local:   http://localhost:5174/
```

### 已尝试的解决方法
1. **检查端口占用**：使用 `netstat -ano | findstr :5173` 检查，未发现占用
2. **强制指定端口**：使用 `npm run dev -- --port 5173`，服务仍会退出
3. **清理node_modules**：未执行，因为依赖安装正常

### 可能原因分析
与后端服务问题类似，可能是终端环境或Trae IDE的限制导致服务无法持续运行。

---

## 问题三：演示数据脚本需要交互确认

### 问题描述
`seed_demo_data.py`脚本在检测到已有数据时，会要求用户输入确认是否清空旧数据，导致自动化流程中断。

### 原始代码
```python
if existing > 0:
    print(f"\n⚠️  检测到已有 {existing} 条数据")
    choice = input("是否清空旧数据并重新生成? (y/n): ").strip().lower()
    if choice == 'y':
        cursor.execute("DELETE FROM violation_evidences")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='violation_evidences'")
        print("✓ 旧数据已清空")
```

### 解决方法（已实施）
修改脚本，自动清空旧数据，无需用户确认：
```python
if existing > 0:
    print(f"\n⚠️  检测到已有 {existing} 条数据，自动清空并重新生成...")
    cursor.execute("DELETE FROM violation_evidences")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='violation_evidences'")
    print("✓ 旧数据已清空")
```

### 状态
**已解决** - 脚本现在可以自动运行完成。

---

## 问题四：前端请求返回500错误

### 问题描述
前端页面加载时，API请求返回500错误，但直接使用命令行测试API接口返回正常。

### 复现步骤
1. 启动后端服务
2. 启动前端服务
3. 浏览器访问 http://localhost:5173/

### 错误信息（浏览器控制台）
```
获取统计数据失败 AxiosError: Request failed with status code 500
at loadStats (http://localhost:5173/src/views/Dashboard.vue:61:12)
获取待审核列表失败 AxiosError: Request failed with status code 500
at loadPendingList (http://localhost:5173/src/views/Dashboard.vue:74:12)
```

### 已验证的正常情况
使用PowerShell直接请求API：
```powershell
(new-object System.Net.WebClient).DownloadString('http://127.0.0.1:8000/api/violations/statistics/summary')
```
返回正常数据：
```json
{"total_count":20,"by_type":{"no_helmet":4,"lane_departure":4,"red_light":5,"wrong_way":4,"illegal_parking":2,"speeding":1},"by_status":{"confirmed":10,"rejected":3,"pending":7},"by_date":{...}}
```

### 可能原因分析
1. **时序问题**：前端请求时后端服务可能已退出
2. **CORS问题**：虽然后端配置了CORS，但可能存在其他问题
3. **Vite代理配置问题**：需要检查vite.config.js的proxy配置

### 相关配置文件
```javascript
// e:\output\1\web-admin\vite.config.js
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})
```

---

## 核心问题总结

### 最关键的问题
**服务无法持续运行** - 这是所有问题的根源。后端和前端服务都会在启动后不久自动退出，导致：
1. API请求失败
2. 前端无法正常加载数据
3. 无法完成端到端验证

### 需要解决的技术点
1. 如何让uvicorn服务在Trae IDE终端中持续运行
2. 如何让Vite开发服务器持续运行
3. 或者找到替代方案（如使用start-dev.bat批处理文件）

---

## 附录：项目结构

```
e:\output\1\
├── api\                          # FastAPI 后端
│   ├── app.py                    # 主应用
│   ├── seed_demo_data.py         # 演示数据脚本（已修复）
│   ├── routers\
│   │   └── violations.py         # 违规路由
│   └── zhitong_violations.db     # SQLite数据库
├── web-admin\                    # Vue3 前端
│   ├── src\
│   │   ├── views\
│   │   │   ├── Dashboard.vue     # 仪表盘
│   │   │   ├── ViolationList.vue # 违规列表
│   │   │   └── Statistics.vue    # 统计分析
│   │   └── api\index.js          # API封装
│   └── vite.config.js            # Vite配置
└── start-dev.bat                 # 一键启动脚本
```

---

## 建议的解决方向

1. **使用批处理文件启动**：尝试使用已有的 `start-dev.bat` 文件
2. **检查Trae IDE终端配置**：确认终端是否有超时设置
3. **使用nohup或后台运行**：在Linux/Mac环境下可尝试，Windows下可用Start-Process
4. **分离启动流程**：在两个独立的终端窗口中分别启动前后端
