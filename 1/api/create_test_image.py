import cv2
import numpy as np
import os

img = np.zeros((480, 640, 3), dtype=np.uint8)

cv2.rectangle(img, (500, 50), (580, 150), (50, 50, 50), -1)
cv2.circle(img, (540, 80), 25, (0, 0, 255), -1)
cv2.circle(img, (540, 120), 20, (50, 50, 50), -1)

cv2.rectangle(img, (100, 300), (300, 400), (100, 100, 150), -1)
cv2.rectangle(img, (120, 320), (280, 380), (80, 80, 120), -1)
cv2.circle(img, (140, 395), 15, (30, 30, 30), -1)
cv2.circle(img, (280, 395), 15, (30, 30, 30), -1)

cv2.rectangle(img, (350, 320), (550, 420), (150, 100, 50), -1)
cv2.rectangle(img, (370, 350), (530, 400), (120, 80, 40), -1)
cv2.rectangle(img, (530, 360), (560, 420), (80, 80, 80), -1)

cv2.rectangle(img, (50, 350), (100, 450), (60, 60, 60), -1)
cv2.circle(img, (75, 340), 10, (255, 255, 255), -1)
cv2.circle(img, (60, 445), 15, (30, 30, 30), -1)
cv2.circle(img, (90, 445), 15, (30, 30, 30), -1)

output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'zhitong', 'data', 'test_images')
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, 'test_traffic.jpg')
cv2.imwrite(output_path, img)
print(f"测试图片已创建: {output_path}")
