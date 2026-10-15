"""批量修复"多反转一次通道"的 bug。

根因（2026-10-04 实测确认，见 _byteorder 实验）：
    CARLA sensor 的 raw_data 字节序是 **BGRA**，
    因此 `reshape(H,W,4)[:, :, :3]` 取到的**就是 BGR**，可直接交给 OpenCV。
    再加 `[:, :, ::-1]` 会把它变成 **RGB 却被当成 BGR 使用** -> 红蓝互换。
    后果：橙色路障读成 B 主导、红灯读成青蓝（整轮颜色结论被污染）。

修法：把 `[:, :, :3][:, :, ::-1]` 与后续的 `arr[:, :, ::-1]` 去掉。
本脚本**先备份**，再逐文件替换，并打印每处改动。
"""
import io
import os
import re
import shutil
import sys

ROOT = r"E:\output\_scripts"
BAK = r"E:\output\_scripts\_bak_byteorder"

# 明确要处理的文件（只改本轮我写的脚本；blind_yun.py 单独处理并请示）
TARGETS = [
    "_all_lights_states.py", "_b4_diff.py", "_calib3.py", "_calib_ground.py",
    "_calib_probe.py", "_capture_carla_lights.py", "_capture_honest.py",
    "_capture_lens.py", "_close_lamp.py", "_compare_window_vs_client.py",
    "_confirm_frame.py", "_demo_scene.py", "_diag_postprocess.py",
    "_dual_cam_demo.py", "_find_headcam.py", "_find_headcam2.py", "_find_headcam3.py",
    "_find_signals.py", "_fix_coord_test.py", "_fix_lightboxes.py", "_grab_frame.py",
    "_ground_map.py", "_lightup_sweep.py", "_lightup_sweep2.py", "_lightup_sweep3.py",
    "_lens_rows.py", "_lit_check.py", "_match_window_look.py", "_match_window_look2.py",
    "_minimal_test.py", "_overlay_all.py", "_preview_candidates.py", "_probe_head.py",
    "_raw_lamp_check.py", "_raw_lamp_check2.py", "_red_control_test.py",
    "_redlight_colour_check.py", "_reference_frame.py", "_render_view_options.py",
    "_res_test.py", "_resolve_light17.py", "_scan_lamps.py", "_settle_box_interp.py",
    "_verify_B.py", "_verify_user_cam.py", "_control_test.py", "_control_test2.py",
]

PATTERNS = [
    # 内联：...reshape(...)[:, :, :3][:, :, ::-1].copy()  -> 去掉反转
    (re.compile(r"\[:, :, :3\]\[:, :, ::-1\]\.copy\(\)"), "[:, :, :3].copy()"),
    (re.compile(r"\[:, :, :3\]\[:, :, ::-1\]"), "[:, :, :3]"),
    # 独立一行：arr = arr[:, :, ::-1].copy()   -> 整行删除
    (re.compile(r"^[ \t]*\w+ = \w+\[:, :, ::-1\]\.copy\(\)[ \t]*(\r?\n)", re.M), ""),
    # 带注释的：...[:, :, ::-1].copy()   # xxx
    (re.compile(r"\[:, :, ::-1\]\.copy\(\)[ \t]*#[^\r\n]*"), ".copy()"),
]


def main():
    os.makedirs(BAK, exist_ok=True)
    total = 0
    changed_files = []
    for name in TARGETS:
        p = os.path.join(ROOT, name)
        if not os.path.exists(p):
            continue
        src = io.open(p, encoding="utf-8").read()
        orig = src
        hits = []
        for pat, rep in PATTERNS:
            src, n = pat.subn(rep, src)
            if n:
                hits.append(n)
        if src != orig:
            shutil.copy2(p, os.path.join(BAK, name))
            io.open(p, "w", encoding="utf-8", newline="").write(src)
            total += sum(hits)
            changed_files.append((name, sum(hits)))
            print("  修复 %-38s %d 处" % (name, sum(hits)))
    print("\n共修改 %d 个文件，%d 处" % (len(changed_files), total))
    print("备份目录: %s" % BAK)

    # 校验：还有没有残留
    print("\n残留检查（应无输出）:")
    left = []
    for name in TARGETS:
        p = os.path.join(ROOT, name)
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding="utf-8").read()
        for m in re.finditer(r"^.*\[:, :, ::-1\].*$", s, re.M):
            left.append((name, m.group(0).strip()))
    for name, line in left:
        print("  %-38s %s" % (name, line))
    if not left:
        print("  （无残留）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
