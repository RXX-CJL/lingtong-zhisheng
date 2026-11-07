# -*- coding: utf-8 -*-
import cv2, os, numpy as np
os.chdir(r"E:\output\1\api\output\event_videos\20261101")
OUT = r"E:\output\_uicheck"
os.makedirs(OUT, exist_ok=True)

# 场景标注里的 4 个 traffic_light_roi
rois = [(988,110,1028,182),(1639,894,1793,945),(1129,119,1150,170),(1325,155,1345,200)]
print("ROI 列表:", rois)

for fname in ["evt_10550_6_3934e4_frame_89.jpg", "evt_10550_6_3934e4_frame_178.jpg"]:
    img = cv2.imread(fname)
    if img is None:
        print("读不到", fname); continue
    print("=" * 50)
    print(fname, img.shape)
    for i,(x1,y1,x2,y2) in enumerate(rois):
        x1,y1,x2,y2 = max(0,x1),max(0,y1),min(img.shape[1],x2),min(img.shape[0],y2)
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            print("  ROI%d 空" % i); continue
        # 放大 8 倍（最近邻，保留原始像素色，不插值污染）
        big = cv2.resize(crop, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
        out = os.path.join(OUT, "roi%d_%s" % (i, fname.replace('.jpg','.png')))
        cv2.imwrite(out, big)
        # 统计主色（BGR -> 找最亮像素）
        flat = crop.reshape(-1,3).astype(int)
        # 亮度最高的 10% 像素
        lum = flat.sum(axis=1)
        idx = np.argsort(lum)[-max(1,len(lum)//10):]
        top = flat[idx]
        b,g,r = top[:,0].mean(), top[:,1].mean(), top[:,2].mean()
        print("  ROI%d (%d,%d,%d,%d) 尺寸%d x %d | 最亮10%%均值 R=%.0f G=%.0f B=%.0f | -> %s" % (
            i,x1,y1,x2,y2, crop.shape[1], crop.shape[0], r,g,b,
            "偏红" if r>g+30 and r>b+30 else ("偏黄" if r>b+40 and g>b+40 else ("偏绿" if g>r+20 else "灰/白/暗"))))
