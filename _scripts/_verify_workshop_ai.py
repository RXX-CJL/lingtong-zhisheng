# -*- coding: utf-8 -*-
r"""AI 化验收：--headless + 剧本。全程零交互，超时即失败。

用法：py -3.12 -X utf8 E:\output\_scripts\_verify_workshop_ai.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WORKSHOP = r"E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py"
PY = sys.executable
PASS = 0
FAIL = 0
FAILED = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(name)
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))


def run(args, timeout=180):
    """跑一条命令，返回 (exit, stdout, elapsed)。超时返回 (-1, ..., elapsed)。"""
    t0 = time.time()
    try:
        proc = subprocess.run([PY, "-X", "utf8", WORKSHOP] + args,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or ""), time.time() - t0
    except subprocess.TimeoutExpired:
        return -1, "<TIMEOUT>", time.time() - t0


def ffprobe(path):
    r"""用 cv2 读视频元信息。

    不用 ffprobe：本机 ffprobe 是 C:/Users/ROG/.local/bin/ffprobe.cmd 包装脚本，
    Windows 下 subprocess 不能直接执行 .cmd（WinError 2），会静默拿不到数据。
    cv2.VideoCapture 走已安装的 OpenCV，零外部依赖。
    """
    try:
        import cv2
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return {}
        data = {
            "streams": [{
                "codec_name": "h264" if _looks_like_h264(path) else "unknown",
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "r_frame_rate": "%d/1" % int(cap.get(cv2.CAP_PROP_FPS)),
                "nb_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            }],
            "format": {},
        }
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        if fps > 0:
            data["format"]["duration"] = "%.3f" % (frames / fps)
        cap.release()
        return data
    except Exception as exc:
        print("  cv2 读视频失败:", exc)
        return {}


def _looks_like_h264(path):
    """MP4 里 codec tag 是 avc1/avc3 即 H.264。"""
    try:
        blob = Path(path).read_bytes()
        return b"avc1" in blob[:200000] or b"avc3" in blob[:200000]
    except Exception:
        return False


print("=" * 70)
print("A. --print-schema（给 AI 看的自描述）")
print("=" * 70)
code, out, _ = run(["--print-schema"], timeout=60)
check("print-schema exit 0", code == 0, code)
check("print-schema 含格式名", "carla_workshop_recipe_v1" in out, "")
check("print-schema 含动作清单", "behavior" in out and "tl_durations" in out, "")

print()
print("=" * 70)
print("B. --selftest（坏剧本必须给出清晰中文错误，且 exit != 0）")
print("=" * 70)
tmp = Path(tempfile.mkdtemp(prefix="workshop_ai_"))

bad_cases = [
    ("坏 JSON", "{ not json", "不是合法 JSON"),
    ("未知动作", json.dumps({"format": "carla_workshop_recipe_v1",
                          "actions": [{"t": 0, "do": "fly_to_moon"}]}), "不受支持"),
    ("非法行为模式", json.dumps({"format": "carla_workshop_recipe_v1",
                           "actions": [{"t": 0, "do": "behavior", "vehicle": 0, "mode": "jump"}]}), "mode"),
    ("缺 kmh", json.dumps({"format": "carla_workshop_recipe_v1",
                         "actions": [{"t": 0, "do": "speed", "vehicle": 0}]}), "kmh"),
    ("非法 label", json.dumps({"format": "carla_workshop_recipe_v1",
                             "actions": [{"t": 0, "do": "hide", "label": "Cars"}]}), "label"),
    ("格式版本错", json.dumps({"format": "v999", "actions": []}), "format"),
]
for name, body, keyword in bad_cases:
    p = tmp / "bad.json"
    p.write_text(body, encoding="utf-8")
    code, out, _ = run(["--selftest", "--recipe", str(p)], timeout=60)
    ok = code != 0 and (keyword in out or "校验失败" in out or "错误" in out)
    check("selftest 拒绝：" + name, ok, "exit=%s keyword=%s" % (code, keyword))

print()
print("=" * 70)
print("C. 端到端：一条命令出片，零交互")
print("=" * 70)
out_mp4 = tmp / "ai_test.mp4"
recipe = {
    "format": "carla_workshop_recipe_v1",
    "title": "AI 化验收",
    "hide": [{"action": "range", "label": "Vegetation", "radius": 40, "mode": "球体"}],
    "actions": [
        {"t": 0.0, "do": "log", "text": "开始"},
        {"t": 0.5, "do": "show_all"},
        {"t": 1.0, "do": "wait", "seconds": 0.5},
    ],
    "record": {"seconds": 4, "fps": 20, "resolution": "960x540", "out": str(out_mp4)},
    "cleanup": {"restore_hidden": True, "restore_traffic_lights": True,
                "destroy_vehicles": True, "restore_camera": True},
}
recipe_path = tmp / "recipe.json"
recipe_path.write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding="utf-8")

code, out, elapsed = run(["--recipe", str(recipe_path)], timeout=180)
check("recipe exit 0", code == 0, code)
check("全程未超时（零交互）", code != -1, "%.1fs" % elapsed)
check("无 headless 弹窗记录", "[warn]" not in out and "[error]" not in out,
      out.count("[warn]") + out.count("[error]"))
check("视频文件已生成", out_mp4.is_file(), str(out_mp4))
if out_mp4.is_file():
    # ffmpeg 关 stdin 后还要一小会儿才写完 moov；立刻 ffprobe 会读到"有文件但无流"
    info = {}
    for _ in range(20):
        info = ffprobe(out_mp4)
        if (info.get("streams") or []) and (info.get("format") or {}).get("duration"):
            break
        time.sleep(0.5)
    stream = (info.get("streams") or [{}])[0]
    duration = float((info.get("format") or {}).get("duration", 0))
    frames = int(stream.get("nb_frames", 0) or 0)
    check("视频 codec 是 h264", stream.get("codec_name") == "h264", stream.get("codec_name"))
    check("视频分辨率 960x540",
          (stream.get("width"), stream.get("height")) == (960, 540),
          (stream.get("width"), stream.get("height")))
    check("视频时长 ≈ 4 秒（±0.6）", abs(duration - 4.0) <= 0.6, "%.2fs" % duration)
    check("视频帧数 ≈ 80（4s×20fps，±15）", abs(frames - 80) <= 15, frames)
    check("视频大小 > 100KB", out_mp4.stat().st_size > 100 * 1024, out_mp4.stat().st_size)

print()
print("=" * 70)
print("D. 幂等收尾：跑完世界必须回到基线")
print("=" * 70)
# 先清理"验收脚本自己"可能留下的残留（历史教训：验证脚本的调试对象会被误判成产品缺陷）
subprocess.run([PY, "-X", "utf8", r"E:\output\_scripts\_cleanup_test_actors.py"],
               capture_output=True, text=True, timeout=120)
probe = subprocess.run(
    [PY, "-X", "utf8", r"E:\output\_scripts\_probe_final_state.py"],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
ptext = probe.stdout or ""
check("收尾后 actor 总数 23", "总 actor 数 = 23" in ptext, ptext.split("\n")[0][:80])
check("收尾后无车辆/道具/相机",
      "vehicle: 0" in ptext and "prop: 0" in ptext and "cam: 0" in ptext, "")
check("收尾后红绿灯全 10/3/2", "配时异常: 无" in ptext or "无（全部 10/3/2）" in ptext, "")

print()
print("RESULT PASS=%d FAIL=%d" % (PASS, FAIL))
if FAILED:
    print("FAILED:", FAILED)
sys.exit(0 if FAIL == 0 else 1)
