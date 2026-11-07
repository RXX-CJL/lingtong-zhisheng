# -*- coding: utf-8 -*-
import cv2, json, sys
p = r'E:\output\1\carla\仿真输出\超速.mp4'
cap = cv2.VideoCapture(p)
if not cap.isOpened():
    print('FAIL 无法打开'); sys.exit(1)
fps = cap.get(cv2.CAP_PROP_FPS)
n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print('分辨率: %dx%d' % (w, h))
print('帧率: %.2f fps' % fps)
print('帧数: %d' % n)
print('时长: %.2f 秒' % (n/fps if fps else 0))
ok, fr = cap.read()
print('首帧可解码:', ok, '| 形状:', None if not ok else fr.shape)
cap.release()