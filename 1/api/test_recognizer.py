import sys
sys.path.insert(0, 'e:\\output\\1\\api')

print("Testing image_recognizer import...")
from image_recognizer import analyze_image, detect_with_yolo, analyze_with_doubao

print("Import successful!")

# 测试检测
test_image = 'uploads/violation_b0b9a3ad_20260609_112733.jpg'
print(f"\nTesting YOLO detection on {test_image}...")
result = detect_with_yolo(test_image)
print(f"YOLO Result: {result}")

print("\nTesting Doubao analysis...")
result = analyze_with_doubao(test_image, 'lane_departure')
print(f"Doubao Result: {result}")

print("\nTesting complete analysis...")
result = analyze_image(test_image, 'lane_departure')
print(f"Final Result: {result}")