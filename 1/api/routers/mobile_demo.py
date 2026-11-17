"""手机扫码演示路由（2026-11-17 新增）

设计目标：期中审查现场，让老师掏出手机扫个码就能参与演示，零安装。

约束与取舍：
  · 浏览器调 getUserMedia 需要 secure context（HTTPS 或 localhost），
    局域网 http://192.168.x.x 会被直接拒绝 —— 所以**不做手机实时推流**；
  · 但 <input type="file" capture> 调相机、<img> 显示 MJPEG 在 HTTP 下都可用，
    所以演示形态定为「扫码看大屏 + 扫码拍一张」。

端点：
  GET  /m                 手机落地页（两个按钮）
  GET  /demo              大屏演示页（二维码 + 最近上传墙）
  POST /api/demo/upload   手机拍照上传 → 走同一套检测 → 返回标注图
  GET  /api/demo/recent   最近上传的元数据（轻量，供轮询）
  GET  /api/demo/image/{id}  取某条上传的标注图
  GET  /api/demo/qr.png   二维码 PNG
"""
import base64
import io
import socket
import time
from collections import deque
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

router = APIRouter(tags=["手机扫码演示"])

# 最近上传的标注图，仅存内存。12 张足够现场展示，进程重启即清空。
_RECENT: deque = deque(maxlen=12)
_SEQ = 0


def _lan_ip() -> str:
    """取本机在局域网中的 IPv4。

    用 UDP connect 探路由，不真正发包；失败回退 127.0.0.1。
    手机扫码必须用局域网 IP，用 localhost 的二维码手机打不开。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class UploadFrame(BaseModel):
    frame: str          # base64 编码的 JPEG，允许带 data: 前缀
    device: str = "手机"


# ==================================================================
# 手机落地页
# ==================================================================
MOBILE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0A1628">
<title>智瞳灵声 · 视频接入</title>
<style>
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{height:100%;margin:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
       background:#000;color:#E8ECF4;overflow:hidden}
  #stage{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center}
  #out{width:100%;height:100%;object-fit:contain;display:none}
  #src{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}
  .hud{position:absolute;left:0;right:0;display:flex;align-items:center;gap:10px;padding:12px 16px;z-index:5}
  .hud.top{top:0;padding-top:calc(12px + env(safe-area-inset-top));
           background:linear-gradient(rgba(0,0,0,.72),rgba(0,0,0,0))}
  .hud.bottom{bottom:0;justify-content:center;padding-bottom:calc(16px + env(safe-area-inset-bottom));
              background:linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.72))}
  .brand{font-size:16px;font-weight:700;letter-spacing:1px}
  .stat{margin-left:auto;font-size:12px;color:#9FB3CC;font-variant-numeric:tabular-nums}
  .mini{background:#16A085;color:#fff;border:none;border-radius:22px;padding:13px 28px;
        font-size:15px;font-weight:600}
  .mini.ghost{background:rgba(34,54,77,.9);color:#C7D3E3}
  .mini:active{opacity:.8}
  .center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
          justify-content:center;padding:28px;text-align:center;gap:18px;z-index:6;background:#060C16}
  .center h1{margin:0;font-size:24px;letter-spacing:2px}
  .center p{margin:0;color:#8E9AAF;font-size:13px;line-height:1.9;max-width:340px}
  .warn{color:#F08A6A;font-size:13px;line-height:1.8;max-width:340px;
        background:rgba(229,89,52,.12);border:1px solid rgba(229,89,52,.4);
        border-radius:12px;padding:14px;text-align:left}
  .hidden{display:none!important}
</style>
</head>
<body>
<div id="stage">
  <img id="out" alt="检测画面">
  <video id="src" playsinline muted></video>

  <div class="hud top hidden" id="hudTop">
    <span class="brand">智瞳灵声 · 视频接入</span>
    <span class="stat" id="stat">连接中…</span>
  </div>

  <div class="hud bottom hidden" id="hudBottom">
    <button class="mini ghost" id="btnStop">停止</button>
    <button class="mini" id="btnFlip">切换镜头</button>
  </div>

  <div class="center" id="intro">
    <h1>接入这台设备</h1>
    <p>允许使用摄像头后，这台手机的画面会实时进入智瞳灵声的检测系统，识别结果同步显示在演示大屏。</p>
    <div class="warn hidden" id="warn"></div>
    <button class="mini" id="btnStart">开始推流</button>
  </div>
</div>
<script>
(function(){
  var $ = function(id){ return document.getElementById(id); };
  var running = false, facing = 'environment', stream = null;
  var canvas = document.createElement('canvas');
  var ctx = canvas.getContext('2d');
  var okCount = 0, lastStat = Date.now();

  // 非安全上下文（局域网 http://）下浏览器禁止调用摄像头。
  // 这是硬限制：点"继续前往"也不放行。降级为「查看系统实时画面」。
  if (!window.isSecureContext) {
    $('intro').classList.add('hidden');
    $('hudTop').classList.remove('hidden');
    var out0 = $('out');
    out0.style.display = 'block';
    out0.src = '/api/realtime/stream?_=' + Date.now();
    $('stat').textContent = '实时画面 · 推流需 HTTPS';
    return;
  }

  function setStat(t){ $('stat').textContent = t; }

  async function openCamera(){
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: facing }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false
    });
    var v = $('src');
    v.srcObject = stream;
    await v.play().catch(function(){});
  }

  async function start(){
    try {
      await openCamera();
    } catch (e) {
      $('warn').classList.remove('hidden');
      $('warn').textContent = '无法打开摄像头：' + ((e && e.message) || e);
      return;
    }
    $('intro').classList.add('hidden');
    $('hudTop').classList.remove('hidden');
    $('hudBottom').classList.remove('hidden');
    $('out').style.display = 'block';
    running = true;
    okCount = 0; lastStat = Date.now();
    setStat('推流中…');
    loop();
  }

  function capture(){
    var v = $('src');
    var w = v.videoWidth || 1280, h = v.videoHeight || 720;
    var scale = Math.min(1, 1280 / Math.max(w, h));
    canvas.width = Math.round(w * scale);
    canvas.height = Math.round(h * scale);
    ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.72).split(',')[1];
  }

  async function loop(){
    while (running) {
      var t0 = Date.now();
      var b64;
      try { b64 = capture(); } catch (e) { break; }
      try {
        var r = await fetch('/api/realtime/detect-frame', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({frame: b64})
        });
        var d = await r.json();
        if (d && d.annotated_frame) {
          $('out').src = 'data:image/jpeg;base64,' + d.annotated_frame;
          okCount++;
        }
      } catch (e) { /* 单帧失败不中断 */ }

      var now = Date.now();
      if (now - lastStat > 1000) {
        setStat('推流中 · ' + (okCount * 1000 / (now - lastStat)).toFixed(1) + ' FPS');
        okCount = 0; lastStat = now;
      }
      var cost = Date.now() - t0;
      if (cost < 180) await new Promise(function(res){ setTimeout(res, 180 - cost); });
    }
  }

  function stop(){
    running = false;
    if (stream) { stream.getTracks().forEach(function(t){ t.stop(); }); stream = null; }
    $('intro').classList.remove('hidden');
    $('hudTop').classList.add('hidden');
    $('hudBottom').classList.add('hidden');
    $('out').style.display = 'none';
    setStat('已停止');
  }

  $('btnStart').addEventListener('click', start);
  $('btnStop').addEventListener('click', stop);
  $('btnFlip').addEventListener('click', function(){
    var was = running;
    running = false;
    setTimeout(function(){
      if (stream) { stream.getTracks().forEach(function(t){ t.stop(); }); stream = null; }
      facing = (facing === 'environment') ? 'user' : 'environment';
      if (was) start();
    }, 150);
  });
})();
</script>
</body>
</html>
"""


# ==================================================================
# 大屏演示页
# ==================================================================
SCREEN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>智瞳灵声 · 演示大屏</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;background:#0A1628;color:#E8ECF4;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
       display:flex;height:100vh;overflow:hidden}
  .left{width:340px;flex-shrink:0;display:flex;flex-direction:column;align-items:center;justify-content:center;
        padding:28px;background:#0D1E33;border-right:1px solid #1B3A5C}
  .left h2{margin:0 0 4px;font-size:19px;letter-spacing:1px}
  .left .hint{color:#7C8CA6;font-size:12px;margin:0 0 22px;text-align:center;line-height:1.7}
  .qr{width:230px;height:230px;background:#fff;border-radius:12px;padding:12px}
  .qr img{width:100%;height:100%;display:block}
  .addr{margin-top:16px;color:#16A085;font-size:13px;font-family:ui-monospace,Menlo,Consolas,monospace}
  .right{flex:1;padding:24px;overflow-y:auto;min-width:0}
  .right h3{margin:0 0 16px;font-size:15px;color:#8E9AAF;font-weight:500;letter-spacing:1px}
  .empty{color:#41546B;font-size:14px;margin-top:40px;text-align:center;line-height:2}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
  .card{background:#12263D;border-radius:12px;overflow:hidden;border:1px solid #1B3A5C;animation:in .3s ease}
  @keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .card img{width:100%;display:block;background:#000}
  .card .meta{padding:10px 12px;font-size:12px;color:#7C8CA6;display:flex;justify-content:space-between;gap:8px}
  .card .meta b{color:#16A085}
  .card .cls{padding:0 12px 12px;font-size:12px;color:#8E9AAF;line-height:1.6}
  .live{margin-bottom:22px;background:#12263D;border-radius:12px;overflow:hidden;border:1px solid #1B3A5C}
  .live img{width:100%;display:block;max-height:42vh;object-fit:contain;background:#000}
  .live .tag{padding:8px 12px;font-size:12px;color:#7C8CA6}
  .mode-switch{display:flex;gap:10px;margin-bottom:16px;align-items:center}
  .mode-switch .lb{color:#7C8CA6;font-size:13px;margin-right:4px}
  .mode-switch button{background:#12263D;color:#8E9AAF;border:1px solid #1B3A5C;border-radius:10px;
    padding:10px 18px;font-size:14px;cursor:pointer;transition:all .15s}
  .mode-switch button:hover{border-color:#16A085}
  .mode-switch button.on{background:#16A085;color:#fff;border-color:#16A085;font-weight:600}
</style>
</head>
<body>
  <div class="left">
    <h2>扫码参与演示</h2>
    <p class="hint">用手机相机扫一下<br>无需安装任何应用</p>
    <div class="qr"><img src="/api/demo/qr.png" alt="二维码"></div>
    <div class="addr" id="addr">__URL__</div>
  </div>
  <div class="right">
    <div class="mode-switch">
      <span class="lb">识别类别</span>
      <button data-mode="traffic" class="on">交通模式</button>
      <button data-mode="all">全量识别</button>
    </div>
    <div class="live">
      <img src="/api/realtime/stream" alt="实时画面">
      <div class="tag">实时检测画面 · 手机拍照结果会出现在下方</div>
    </div>
    <h3>现场上传</h3>
    <div id="empty" class="empty">还没有人上传<br>让老师扫左边的码，拍一张试试</div>
    <div class="grid" id="grid"></div>
  </div>
<script>
(function(){
  var lastTop = -1;

  // ---- 识别类别切换（traffic / all）----
  function setActiveMode(m){
    var btns = document.querySelectorAll('.mode-switch button');
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle('on', btns[i].getAttribute('data-mode') === m);
    }
  }
  function loadMode(){
    fetch('/api/realtime/class-mode').then(function(r){ return r.json(); })
      .then(function(d){ if (d && d.mode) setActiveMode(d.mode); }).catch(function(){});
  }
  Array.prototype.forEach.call(document.querySelectorAll('.mode-switch button'), function(b){
    b.addEventListener('click', function(){
      var m = b.getAttribute('data-mode');
      fetch('/api/realtime/class-mode', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mode: m})
      }).then(function(r){ return r.json(); })
        .then(function(d){ if (d && d.success) setActiveMode(d.mode); })
        .catch(function(){});
    });
  });
  loadMode();
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  function poll(){
    fetch('/api/demo/recent').then(function(r){ return r.json(); }).then(function(res){
      var items = (res && res.items) || [];
      if (!items.length) return;
      var top = items[0].id;
      if (top === lastTop) return;
      lastTop = top;
      document.getElementById('empty').style.display = 'none';
      var html = items.map(function(it){
        return '<div class="card">' +
          '<img src="/api/demo/image/' + it.id + '?t=' + it.ts_ms + '" alt="上传画面">' +
          '<div class="meta"><b>' + (it.count||0) + ' 个目标</b><span>' + esc(it.time) + '</span></div>' +
          '<div class="cls">' + esc((it.classes||[]).join('、') || '无检出') + '</div>' +
        '</div>';
      }).join('');
      document.getElementById('grid').innerHTML = html;
    }).catch(function(){});
  }
  poll();
  setInterval(poll, 2000);
})();
</script>
</body>
</html>
"""


# ==================================================================
# API
# ==================================================================
@router.post("/api/demo/upload")
def demo_upload(req: UploadFrame):
    """手机拍照上传 → 走实时检测同一套管线 → 返回标注图并同步到大屏。"""
    global _SEQ
    t0 = time.time()
    try:
        raw = (req.frame or "").split(",")[-1].strip()
        if not raw:
            return {"success": False, "message": "没有收到图像数据"}
        if len(raw) > 16 * 1024 * 1024:
            return {"success": False, "message": "图片过大（超过 12MB）"}

        from realtime_detector import realtime_detector

        result = realtime_detector.detect_external_frame(raw)
        if not result or not result.get("success"):
            return {"success": False, "message": (result or {}).get("message", "检测失败")}

        dets = result.get("detections") or []
        # 去重保序，给前端展示"这一张认出了哪些类"
        classes = []
        for d in dets:
            name = str((d or {}).get("class_name") or (d or {}).get("class") or "").strip()
            if name and name not in classes:
                classes.append(name)

        _SEQ += 1
        item = {
            "id": _SEQ,
            "ts_ms": int(time.time() * 1000),
            "time": time.strftime("%H:%M:%S"),
            "count": len(dets),
            "classes": classes[:8],
            "annotated": result.get("annotated_frame") or "",
            "device": req.device or "手机",
        }
        _RECENT.appendleft(item)

        return {
            "success": True,
            "id": item["id"],
            "count": item["count"],
            "classes": item["classes"],
            "annotated": item["annotated"],
            "ms": int((time.time() - t0) * 1000),
        }
    except Exception as e:
        import logging
        logging.getLogger("zhitong_api").exception("手机上传识别失败")
        return {"success": False, "message": f"处理异常：{e}"}


@router.get("/api/demo/recent")
def demo_recent():
    """轻量列表：只有元数据，图片单独取，避免轮询时反复传大图。"""
    return {
        "items": [
            {"id": it["id"], "ts_ms": it["ts_ms"], "time": it["time"],
             "count": it["count"], "classes": it["classes"], "device": it["device"]}
            for it in _RECENT
        ]
    }


@router.get("/api/demo/image/{item_id}")
def demo_image(item_id: int):
    for it in _RECENT:
        if it["id"] == item_id:
            try:
                raw = base64.b64decode(it["annotated"])
                return Response(content=raw, media_type="image/jpeg",
                                headers={"Cache-Control": "public, max-age=3600"})
            except Exception:
                break
    return Response(status_code=404)


@router.get("/api/demo/qr.png")
def demo_qr(request: Request):
    """生成手机落地页的二维码。优先用局域网 IP，避免二维码扫进 localhost。"""
    try:
        import qrcode
    except ImportError:
        return Response(status_code=503, content=b"qrcode module not installed")

    # 允许 ?host= 覆盖（比如机器多网卡，自动选的不是连着手机的那块）
    host = request.query_params.get("host")
    if not host:
        host = f"{_lan_ip()}:{request.url.port or 8001}"

    url = f"http://{host}/m"
    img = qrcode.make(url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@router.get("/api/demo/url")
def demo_url(request: Request):
    """给前端/排查用：当前二维码指向的地址。"""
    host = request.query_params.get("host") or f"{_lan_ip()}:{request.url.port or 8001}"
    return {"url": f"http://{host}/m", "lan_ip": _lan_ip()}


@router.get("/m", response_class=HTMLResponse)
def mobile_page():
    return HTMLResponse(MOBILE_HTML)


@router.get("/demo", response_class=HTMLResponse)
def screen_page(request: Request):
    host = request.query_params.get("host") or f"{_lan_ip()}:{request.url.port or 8001}"
    return HTMLResponse(SCREEN_HTML.replace("__URL__", f"http://{host}/m"))
