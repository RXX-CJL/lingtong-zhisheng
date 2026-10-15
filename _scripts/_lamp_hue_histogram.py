"""Unambiguous check: what colours do the LAMPS themselves have in the user's view?

Uses only strongly-saturated bright pixels (the lit lens cores), reports each
blob's colour and position, and prints the overall hue histogram of lit-lens
pixels so there is no ambiguity about "what colour are the lights".
"""
import os
import sys

import cv2
import numpy as np

FRAMES = [
    (r"E:\output\_camera_verify\reference_1080.png", "reference (no overlay)"),
    (r"E:\output\_camera_verify\confirm_1080.png", "confirm (no overlay areas)"),
    (r"E:\output\_camera_check\frame_raw.png", "frame_raw 720p"),
]
OUT = r"E:\output\_tl_glow_eval\lamp_colour_histogram.png"


def hue_name(hue, sat):
    if sat < 50:
        return "unsaturated"
    if hue < 15 or hue >= 345:
        return "RED"
    if hue < 45:
        return "ORANGE/BROWN"
    if hue < 70:
        return "YELLOW"
    if hue < 100:
        return "YELLOW-GREEN"
    if hue < 150:
        return "GREEN"
    if hue < 200:
        return "CYAN"
    if hue < 260:
        return "BLUE"
    return "PURPLE"


def main():
    for path, tag in FRAMES:
        if not os.path.exists(path):
            continue
        img = cv2.imread(path)
        H, W = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hh, ss, vv = hsv[:, :, 0].astype(np.int16), hsv[:, :, 1].astype(np.int16), hsv[:, :, 2].astype(np.int16)
        # lit lens cores: strongly saturated AND bright, upper 45% of the frame
        m = (ss > 130) & (vv > 150)
        m[int(H * 0.45):, :] = False
        bins = {}
        for h in hh[m]:
            bins[int(h) * 2] = bins.get(int(h) * 2, 0) + 1
        print("\n" + "=" * 88)
        print("%s  (%dx%d)   lit-lens pixels: %d" % (tag, W, H, int(m.sum())))
        print("=" * 88)
        if bins:
            top = sorted(bins.items(), key=lambda t: -t[1])[:10]
            for hue, n in top:
                print("   hue %3d  n=%-6d  -> %s" % (hue, n, hue_name(hue, 200)))
            # group by name
            grp = {}
            for hue, n in bins.items():
                k = hue_name(hue, 200)
                grp[k] = grp.get(k, 0) + n
            print("   --- grouped: %s" % sorted(grp.items(), key=lambda t: -t[1]))
        else:
            print("   no strongly-saturated bright pixels in the upper 45%")

        # locate the blobs
        mm = cv2.morphologyEx((m.astype(np.uint8)) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(mm, 8)
        found = []
        for i in range(1, n):
            a = int(stats[i, cv2.CC_STAT_AREA])
            if a < 40:
                continue
            found.append((a, cent[i], int(stats[i, cv2.CC_STAT_WIDTH]), int(stats[i, cv2.CC_STAT_HEIGHT])))
        found.sort(key=lambda t: -t[0])
        print("   blobs (area>=40):")
        for a, c, w_, h_ in found[:8]:
            b, g, r = [int(img[int(c[1]), int(c[0]), i]) for i in range(3)]
            hval = int(hsv[int(c[1]), int(c[0]), 0]) * 2
            print("      area=%-6d (%4d,%4d) %3dx%-3d  BGR=(%3d,%3d,%3d) hue=%3d -> %s"
                  % (a, c[0], c[1], w_, h_, b, g, r, hval, hue_name(hval, 200)))

        # swatch strip of those blob colours
        tiles = []
        for a, c, w_, h_ in found[:8]:
            b, g, r = [int(img[int(c[1]), int(c[0]), i]) for i in range(3)]
            t = np.zeros((70, 130, 3), np.uint8)
            t[:50] = (b, g, r)
            cv2.putText(t, "(%d,%d)" % (c[0], c[1]), (3, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            tiles.append(t)
        if tiles:
            while len(tiles) % 8:
                tiles.append(np.zeros((70, 130, 3), np.uint8))
            cv2.imwrite(OUT, np.hstack(tiles))
    print("\nwrote %s  (swatches = actual lamp pixel colours)" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
