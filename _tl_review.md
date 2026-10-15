CNN4 可用: True
找到权重候选: ['yolov8n.pt', 'yolov8n.pt', 'yolov8n.pt', 'yolov8n_pretrained.pt', 'yolov8n.pt']
已加载: yolov8n.pt

==============================================================================
判色复核结果
==============================================================================
  CARLA 2K: 检出红绿灯框 17 个
     判色分布: {'yellow': 16, 'none': 1}
  CARLA 简单 28s: 检出红绿灯框 5 个
     判色分布: {'yellow': 5}
  真实路口: 检出红绿灯框 5 个
     判色分布: {'red': 4, 'none': 1}

  合计 27 个框，判色分布: {'yellow': 21, 'none': 2, 'red': 4}
    yellow 占比: 78%   red 15%   green 0%   none 7%   unknown 0%

  ROI 拼图（供人工核对）: E:\output\_tl_review\tl_roi_grid.png   尺寸 880x570
  每格: 左上角=判定状态, 左下角=来源(cnn/hsv)
