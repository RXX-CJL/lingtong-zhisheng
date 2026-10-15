exists: True
行数: 145
  L26: _MODEL_PATH = r"E:\output\_tl_color_cls\tl_color_cnn4.pt"
  L37: def _ensure_loaded() -> bool:
  L49: if not os.path.exists(_MODEL_PATH):
  L63: ck = torch.load(_MODEL_PATH, map_location=dev, weights_only=False)
  L75: def classify_traffic_light(roi_bgr: np.ndarray,
  L118: def hsv_fallback_state(roi_bgr: np.ndarray) -> str:
  L143: def is_available() -> bool:
