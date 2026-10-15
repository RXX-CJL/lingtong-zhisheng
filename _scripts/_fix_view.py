"""守法车"停在停止线却出画"的补救方案分析（纯几何，用已验证投影）。

约束：只能动相机（用户只要求"视角就这样"，但若给出量化选项由用户定）。
目标：两车在停止线/路口区域都完整在画面内（车宽约 2.0 m，需中心 |u-960| < 800 才留边）。
"""
import math
import numpy as np

W, H, FOV = 1920, 1080, 90.0
F = W / (2 * math.tan(math.radians(FOV) / 2))

STOP = np.array([-25.61, -61.71])        # 停止线
LANE1_Y, LANE2_Y = -64.7, -68.2          # 左道 / 右道中心
FAR_STOP_X = -68.44


def R_of(pitch, yaw, roll=0.0):
    p, y, r = map(math.radians, (pitch, yaw, roll))
    cz, sz = math.cos(y), math.sin(y)
    cp, sp = math.cos(p), math.sin(p)
    cx, sx = math.cos(r), math.sin(r)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    return Rz @ Ry @ Rx


def project(cam, R, p):
    vc = R.T @ (np.asarray(p, float) - np.asarray(cam, float))
    if vc[0] <= 1e-6:
        return None
    return (W / 2 + F * (vc[1] / vc[0]), H / 2 - F * (vc[2] / vc[0]), float(vc[0]))


CAR_LEN, CAR_W = 4.6, 2.0


def car_visible_fraction(cam, R, cx, cy, z=0.8):
    """把车当成沿 x 轴 4.6m、宽 2.0m 的矩形，采样看有多少角的投影在画面内。"""
    pts = []
    for dx in np.linspace(-CAR_LEN / 2, CAR_LEN / 2, 5):
        for dy in (-CAR_W / 2, CAR_W / 2):
            pts.append([cx + dx, cy + dy, z])
    inside = 0
    for p in pts:
        r = project(cam, R, p)
        if r and 0 <= r[0] < W and 0 <= r[1] < H:
            inside += 1
    return inside / len(pts)


def evaluate(cam, pitch, yaw, label):
    R = R_of(pitch, yaw)
    line = "  %-42s" % label
    ok = True
    for tag, cx, cy in (("左车@停止线", STOP[0], LANE1_Y),
                        ("右车@停止线", STOP[0], LANE2_Y),
                        ("左车@路口中心", -29.09, LANE1_Y),
                        ("左车@对面停止线", FAR_STOP_X, LANE1_Y),
                        ("右车@对面停止线", FAR_STOP_X, LANE2_Y)):
        fr = car_visible_fraction(cam, R, cx, cy)
        line += " %s=%.0f%%" % (tag[:6], fr * 100)
        if fr < 0.9:
            ok = False
    print(line + ("   <-- 全可见" if ok else ""))
    return ok


def main():
    print("画面内可见比例（100% = 整辆车都在画面里）\n")
    print("=== 现状 ===")
    evaluate([-19.720, -63.145, 5.732], -23.445, 179.536, "现状 (%.1f,%.1f,%.1f) p=%.1f" % (-19.720, -63.145, 5.732, -23.445))

    print("\n=== 方案 1：相机后移（沿 +x），保持高度/俯角 ===")
    for dx in (4, 8, 12, 16, 20, 26):
        evaluate([-19.720 + dx, -63.145, 5.732], -23.445, 179.536,
                 "后移 %2d m -> x=%.1f" % (dx, -19.720 + dx))

    print("\n=== 方案 2：抬高并减小俯角（后移 8 m）===")
    for z, p in ((7.0, -20.0), (8.0, -18.0), (9.0, -16.0), (10.0, -15.0)):
        evaluate([-19.720 + 8, -63.145, z], p, 179.536, "z=%.1f pitch=%.1f" % (z, p))

    print("\n=== 方案 3：当前位置只抬高 ===")
    for z, p in ((7.0, -20.0), (8.0, -18.0), (9.5, -16.0), (11.0, -14.0)):
        evaluate([-19.720, -63.145, z], p, 179.536, "z=%.1f pitch=%.1f" % (z, p))
    return 0


if __name__ == "__main__":
    main()
