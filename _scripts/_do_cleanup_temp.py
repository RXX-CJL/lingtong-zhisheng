# -*- coding: utf-8 -*-
"""安全删除本轮临时调试脚本：显式白名单 + 删前打印绝对路径 + 只删 _scripts 下。"""
import os
from pathlib import Path

D = Path(r"E:\output\_scripts").resolve()
print("目标目录:", D)
print("目录存在:", D.is_dir())

TEMP = [
    "_baseline_snap.py", "_diag_noise_floor.py", "_diag_pick.py", "_diag_pick2.py",
    "_diag_pick3.py", "_diag_pick4.py", "_diag_pose.py", "_diag_pose2.py",
    "_diag_render.py", "_diag_replay.py", "_diag_sibling.py", "_diag_spec2.py",
    "_diag_steal.py", "_diag_timing.py", "_probe_cam_fps.py", "_probe_cam_fps2.py",
    "_probe_cam_leak.py", "_probe_clean.py", "_probe_clean2.py", "_probe_env_objects.py",
    "_probe_env_perf.py", "_probe_ffprobe.py", "_probe_lights.py", "_probe_lights2.py",
    "_probe_rec_timing.py", "_probe_spawn_pt.py", "_probe_spec.py", "_probe_weather_fields.py",
    "_restore_all_env.py", "_restore_cam2.py", "_restore_cam3.py", "_restore_camera.py",
    "_restore_lights.py", "_smoke_headless.py", "_wait_carla.py", "_list_temp_scripts.py",
    "_verify_headless_isolation.py",
    # 子代理遗留的一次性探针
    "_verify_workshop_env_probe.py", "_verify_workshop_env_probe2.py",
    "_verify_workshop_env_probe3.py", "_verify_workshop_env_probe4.py",
    "_verify_workshop_env_probe5.py", "_verify_workshop_env_pickdbg.py",
    "_verify_workshop_env_spect.py",
]

KEEP = [
    "_world_state.py", "_cleanup_test_actors.py",
    "_verify_workshop_ai.py", "_verify_workshop_env_live.py", "_verify_workshop_env_offline.py",
    "_verify_scene_v2_mock.py", "_verify_workshop_gui.py",
    "_verify_workshop_scene_v2.py", "_verify_workshop_scene_v2_offline.py",
    "_verify_gui_real_window.py", "_verify_headless_guard.py", "_verify_headless_reversible.py",
    "_verify_recipe_gui_handoff.py", "_verify_world_state_diff.py", "_probe_final_state.py",
    "_verify_workshop_projection.py", "_verify_workshop_drag_flow.py",
    "_verify_workshop_live_carla.py", "_verify_workshop_menu_live.py",
    "_verify_workshop_behavior_live.py",
]

# 安全闸：KEEP 与 TEMP 不得重叠
overlap = set(KEEP) & set(TEMP)
if overlap:
    print("拒绝删除：以下文件同时出现在保留清单里:", overlap)
    raise SystemExit(1)

deleted, missing = 0, []
for name in TEMP:
    p = (D / name)
    # 安全检查：必须真实位于 _scripts 下，且是文件
    if p.resolve().parent != D:
        print("跳过（路径越界）:", p)
        continue
    if not p.is_file():
        missing.append(name)
        continue
    print("删除:", p)
    p.unlink()
    deleted += 1

print("\n已删除 %d 个；不存在 %d 个" % (deleted, len(missing)))
if missing:
    print("不存在的:", missing)

print("\n保留清单核对：")
for name in KEEP:
    p = D / name
    print("   %s %s" % ("OK " if p.is_file() else "缺失", name))
