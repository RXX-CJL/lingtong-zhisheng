真值: frame<80 -> Green ; frame>=81 -> Red
CNN4 可用: True

====================================================================================
逐样本结果（共 11）
====================================================================================
      帧     真值      框尺寸   检测conf      CNN  CNNconf      HSV    CNN判定
     10  green    23x52      0.3   yellow     0.98   yellow ❌
     25  green    24x53     0.42   yellow     0.99   yellow ❌
     40  green    24x52     0.42   yellow     0.99   yellow ❌
     55  green    24x53     0.42   yellow      1.0   yellow ❌
     70  green    23x52     0.39   yellow     0.99   yellow ❌
     90    red    24x53     0.37   yellow      1.0   yellow ❌
    120    red    23x51     0.42   yellow     0.99   yellow ❌
    200    red    23x52     0.26   yellow     0.99   yellow ❌
    300    red    24x53     0.25   yellow      1.0   yellow ❌
    400    red    22x52     0.28   yellow     0.99   yellow ❌
    480    red    23x53     0.38   yellow     0.99   yellow ❌

====================================================================================
判色精度
====================================================================================
  CNN 给出有效判定的样本: 11/11
  其中判对: 0/11 = 0%
  Green 真值: 5 样本, CNN 判定分布 {'yellow': 5}
  Red 真值: 6 样本, CNN 判定分布 {'yellow': 6}

  【对照】HSV 兜底在同一批样本上的表现:
     HSV 判定分布: {'yellow': 11}
     HSV 判对: 0/11 (0%)

  拼图（上排=Green真值, 下排=Red真值；白字=真值, 彩字=CNN判定）: E:\output\_tl_review\tl_truth_grid.png
