配置: ground_plane（缺省 8.0m / -20.0°）
各 y 处 ppm:
   y=  102  ppm=    0.14
   y=  141  ppm=    0.45
   y=  200  ppm=    1.28
   y=  300  ppm=    3.63
   y=  500  ppm=   11.98
   y=  800  ppm=   33.54
   y= 1080  ppm=   63.48

=== 出问题的真实数值复现（之前算出 158.6 km/h）===
  y≈118, 32.96px/s  ->  kmh=0.0  conf=unavailable  q=too_far
     note=目标过远（ppm=0.2 < 3.0），几何精度不足，不输出速度

=== 正常近处目标（应正常输出）===
  y=1080, 100px/s  ->  kmh=5.7  conf=assumed  q=ok
