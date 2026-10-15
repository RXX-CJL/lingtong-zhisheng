"""Settle the colour question with pixels, not argument.

For each signal head visible in the frames the user has been looking at:
  - sample the HOUSING (the solid body of the signal)
  - sample the LIT LENS (brightest compact region on it)
Print BGR / HSV / hue for each, plus the plain-language colour name, and write a
swatch strip so the actual colours are visible side by side.
"""
import glob
import os
import sys

import cv2
import numpy as np

OUT = r"E:\output\_tl_glow_eval"
os.makedirs(OUT, exist_ok=True)

FRAMES = [
    r"E:\output\_camera_verify\reference_1080.png",
    r"E:\output\_camera_verify\confirm_1080.png",
    r"E:\output\_camera_check\frame_raw.png",
]


def name_colour(b, g, r):
    """Plain-language name from BGR, using hue + saturation + value."""
    px = np.uint8([[[b, g, r]]])
    h, s, v = cv2.cvtColor(px, cv2.COLOR_BGR2HSV)[0, 0]
    hue = int(h) * 2
    if s < 40:
        return "grey/white (hue %.0f, sat %d)" % (hue, s) if v > 120 else "dark grey"
    if hue < 15 or hue >= 345:
        return "RED (hue %d)" % hue
    if hue < 45:
        return "ORANGE/BROWN (hue %d)" % hue
    if hue < 70:
        return "YELLOW (hue %d)" % hue
    if hue < 100:
        return "YELLOW-GREEN (hue %d)" % hue
    if hue < 150:
        return "GREEN (hue %d)" % hue
    if hue < 200:
        return "CYAN (hue %d)" % hue
    if hue < 260:
        return "BLUE (hue %d)" % hue
    return "PURPLE/MAGENTA (hue %d)" % hue


def sample_at(img, x, y, label, half=6):
    x0, y0 = max(0, x - half), max(0, y - half)
    patch = img[y0:y0 + 2 * half + 1, x0:x0 + 2 * half + 1]
    if patch.size == 0:
        return None
    b, g, r = [float(patch[:, :, i].mean()) for i in range(3)]
    return {"label": label, "xy": (x, y), "b": b, "g": g, "r": r,
            "name": name_colour(int(b), int(g), int(r))}


def main():
    rows = []
    swatches = []
    for f in FRAMES:
        if not os.path.exists(f):
            print("missing:", f)
            continue
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        H, W = img.shape[:2]
        print("\n" + "=" * 96)
        print("%s   (%dx%d)" % (os.path.basename(f), W, H))
        print("=" * 96)

        # the traffic-light lamp positions I previously reported for this camera
        probes = []
        if W == 1920:
            probes = [("TL9 lamp (reported)", 1238, 133),
                      ("TL18 lamp (reported)", 111, 137),
                      ("TL10 lamp (reported)", 30, 686) if H == 720 else ("TL10 lamp", 30, 1029)]
        else:
            probes = [("TL9 lamp", 824, 89), ("TL18 lamp", 74, 91)]
        for label, x, y in probes:
            if not (0 <= x < W and 0 <= y < H):
                continue
            s = sample_at(img, x, y, label)
            if s:
                rows.append(s)
                print("  %-26s at (%4d,%4d)  BGR=(%5.1f,%5.1f,%5.1f)  -> %s"
                      % (s["label"], x, y, s["b"], s["g"], s["r"], s["name"]))
                swatches.append((s, (int(s["b"]), int(s["g"]), int(s["r"]))))

        # also: find all bright lamp-like spots in the upper 40% and name their colour
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        v = hsv[:, :, 2].astype(np.int16)
        s_ = hsv[:, :, 1].astype(np.int16)
        mask = ((v > 140) & (s_ > 60)).astype(np.uint8)
        mask[int(H * 0.42):, :] = 0
        mask = cv2.morphologyEx(mask * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
        found = []
        for i in range(1, n):
            a = int(stats[i, cv2.CC_STAT_AREA])
            if a < 25 or a > 3000:
                continue
            w_, h_ = int(stats[i, cv2.CC_STAT_WIDTH]), int(stats[i, cv2.CC_STAT_HEIGHT])
            if max(w_, h_) / max(1, min(w_, h_)) > 4:
                continue
            found.append((a, cent[i], w_, h_))
        found.sort(key=lambda t: -t[0])
        print("  -- bright/saturated compact spots in the upper 42%% of frame --")
        for a, c, w_, h_ in found[:10]:
            s = sample_at(img, int(c[0]), int(c[1]), "spot")
            if s:
                print("     area=%-5d (%4d,%4d) %2dx%-2d  BGR=(%5.1f,%5.1f,%5.1f)  %s"
                      % (a, c[0], c[1], w_, h_, s["b"], s["g"], s["r"], s["name"]))

    # swatch strip
    if swatches:
        tile_w, tile_h = 190, 120
        cols = 6
        tiles = []
        for s, bgr in swatches:
            t = np.zeros((tile_h, tile_w, 3), np.uint8)
            t[:80] = bgr
            txt = s["name"].replace(" (hue", " h")
            cv2.putText(t, s["label"][:24], (4, 96), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(t, txt[:30], (4, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)
            tiles.append(t)
        while len(tiles) % cols:
            tiles.append(np.zeros((tile_h, tile_w, 3), np.uint8))
        sheet = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
        p = os.path.join(OUT, "colour_swatches.png")
        cv2.imwrite(p, sheet)
        print("\nwrote %s  (each swatch = the actual sampled pixels, with its measured name)" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
