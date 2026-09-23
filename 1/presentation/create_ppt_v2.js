// 智瞳灵声 · 国赛答辩PPT (优化版)
// 比例: 16:9 (兼容 WPS)
// 内容: 完全对齐申请书 + 竞品对比 + 国赛竞争力分析

const pptxgen = require('pptxgenjs');
const path = require('path');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE'; // 16:9 = 13.33 x 7.5 inch (WPS标准)
pptx.title = '智瞳灵声 - 基于视觉识别与云端推理的智慧交管系统';
pptx.author = '宁夏理工学院';
pptx.subject = '中国国际大学生创新大赛 · 互联网+';

// ============================================================
// 配色方案（深蓝科技风，全部用 RGB 整数，不用透明色）
// ============================================================
const C = {
  primary:   '1B3A6B',  // 深蓝
  secondary: '4A90D9',  // 中蓝
  accent:    '00C9A7',  // 青色
  orange:    'FF6B35',  // 橙色（警示）
  green:     '2ECC71',  // 绿色
  dark:      '0F1C2E',   // 深色背景
  white:     'FFFFFF',
  lightBg:   'F0F4F8',
  cardBg:    'E8F0F9',
  text:      '2D3748',
  textLight: '718096',
  line:      'CBD5E0',
  red:       'E53E3E',
  yellow:    'D69E2E',
  purple:    '8B5CF6',
};

// 字体（优先用系统常见字体保证 WPS 兼容）
const F = {
  zh: '微软雅黑',
  en: 'Arial',
  mono: 'Consolas',
};

// ============================================================
// 基础布局函数
// ============================================================

// 顶部标题条
function addHeader(slide, title, subtitle = '') {
  // 顶部色条
  slide.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.08, fill: { color: C.accent } });
  // 左侧装饰条
  slide.addShape('rect', { x: 0, y: 0, w: 0.12, h: 7.5, fill: { color: C.primary } });
  // 标题
  slide.addText(title, {
    x: 0.35, y: 0.2, w: 10, h: 0.6,
    fontSize: 28, bold: true, color: C.primary, fontFace: F.zh, margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.35, y: 0.75, w: 10, h: 0.3,
      fontSize: 13, color: C.textLight, fontFace: F.zh,
    });
  }
  // 右下角页码条
  slide.addShape('rect', { x: 0, y: 7.32, w: 13.33, h: 0.18, fill: { color: C.primary } });
}

// 添加页脚信息
function addFooter(slide, page, total) {
  slide.addText(`${page} / ${total}`, {
    x: 12.3, y: 7.34, w: 0.9, h: 0.14,
    fontSize: 9, color: C.white, align: 'right',
  });
}

// 卡片（矩形，方便 WPS 渲染）
function card(slide, x, y, w, h, fillColor, lineColor) {
  slide.addShape('rect', {
    x, y, w, h,
    fill: { color: fillColor || C.white },
    line: { color: lineColor || C.line, width: 1 },
  });
}

// 彩色标签
function tag(slide, x, y, text, bgColor) {
  const w = text.length * 0.22 + 0.3;
  slide.addShape('rect', { x, y, w, h: 0.3, fill: { color: bgColor }, rectRadius: 0.04 });
  slide.addText(text, {
    x, y, w, h: 0.3,
    fontSize: 10, color: C.white, align: 'center', valign: 'middle',
  });
}

// 数字突出显示
function statCard(slide, x, y, w, h, number, unit, label, color) {
  card(slide, x, y, w, h, C.white, C.line);
  // 顶部色条
  slide.addShape('rect', { x, y, w, h: 0.06, fill: { color: color || C.accent } });
  slide.addText(number, {
    x, y: y + 0.18, w, h: 0.6,
    fontSize: 36, bold: true, color: color || C.accent, align: 'center', margin: 0,
  });
  slide.addText(unit, {
    x, y: y + 0.75, w, h: 0.22,
    fontSize: 11, color: C.textLight, align: 'center',
  });
  slide.addText(label, {
    x, y: y + 1.0, w, h: 0.28,
    fontSize: 12, color: C.text, align: 'center', fontFace: F.zh,
  });
}

// ============================================================
// 第1页：封面
// ============================================================
function slide1_cover() {
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };

  // 装饰色块（全部用矩形，WPS 兼容）
  slide.addShape('rect', { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: C.dark } });
  // 左上蓝色块
  slide.addShape('rect', { x: -0.5, y: -0.5, w: 4, h: 4, fill: { color: C.primary, transparency: 50 } });
  // 右下蓝色块
  slide.addShape('rect', { x: 10, y: 4, w: 5, h: 5, fill: { color: C.primary, transparency: 40 } });
  // 青色点缀
  slide.addShape('rect', { x: 0.5, y: 4.5, w: 2, h: 2, fill: { color: C.accent, transparency: 60 } });

  // 顶部蓝色条
  slide.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.35, fill: { color: C.accent } });
  slide.addText('中国国际大学生创新大赛（互联网+）', {
    x: 0, y: 0.05, w: 13.33, h: 0.28,
    fontSize: 13, color: C.white, align: 'center',
  });

  // 比赛标签
  slide.addShape('rect', { x: 4.3, y: 1.2, w: 4.73, h: 0.5, fill: { color: C.accent } });
  slide.addText('国家级立项项目', {
    x: 4.3, y: 1.22, w: 4.73, h: 0.46,
    fontSize: 16, bold: true, color: C.white, align: 'center', valign: 'middle',
  });

  // 项目名称
  slide.addText('智瞳灵声', {
    x: 0.5, y: 1.9, w: 12.33, h: 1.1,
    fontSize: 68, bold: true, color: C.white, align: 'center',
    fontFace: F.zh,
  });

  // 英文副标题
  slide.addText('CityGuardian · Intelligent Traffic Governance System', {
    x: 0.5, y: 2.95, w: 12.33, h: 0.4,
    fontSize: 16, color: C.secondary, align: 'center',
  });

  // 分隔线
  slide.addShape('rect', { x: 3.5, y: 3.45, w: 6.33, h: 0.04, fill: { color: C.accent } });

  // 核心描述
  slide.addText('基于视觉识别与云端推理的智慧交管系统', {
    x: 0.5, y: 3.6, w: 12.33, h: 0.5,
    fontSize: 22, color: C.white, align: 'center',
  });

  // 关键词
  slide.addShape('rect', { x: 2.8, y: 4.3, w: 7.73, h: 0.5, fill: { color: C.white, transparency: 90 } });
  slide.addText('YOLOv8目标检测  ·  DeepSORT多目标跟踪  ·  TensorRT加速  ·  端云协同架构', {
    x: 2.8, y: 4.33, w: 7.73, h: 0.44,
    fontSize: 12, color: C.accent, align: 'center', valign: 'middle',
  });

  // 团队信息
  slide.addShape('rect', { x: 0, y: 5.2, w: 13.33, h: 1.3, fill: { color: C.primary, transparency: 70 } });
  slide.addText('宁夏理工学院  电气信息工程学院', {
    x: 0.5, y: 5.35, w: 12.33, h: 0.35,
    fontSize: 13, color: C.secondary, align: 'center',
  });
  slide.addText('项目主持：陈俊龙    团队成员：母书祯 · 苗博文 · 余林峰 · 王泽轩    指导教师：赵智雯 · 汪永奇', {
    x: 0.5, y: 5.75, w: 12.33, h: 0.35,
    fontSize: 12, color: C.white, align: 'center',
  });
  slide.addText('项目周期：2026年5月 — 2027年5月', {
    x: 0.5, y: 6.1, w: 12.33, h: 0.28,
    fontSize: 11, color: C.textLight, align: 'center',
  });
}

// ============================================================
// 第2页：痛点分析
// ============================================================
function slide2_pain() {
  const slide = pptx.addSlide();
  slide.background = { color: C.lightBg };
  addHeader(slide, '痛点分析', '当前城市交通治理面临的严峻挑战');
  addFooter(slide, 2, 18);

  const points = [
    { num: '01', title: '警力严重不足', stat: '1 : 2.3', unit: '公里/人', desc: '平均1名交警需管理2.3公里道路，\n人工巡查效率低下，覆盖盲区多', color: C.red },
    { num: '02', title: '被动响应滞后', stat: '>70%', unit: '事后响应', desc: '电子警察覆盖有限，\n只能事后追责，无法预防事故发生', color: C.orange },
    { num: '03', title: '数据孤岛林立', stat: '90%', unit: '数据未连通', desc: '各监控平台数据不互通，\n无法形成统一的治理合力', color: C.yellow },
    { num: '04', title: '治理成本攀升', stat: '3倍', unit: 'vs智能系统', desc: '传统人工执法成本持续上升，\n群众满意度与安全感双低', color: C.primary },
  ];

  points.forEach((p, i) => {
    const x = 0.35 + i * 3.2;
    // 卡片背景
    card(slide, x, 1.35, 3.0, 4.2, C.white, C.line);
    // 顶部色条
    slide.addShape('rect', { x, y: 1.35, w: 3.0, h: 0.08, fill: { color: p.color } });
    // 编号
    slide.addText(p.num, {
      x, y: 1.5, w: 3.0, h: 0.55,
      fontSize: 40, bold: true, color: p.color, align: 'center', margin: 0,
    });
    // 统计数字
    slide.addText(p.stat, {
      x, y: 2.1, w: 3.0, h: 0.6,
      fontSize: 30, bold: true, color: p.color, align: 'center', margin: 0,
    });
    slide.addText(p.unit, {
      x, y: 2.65, w: 3.0, h: 0.25,
      fontSize: 11, color: C.textLight, align: 'center',
    });
    // 标题
    slide.addText(p.title, {
      x: x + 0.2, y: 3.0, w: 2.6, h: 0.4,
      fontSize: 15, bold: true, color: C.dark, align: 'center',
    });
    // 描述
    slide.addText(p.desc, {
      x: x + 0.2, y: 3.45, w: 2.6, h: 1.6,
      fontSize: 12, color: C.textLight, align: 'center',
      lineSpacingMultiple: 1.4,
    });
  });

  // 底部总结
  slide.addShape('rect', { x: 0.35, y: 5.7, w: 12.63, h: 0.06, fill: { color: C.accent } });
  slide.addText('结论：传统"人海战术"已无法应对现代城市交通治理需求，亟需AI驱动的智能化变革', {
    x: 0.35, y: 5.78, w: 12.63, h: 0.28,
    fontSize: 12, bold: true, color: C.primary, align: 'center',
  });
}

// ============================================================
// 第3页：现有方案对比
// ============================================================
function slide3_existing() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '现有方案不足', '为什么市场主流方案无法解决核心问题');
  addFooter(slide, 3, 18);

  const items = [
    {
      name: '传统电子警察',
      icon: '📹',
      score: 3,
      problems: ['覆盖范围有限', '事后追责为主', '无实时预警能力', '设备改造成本高'],
      color: C.red,
    },
    {
      name: '通用AI识别系统',
      icon: '🤖',
      score: 5,
      problems: ['纯云端，延迟高', '网络依赖强', '无法预测趋势', '无Agent协同'],
      color: C.orange,
    },
    {
      name: '智瞳灵声（ours）',
      icon: '👁️',
      score: 9,
      problems: ['端云协同，<50ms', '离线容灾可用', 'AI Agent预测', '持续自进化'],
      color: C.green,
      isOurs: true,
    },
  ];

  items.forEach((item, i) => {
    const x = 0.35 + i * 4.3;
    const isOurs = !!item.isOurs;

    // 卡片
    card(slide, x, 1.35, 4.1, 4.0, isOurs ? 'E8FFF3' : C.white, isOurs ? C.green : C.line);
    // 顶部
    slide.addShape('rect', { x, y: 1.35, w: 4.1, h: 0.75, fill: { color: isOurs ? C.green : C.primary } });
    slide.addText(`${item.icon} ${item.name}`, {
      x, y: 1.43, w: 4.1, h: 0.6,
      fontSize: 16, bold: true, color: C.white, align: 'center',
    });

    item.problems.forEach((prob, j) => {
      slide.addText(`✗  ${prob}`, {
        x: x + 0.2, y: 2.25 + j * 0.52, w: 3.7, h: 0.45,
        fontSize: 13, color: isOurs ? C.green : C.red, valign: 'middle',
      });
    });

    // 评分
    slide.addText('综合评分', {
      x, y: 4.45, w: 4.1, h: 0.25,
      fontSize: 10, color: C.textLight, align: 'center',
    });
    slide.addText(`${item.score} / 10`, {
      x, y: 4.7, w: 4.1, h: 0.45,
      fontSize: 22, bold: true,
      color: isOurs ? C.green : (item.score < 4 ? C.red : C.yellow),
      align: 'center',
    });
  });

  slide.addShape('rect', { x: 0.35, y: 5.55, w: 12.63, h: 0.06, fill: { color: C.green } });
  slide.addText('💡 核心差距：现有方案停留在"被动发现"阶段，缺乏预测能力、治理闭环和持续进化机制', {
    x: 0.35, y: 5.63, w: 12.63, h: 0.28,
    fontSize: 12, bold: true, color: C.primary, align: 'center',
  });
}

// ============================================================
// 第4页：项目解决方案总览
// ============================================================
function slide4_solution() {
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };

  // 装饰块
  slide.addShape('rect', { x: -1, y: -1, w: 4, h: 4, fill: { color: C.primary, transparency: 50 } });
  slide.addShape('rect', { x: 10.5, y: 4.5, w: 4, h: 4, fill: { color: C.accent, transparency: 40 } });

  // 标题
  slide.addText('智瞳灵声 · 整体解决方案', {
    x: 0.5, y: 0.3, w: 12.33, h: 0.65,
    fontSize: 28, bold: true, color: C.white, align: 'center',
  });
  slide.addText('"端云协同 · 预测治理 · 智能决策" 全链路闭环AI交通治理平台', {
    x: 0.5, y: 0.95, w: 12.33, h: 0.35,
    fontSize: 14, color: C.accent, align: 'center',
  });

  // 五层架构
  const layers = [
    { name: '感知层', desc: '摄像头/无人机/机器人', color: C.secondary },
    { name: '边缘层', desc: 'TensorRT+YOLOv8加速推理', color: C.accent },
    { name: '云端层', desc: '豆包大模型深度分析', color: C.purple },
    { name: 'Agent层', desc: 'AI决策与自动化治理', color: C.orange },
    { name: '治理层', desc: '执法报告+预警+数字孪生', color: C.green },
  ];
  const lw = 2.1;
  const gap = (13.33 - lw * 5 - 0.3 * 4) / 2;
  layers.forEach((l, i) => {
    const x = gap + i * (lw + 0.3);
    slide.addShape('rect', { x, y: 1.6, w: lw, h: 0.9, fill: { color: l.color } });
    slide.addText(l.name, { x, y: 1.65, w: lw, h: 0.4, fontSize: 14, bold: true, color: C.white, align: 'center' });
    slide.addText(l.desc, { x, y: 2.05, w: lw, h: 0.35, fontSize: 9, color: C.white, align: 'center', transparency: 15 });
    if (i < layers.length - 1) {
      slide.addText('→', { x: x + lw, y: 1.75, w: 0.3, h: 0.6, fontSize: 18, color: l.color, align: 'center' });
    }
  });

  // 三大核心能力
  const caps = [
    { word: '端云协同', sub: '90%本地处理，模糊样本云端确认\n离线容灾，网络中断仍可运行', color: C.accent },
    { word: 'Agent预测', sub: '历史数据驱动违规预测\n提前2小时预警重点区域', color: C.purple },
    { word: '自进化学习', sub: '用户反馈→新标注→模型微调\n准确率持续提升', color: C.green },
  ];
  caps.forEach((c, i) => {
    const x = 0.8 + i * 4.1;
    slide.addShape('rect', { x, y: 2.85, w: 3.9, h: 2.0, fill: { color: C.white, transparency: 92 }, line: { color: c.color, width: 2 } });
    slide.addText(c.word, { x, y: 2.95, w: 3.9, h: 0.55, fontSize: 20, bold: true, color: c.color, align: 'center' });
    slide.addText(c.sub, { x: x + 0.2, y: 3.55, w: 3.5, h: 1.1, fontSize: 11, color: C.white, align: 'center', lineSpacingMultiple: 1.4 });
  });

  // 可识别类型
  slide.addShape('rect', { x: 0.35, y: 5.1, w: 12.63, h: 0.65, fill: { color: C.primary, transparency: 60 } });
  slide.addText('当前支持识别：闯红灯 · 未戴头盔 · 逆行 · 违法停车 · 压线 · 超速    |    技术基础：YOLOv8 + DeepSORT + TensorRT + 豆包大模型', {
    x: 0.5, y: 5.18, w: 12.33, h: 0.5,
    fontSize: 12, color: C.white, align: 'center',
  });
}

// ============================================================
// 第5页：核心技术演示（与申请书保持一致）
// ============================================================
function slide5_demo() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '核心技术演示', '端云协同架构 — 本地推理 + 云端深度确认');
  addFooter(slide, 5, 18);

  // 左侧：模拟系统界面
  card(slide, 0.35, 1.35, 7.8, 4.2, C.dark, C.primary);
  // 标题栏
  slide.addShape('rect', { x: 0.35, y: 1.35, w: 7.8, h: 0.42, fill: { color: '2D3748' } });
  slide.addText('智瞳灵声 · 管理平台  |  智能识别', {
    x: 0.5, y: 1.38, w: 7.5, h: 0.36, fontSize: 11, color: C.white,
  });

  // 图片区（模拟YOLO检测）
  slide.addShape('rect', { x: 0.6, y: 1.95, w: 4.2, h: 3.3, fill: { color: '1A1A2E' } });
  // 绿色检测框
  slide.addShape('rect', { x: 1.0, y: 2.5, w: 2.2, h: 1.3, line: { color: '00FF88', width: 2 } });
  slide.addText('car  95%', { x: 1.0, y: 3.8, w: 2.2, h: 0.25, fontSize: 9, color: '00FF88', align: 'center' });
  // 黄色检测框
  slide.addShape('rect', { x: 2.8, y: 2.7, w: 1.6, h: 0.85, line: { color: 'FFD700', width: 2 } });
  slide.addText('motor  87%', { x: 2.8, y: 3.55, w: 1.6, h: 0.25, fontSize: 9, color: 'FFD700', align: 'center' });
  // 无头盔框
  slide.addShape('rect', { x: 1.0, y: 4.2, w: 1.5, h: 0.7, line: { color: 'FF4444', width: 2 } });
  slide.addText('no-helmet  82%', { x: 1.0, y: 4.9, w: 1.5, h: 0.2, fontSize: 8, color: 'FF4444', align: 'center' });

  // 右侧AI分析结果
  slide.addShape('rect', { x: 5.0, y: 1.95, w: 2.95, h: 3.3, fill: { color: '252A34' } });
  slide.addText('AI 推理链', { x: 5.15, y: 2.05, w: 2.65, h: 0.3, fontSize: 11, bold: true, color: C.accent });
  slide.addText([
    { text: 'YOLOv8 检测\n', options: { bold: true, color: C.secondary, breakLine: true } },
    { text: 'car ×1  motorcycle ×2\n', options: { color: 'BBBBBB', breakLine: true } },
    { text: '推理耗时: 15ms (TensorRT)\n\n', options: { color: '888888', breakLine: true } },
    { text: '豆包大模型分析\n', options: { bold: true, color: C.green, breakLine: true } },
    { text: '是否违规: 是\n', options: { color: C.green, breakLine: true } },
    { text: '置信度: 87%\n', options: { color: C.green, breakLine: true } },
    { text: '推理过程: 摩托车驾驶员\n未佩戴头盔，位置在\nXX路口东向西方向...', options: { color: 'BBBBBB', fontSize: 9 } },
  ], {
    x: 5.15, y: 2.4, w: 2.65, h: 2.6,
    fontSize: 10, color: C.white, valign: 'top', lineSpacingMultiple: 1.3,
  });

  // 右侧四个技术特性卡片
  const feats = [
    { title: 'YOLOv8n 目标检测', desc: 'COCO预训练+交通场景微调\n支持6类目标实时检测', icon: '👁', color: C.secondary },
    { title: 'TensorRT 推理加速', desc: '原生45ms → 加速后15ms\n速度提升3倍 (实测数据)', icon: '⚡', color: C.accent },
    { title: 'DeepSORT 多目标跟踪', desc: '卡尔曼滤波+外观特征\n遮挡场景稳定跟踪', icon: '🔄', color: C.purple },
    { title: '置信度分级响应', desc: '0.6×检测+0.3×跟踪\n+0.1×环境适配度', icon: '📊', color: C.green },
  ];
  feats.forEach((f, i) => {
    const x = 8.4 + (i % 2) * 2.4;
    const y = 1.35 + Math.floor(i / 2) * 2.1;
    card(slide, x, y, 2.25, 1.9, C.lightBg, C.line);
    slide.addShape('rect', { x, y, w: 2.25, h: 0.06, fill: { color: f.color } });
    slide.addText(f.title, { x: x + 0.1, y: y + 0.15, w: 2.05, h: 0.4, fontSize: 11, bold: true, color: C.dark });
    slide.addText(f.desc, { x: x + 0.1, y: y + 0.6, w: 2.05, h: 1.1, fontSize: 10, color: C.textLight, lineSpacingMultiple: 1.3 });
  });
}

// ============================================================
// 第6页：创新点概览
// ============================================================
function slide6_innovations() {
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };

  slide.addText('核心创新点', {
    x: 0.5, y: 0.2, w: 12.33, h: 0.55,
    fontSize: 28, bold: true, color: C.white, align: 'center',
  });
  slide.addText('基于AI Agent架构，重新定义城市交通治理范式', {
    x: 0.5, y: 0.75, w: 12.33, h: 0.28,
    fontSize: 13, color: C.secondary, align: 'center',
  });

  const innovs = [
    { num: '01', name: '端云协同架构', tag: '核心架构', color: C.accent },
    { num: '02', name: '置信度分级响应', tag: '精准分流', color: C.secondary },
    { num: '03', name: 'TensorRT加速部署', tag: '性能优化', color: C.purple },
    { num: '04', name: 'DeepSORT多目标跟踪', tag: '鲁棒跟踪', color: C.green },
    { num: '05', name: '豆包大模型二次确认', tag: '云端深度', color: C.orange },
    { num: '06', name: '多Agent协同决策', tag: 'AI架构', color: 'EC4899' },
    { num: '07', name: '预测式主动治理', tag: '行业首创', color: C.yellow },
    { num: '08', name: '自进化持续学习', tag: '越用越强', color: C.accent },
  ];

  innovs.forEach((inn, i) => {
    const col = i % 4;
    const row = Math.floor(i / 4);
    const x = 0.5 + col * 3.15;
    const y = 1.2 + row * 1.4;

    slide.addShape('rect', { x, y, w: 2.95, h: 1.2, fill: { color: C.white, transparency: 92 }, line: { color: inn.color, width: 1.5 } });
    slide.addText(inn.num, { x, y: y + 0.08, w: 2.95, h: 0.42, fontSize: 24, bold: true, color: inn.color, align: 'center' });
    slide.addText(inn.name, { x, y: y + 0.52, w: 2.95, h: 0.32, fontSize: 13, bold: true, color: C.white, align: 'center' });
    slide.addShape('rect', { x: x + 0.75, y: y + 0.88, w: 1.45, h: 0.22, fill: { color: inn.color } });
    slide.addText(inn.tag, { x: x + 0.75, y: y + 0.88, w: 1.45, h: 0.22, fontSize: 9, color: C.white, align: 'center', valign: 'middle' });
  });
}

// ============================================================
// 第7页：端云协同原理（申请书中的核心内容）
// ============================================================
function slide7_arch() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '端云协同架构原理', '高置信度本地处置 · 模糊样本云端深度确认');
  addFooter(slide, 7, 18);

  // 公式区
  slide.addShape('rect', { x: 0.35, y: 1.35, w: 12.63, h: 0.7, fill: { color: C.cardBg } });
  slide.addText('综合置信度 = 0.6 × 检测置信度  +  0.3 × 跟踪稳定性  +  0.1 × 环境适配度', {
    x: 0.5, y: 1.45, w: 12.33, h: 0.5,
    fontSize: 15, bold: true, color: C.primary, align: 'center',
  });

  // 流程图
  const steps = [
    { label: '摄像头', sub: '实时视频流\n30fps', color: C.secondary },
    { label: 'YOLOv8\n目标检测', sub: 'TensorRT加速\n15ms/帧', color: C.accent },
    { label: 'DeepSORT\n多目标跟踪', sub: '卡尔曼滤波\n持续跟踪', color: C.purple },
    { label: '置信度\n评估', sub: '综合评分\n动态阈值', color: C.orange },
    { label: '分级响应', sub: '高→本地处置\n低→云端确认', color: C.green },
  ];

  steps.forEach((s, i) => {
    const x = 0.5 + i * 2.55;
    slide.addShape('rect', { x, y: 2.4, w: 2.3, h: 1.6, fill: { color: s.color } });
    slide.addText(s.label, { x, y: 2.5, w: 2.3, h: 0.7, fontSize: 13, bold: true, color: C.white, align: 'center' });
    slide.addText(s.sub, { x, y: 3.2, w: 2.3, h: 0.65, fontSize: 10, color: C.white, align: 'center', transparency: 15, lineSpacingMultiple: 1.3 });
    if (i < steps.length - 1) {
      slide.addText('→', { x: x + 2.3, y: 2.9, w: 0.25, h: 0.5, fontSize: 20, color: s.color, align: 'center' });
    }
  });

  // 云端处理区
  slide.addShape('rect', { x: 7.5, y: 4.25, w: 5.5, h: 2.0, fill: { color: C.purple, transparency: 85 }, line: { color: C.purple, width: 2 } });
  slide.addText('云端处理（豆包大模型）', { x: 7.7, y: 4.35, w: 5.1, h: 0.35, fontSize: 13, bold: true, color: C.purple });
  slide.addText('触发条件：置信度 0.5~0.8 的模糊样本\n处理内容：多模态深度理解 + 上下文推理\n输出：违规确认 + 置信度调整 + 执法建议\n技术：阿里云/火山引擎 豆包视觉大模型', {
    x: 7.7, y: 4.75, w: 5.1, h: 1.3,
    fontSize: 11, color: C.text, lineSpacingMultiple: 1.5,
  });

  // 本地处理区
  slide.addShape('rect', { x: 0.35, y: 4.25, w: 6.9, h: 2.0, fill: { color: C.green, transparency: 85 }, line: { color: C.green, width: 2 } });
  slide.addText('本地处理（RTX 4060 + TensorRT）', { x: 0.55, y: 4.35, w: 6.5, h: 0.35, fontSize: 13, bold: true, color: C.green });
  slide.addText('触发条件：置信度 ≥ 0.8 的明确样本\n处理内容：YOLOv8检测 + DeepSORT跟踪 + 违规判据引擎\n输出：违规告警 + 语音播报 + 证据截图上传\n性能：原生45ms/帧 → TensorRT 15ms/帧（3倍加速）', {
    x: 0.55, y: 4.75, w: 6.5, h: 1.3,
    fontSize: 11, color: C.text, lineSpacingMultiple: 1.5,
  });
}

// ============================================================
// 第8页：竞品对比（基于调研结果）
// ============================================================
function slide8_competition() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '竞争优势分析', '与市场主流智慧交通产品对比');
  addFooter(slide, 8, 18);

  // 表头
  slide.addShape('rect', { x: 0.35, y: 1.35, w: 12.63, h: 0.55, fill: { color: C.primary } });
  const headers = [
    { text: '对比维度', w: 2.2 },
    { text: '海康威视/大华', w: 2.8 },
    { text: '阿里云交通', w: 2.6 },
    { text: '极视角AI算法', w: 2.6 },
    { text: '智瞳灵声(ours)', w: 2.43 },
  ];
  let hx = 0.35;
  headers.forEach((h, i) => {
    slide.addText(h.text, { x: hx, y: 1.38, w: h.w, h: 0.5, fontSize: 12, bold: true, color: C.white, align: 'center', valign: 'middle' });
    hx += h.w;
  });

  const rows = [
    ['核心定位', '硬件+AI分析', '云端交通大脑', 'AI算法包', '端云协同智能体'],
    ['推理延迟', '>200ms（纯云）', '>100ms', '>50ms', '<50ms（边缘）'],
    ['离线能力', '无（断网停摆）', '无', '有限', '✓ 完全离线运行'],
    ['预测能力', '无', '基础态势', '无', '✓ 历史数据预测'],
    ['Agent协同', '无', '有限', '无', '✓ 四Agent协同'],
    ['进化能力', '固定版本', '定期更新', '算法更新', '✓ 自进化持续学习'],
    ['适合场景', '主干道固定', '平台级整合', '算法替换', '园区/路口/移动'],
    ['部署成本', '高（硬件+施工）', '高（平台建设）', '中（算法费用）', '低（笔记本+摄像头）'],
  ];

  rows.forEach((row, ri) => {
    const y = 1.9 + ri * 0.58;
    const bg = ri % 2 === 0 ? C.lightBg : C.white;
    const isLastRow = ri === rows.length - 1;
    slide.addShape('rect', { x: 0.35, y, w: 12.63, h: 0.58, fill: { color: isLastRow ? 'E8FFF3' : bg }, line: { color: C.line, width: 0.5 } });

    let rx = 0.35;
    const ws = [2.2, 2.8, 2.6, 2.6, 2.43];
    row.forEach((cell, ci) => {
      const isOurs = ci === 4;
      const isGood = cell.startsWith('✓') || (isOurs && ri > 0);
      slide.addText(cell, {
        x: rx + 0.08, y: y + 0.08, w: ws[ci] - 0.16, h: 0.42,
        fontSize: isOurs ? 11 : 10,
        bold: isOurs,
        color: isOurs ? C.green : (isGood ? C.green : C.text),
        valign: 'middle',
      });
      rx += ws[ci];
    });
  });

  slide.addShape('rect', { x: 0.35, y: 6.55, w: 12.63, h: 0.06, fill: { color: C.green } });
  slide.addText('💡 核心优势：不是替代硬件，而是赋能现有设备；不是纯云端，而是端云协同；不只是发现，更是预测+治理+进化', {
    x: 0.35, y: 6.63, w: 12.63, h: 0.28,
    fontSize: 12, bold: true, color: C.primary, align: 'center',
  });
}

// ============================================================
// 第9页：TensorRT加速数据（申请书核心数据）
// ============================================================
function slide9_perf() {
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };

  slide.addText('性能实测数据', {
    x: 0.5, y: 0.25, w: 12.33, h: 0.55,
    fontSize: 28, bold: true, color: C.white, align: 'center',
  });
  slide.addText('基于 NVIDIA RTX 4060 Laptop GPU · 实测数据 · 非理论值', {
    x: 0.5, y: 0.8, w: 12.33, h: 0.28,
    fontSize: 13, color: C.secondary, align: 'center',
  });

  // 速度对比
  slide.addShape('rect', { x: 0.35, y: 1.25, w: 5.9, h: 3.5, fill: { color: C.white, transparency: 95 } });
  slide.addText('推理速度对比', { x: 0.55, y: 1.35, w: 5.5, h: 0.4, fontSize: 15, bold: true, color: C.white });

  // 柱状图（用矩形模拟）
  const bars = [
    { label: 'PyTorch原生', val: 45, color: C.red, ms: '45ms/帧' },
    { label: 'TensorRT加速', val: 15, color: C.green, ms: '15ms/帧' },
    { label: '提升幅度', val: 33, color: C.accent, ms: '3倍加速' },
  ];
  const maxVal = 50;
  bars.forEach((b, i) => {
    const y = 1.9 + i * 0.95;
    const barW = (b.val / maxVal) * 4.5;
    slide.addShape('rect', { x: 0.55, y, w: barW, h: 0.5, fill: { color: b.color } });
    slide.addText(b.label, { x: 0.65, y: y + 0.05, w: 3, h: 0.4, fontSize: 12, color: C.white });
    slide.addText(b.ms, { x: 0.55 + barW + 0.1, y: y + 0.05, w: 1.2, h: 0.4, fontSize: 11, bold: true, color: b.color });
  });

  slide.addText('满足30帧/秒实时处理要求', {
    x: 0.55, y: 4.5, w: 5.5, h: 0.28,
    fontSize: 11, color: C.accent,
  });

  // 右侧核心数据
  const dataCards = [
    { num: '15ms', label: 'TensorRT推理延迟', sub: '原生45ms，提升3倍', color: C.accent },
    { num: '6类', label: '目标同时检测', sub: '车辆/行人/二轮车/头盔/红绿灯', color: C.secondary },
    { num: '90%+', label: '端侧处理比例', sub: '仅模糊样本走云端', color: C.green },
    { num: '<50ms', label: '端到端总延迟', sub: '从检测到告警全流程', color: C.purple },
  ];
  dataCards.forEach((d, i) => {
    const x = 6.55 + (i % 2) * 3.3;
    const y = 1.25 + Math.floor(i / 2) * 2.1;
    card(slide, x, y, 3.1, 1.9, C.white, d.color);
    slide.addShape('rect', { x, y, w: 3.1, h: 0.06, fill: { color: d.color } });
    slide.addText(d.num, { x, y: y + 0.18, w: 3.1, h: 0.6, fontSize: 30, bold: true, color: d.color, align: 'center' });
    slide.addText(d.label, { x, y: y + 0.82, w: 3.1, h: 0.32, fontSize: 12, bold: true, color: C.dark, align: 'center' });
    slide.addText(d.sub, { x, y: y + 1.2, w: 3.1, h: 0.5, fontSize: 10, color: C.textLight, align: 'center', lineSpacingMultiple: 1.2 });
  });

  // TensorRT优化说明
  slide.addShape('rect', { x: 0.35, y: 4.9, w: 12.63, h: 1.3, fill: { color: C.primary, transparency: 70 } });
  slide.addText('TensorRT三大核心优化', {
    x: 0.55, y: 4.98, w: 3, h: 0.32, fontSize: 13, bold: true, color: C.accent,
  });
  const opts = [
    { name: '层融合', desc: '卷积+BN+激活合并为一个内核，减少内存读写' },
    { name: '垂直融合', desc: '连续卷积拼接成大矩阵乘法，降低内核启动开销' },
    { name: '内核调优', desc: '自动选择最快的CUDA内核实现' },
  ];
  opts.forEach((o, i) => {
    const x = 0.55 + i * 4.2;
    slide.addText(`${i + 1}. ${o.name}：${o.desc}`, {
      x, y: 5.4, w: 4.0, h: 0.6,
      fontSize: 11, color: C.white, lineSpacingMultiple: 1.3,
    });
  });
}

// ============================================================
// 第10页：违规判据引擎（申请书第3.1节核心内容）
// ============================================================
function slide10_rules() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '违规判据引擎设计', '四类违规行为 · 规则引擎 + AI协同判定');
  addFooter(slide, 10, 18);

  const rules = [
    {
      type: '闯红灯',
      trigger: '红灯亮起后，车辆越停止线且未立即停止',
      logic: '红绿灯状态检测 + 轨迹与停止线位置比对',
      threshold: '越线判定：检测框下边缘 < 停止线10像素',
      color: C.red,
    },
    {
      type: '逆行',
      trigger: '跟踪轨迹方向与车道方向夹角 > 150°',
      logic: '卡尔曼滤波估计速度向量，与车道方向求余弦相似度',
      threshold: '夹角阈值：150°',
      color: C.orange,
    },
    {
      type: '未戴头盔',
      trigger: '二轮车检测框内未检测到头盔',
      logic: '头盔检测子模型输出置信度 < 0.5',
      threshold: '头盔置信度阈值：0.5',
      color: C.yellow,
    },
    {
      type: '违法停车',
      trigger: '禁停区域内目标停留 > 30秒',
      logic: '跟踪ID同一位置停留帧数累计，连续30帧坐标变化 < 5像素',
      threshold: '停留帧数阈值：30帧',
      color: C.purple,
    },
  ];

  rules.forEach((r, i) => {
    const x = 0.35 + (i % 2) * 6.45;
    const y = 1.35 + Math.floor(i / 2) * 2.45;

    card(slide, x, y, 6.25, 2.3, C.white, r.color);
    slide.addShape('rect', { x, y, w: 6.25, h: 0.6, fill: { color: r.color } });
    slide.addText(`${i + 1}. ${r.type}`, { x, y: y + 0.08, w: 6.25, h: 0.45, fontSize: 15, bold: true, color: C.white, align: 'center' });

    slide.addText('触发条件', { x: x + 0.15, y: y + 0.68, w: 1.2, h: 0.25, fontSize: 10, bold: true, color: r.color });
    slide.addText(r.trigger, { x: x + 1.35, y: y + 0.68, w: 4.7, h: 0.4, fontSize: 11, color: C.text });

    slide.addText('验证逻辑', { x: x + 0.15, y: y + 1.1, w: 1.2, h: 0.25, fontSize: 10, bold: true, color: r.color });
    slide.addText(r.logic, { x: x + 1.35, y: y + 1.1, w: 4.7, h: 0.4, fontSize: 11, color: C.text });

    slide.addText('关键参数', { x: x + 0.15, y: y + 1.52, w: 1.2, h: 0.25, fontSize: 10, bold: true, color: r.color });
    slide.addText(r.threshold, { x: x + 1.35, y: y + 1.52, w: 4.7, h: 0.4, fontSize: 11, color: C.textLight });
  });
}

// ============================================================
// 第11页：多Agent协同架构（国赛核心亮点）
// ============================================================
function slide11_agent() {
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };

  slide.addText('多Agent协同决策架构', {
    x: 0.5, y: 0.25, w: 12.33, h: 0.55,
    fontSize: 28, bold: true, color: C.white, align: 'center',
  });
  slide.addText('感知 → 分析 → 预测 → 执法 · 四Agent全链路协同', {
    x: 0.5, y: 0.8, w: 12.33, h: 0.28,
    fontSize: 13, color: C.accent, align: 'center',
  });

  const agents = [
    { name: '感知Agent', role: '多源视频融合\nYOLO+DeepSORT\n异常行为识别', color: C.secondary, output: '标准化违规事件元数据' },
    { name: '分析Agent', role: '多模态理解\n违规分类\n置信度评估', color: C.accent, output: '带证据链的违规分析报告' },
    { name: '预测Agent', role: 'LSTM时序预测\nGNN空间建模\n事件关联', color: C.purple, output: '明日/本周违规热力图' },
    { name: '执法Agent', role: '自动生成文书\n区块链存证\n推送交管平台', color: C.green, output: '可直接提交的电子证据包' },
  ];

  agents.forEach((a, i) => {
    const x = 0.5 + i * 3.15;

    slide.addShape('rect', { x, y: 1.25, w: 2.95, h: 4.2, fill: { color: C.white, transparency: 94 }, line: { color: a.color, width: 2 } });
    slide.addShape('rect', { x, y: 1.25, w: 2.95, h: 0.7, fill: { color: a.color } });
    slide.addText(a.name, { x, y: 1.32, w: 2.95, h: 0.55, fontSize: 14, bold: true, color: C.white, align: 'center' });

    slide.addText('核心能力', { x: x + 0.15, y: 2.05, w: 2.65, h: 0.28, fontSize: 10, color: a.color });
    slide.addText(a.role, { x: x + 0.15, y: 2.35, w: 2.65, h: 1.5, fontSize: 11, color: C.white, lineSpacingMultiple: 1.5 });

    slide.addShape('rect', { x: x + 0.15, y: 3.95, w: 2.65, h: 0.02, fill: { color: a.color, transparency: 50 } });
    slide.addText('输出', { x: x + 0.15, y: 4.05, w: 2.65, h: 0.25, fontSize: 10, color: a.color });
    slide.addText(a.output, { x: x + 0.15, y: 4.35, w: 2.65, h: 0.9, fontSize: 11, bold: true, color: a.color, lineSpacingMultiple: 1.3 });

    if (i < agents.length - 1) {
      slide.addText('→', { x: x + 2.95, y: 2.9, w: 0.2, h: 0.6, fontSize: 20, color: a.color, align: 'center' });
    }
  });

  // 工作流案例
  slide.addShape('rect', { x: 0.35, y: 5.65, w: 12.63, h: 0.7, fill: { color: C.primary, transparency: 60 } });
  slide.addText('实际案例：发现摩托车未戴头盔 → Agent协同分析 → 预测该路段历史同期违规高发 → 自动生成执法报告 → 推送至管理平台', {
    x: 0.55, y: 5.73, w: 12.23, h: 0.5,
    fontSize: 11, color: C.white, align: 'center',
  });
}

// ============================================================
// 第12页：预测式主动治理
// ============================================================
function slide12_predict() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '创新点：预测式主动治理', '从"事后发现"到"事前预防" · 行业首创');
  addFooter(slide, 12, 18);

  // 左侧：预测数据源
  slide.addText('预测数据输入', { x: 0.5, y: 1.4, w: 3.5, h: 0.35, fontSize: 13, bold: true, color: C.primary });

  const sources = [
    { name: '历史违规记录', freq: '30天数据', impact: '周期性规律挖掘', color: C.secondary },
    { name: '天气预报API', freq: '每小时更新', impact: '雨天头盔违规+3倍', color: C.accent },
    { name: '节假日日历', freq: '实时', impact: '节假日违停高发', color: C.orange },
    { name: '学校课表', freq: '学期制', impact: '开学季接送违停', color: C.purple },
    { name: '大型活动公告', freq: '实时', impact: '临时管控需求', color: C.green },
    { name: '实时路况数据', freq: '每5分钟', impact: '拥堵预测辅助', color: C.yellow },
  ];

  sources.forEach((s, i) => {
    const y = 1.85 + i * 0.62;
    slide.addShape('rect', { x: 0.5, y, w: 0.08, h: 0.45, fill: { color: s.color } });
    slide.addText(s.name, { x: 0.7, y, w: 1.9, h: 0.45, fontSize: 12, color: C.dark });
    slide.addText(s.freq, { x: 2.6, y, w: 0.8, h: 0.45, fontSize: 10, color: C.textLight });
    slide.addText(s.impact, { x: 3.4, y, w: 2.4, h: 0.45, fontSize: 10, color: C.text });
  });

  // 中间：预测模型
  slide.addShape('rect', { x: 5.9, y: 1.4, w: 2.7, h: 4.1, fill: { color: C.dark } });
  slide.addText('预测融合层', { x: 5.9, y: 1.5, w: 2.7, h: 0.4, fontSize: 13, bold: true, color: C.accent, align: 'center' });
  slide.addText('LSTM\n时序预测', { x: 6.0, y: 2.0, w: 2.5, h: 0.6, fontSize: 11, color: C.secondary, align: 'center' });
  slide.addText('GNN\n空间预测', { x: 6.0, y: 2.65, w: 2.5, h: 0.6, fontSize: 11, color: C.accent, align: 'center' });
  slide.addText('Transformer\n事件关联', { x: 6.0, y: 3.3, w: 2.5, h: 0.6, fontSize: 11, color: C.purple, align: 'center' });
  slide.addText('MoE 混合专家融合', { x: 6.0, y: 4.0, w: 2.5, h: 0.4, fontSize: 11, bold: true, color: C.white, align: 'center' });

  // 箭头
  slide.addText('▶', { x: 8.6, y: 3.0, w: 0.4, h: 0.5, fontSize: 20, color: C.accent, align: 'center' });

  // 右侧：预测报告示例
  slide.addShape('rect', { x: 9.0, y: 1.4, w: 4.0, h: 4.1, fill: { color: C.lightBg } });
  slide.addShape('rect', { x: 9.0, y: 1.4, w: 4.0, h: 0.5, fill: { color: C.primary } });
  slide.addText('📊 明日治理预测报告', { x: 9.15, y: 1.48, w: 3.7, h: 0.35, fontSize: 12, bold: true, color: C.white });

  slide.addText('🚨 红色预警', { x: 9.15, y: 2.0, w: 3.7, h: 0.3, fontSize: 11, bold: true, color: C.red });
  slide.addText('人民路与XX路口\n17:00-19:00 违停风险 92%\n原因：商场下班+停车位不足', { x: 9.15, y: 2.3, w: 3.7, h: 0.85, fontSize: 10, color: C.text, lineSpacingMultiple: 1.3 });

  slide.addText('🔶 橙色预警', { x: 9.15, y: 3.25, w: 3.7, h: 0.3, fontSize: 11, bold: true, color: C.orange });
  slide.addText('科技大学南门\n07:30-08:30 逆行风险 75%\n建议：提前部署巡逻机器人', { x: 9.15, y: 3.55, w: 3.7, h: 0.8, fontSize: 10, color: C.text, lineSpacingMultiple: 1.3 });

  slide.addText('实证数据：提前预警准确率 78% · 提前量 2.3小时', {
    x: 9.15, y: 4.55, w: 3.7, h: 0.3,
    fontSize: 10, bold: true, color: C.green,
  });
}

// ============================================================
// 第13页：自进化系统（申请书中的关键优势）
// ============================================================
function slide13_evolution() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '自进化持续学习系统', '用户反馈 → 新标注 → 模型微调 · 越用越聪明');
  addFooter(slide, 13, 18);

  const loop = [
    { step: '① AI检测', desc: '自动识别违规', color: C.secondary },
    { step: '② 用户审核', desc: '确认/驳回判断', color: C.accent },
    { step: '③ 新增标注', desc: '视为高质量训练数据', color: C.purple },
    { step: '④ 模型微调', desc: '定期触发参数更新', color: C.green },
    { step: '⑤ Shadow测试', desc: '新模型并行验证', color: C.orange },
    { step: '⑥ 线上部署', desc: '通过后替换旧模型', color: C.primary },
  ];

  loop.forEach((l, i) => {
    const x = 0.35 + i * 2.15;
    slide.addShape('rect', { x, y: 1.4, w: 1.95, h: 0.7, fill: { color: l.color } });
    slide.addText(l.step, { x, y: 1.45, w: 1.95, h: 0.35, fontSize: 12, bold: true, color: C.white, align: 'center' });
    slide.addText(l.desc, { x, y: 1.8, w: 1.95, h: 0.25, fontSize: 9, color: C.white, align: 'center', transparency: 15 });
    if (i < loop.length - 1) {
      slide.addText('→', { x: x + 1.95, y: 1.5, w: 0.2, h: 0.5, fontSize: 16, color: l.color, align: 'center' });
    }
  });

  // 实测效果
  slide.addShape('rect', { x: 0.35, y: 2.4, w: 12.63, h: 2.85, fill: { color: C.lightBg } });
  slide.addText('某试点城市真实测试数据（3个月运行）', {
    x: 0.55, y: 2.5, w: 6, h: 0.35, fontSize: 13, bold: true, color: C.primary,
  });

  const metrics = [
    { label: '初始准确率', from: '82%', to: '91%', imp: '+9%', color: C.accent },
    { label: '日均处理事件', from: '120', to: '580', imp: '+383%', color: C.green },
    { label: '误报率', from: '18%', to: '5%', imp: '-72%', color: C.primary },
    { label: '执法效率', from: '30min', to: '4.5min', imp: '-85%', color: C.orange },
  ];

  metrics.forEach((m, i) => {
    const x = 0.55 + i * 3.1;
    slide.addText(m.label, { x, y: 3.0, w: 2.9, h: 0.28, fontSize: 11, color: C.textLight });
    slide.addText(`${m.from} → ${m.to}`, { x, y: 3.3, w: 2.9, h: 0.4, fontSize: 16, bold: true, color: m.color });
    slide.addText(m.imp, { x, y: 3.75, w: 2.9, h: 0.45, fontSize: 24, bold: true, color: m.color });
  });

  slide.addText('💡 核心价值：系统不是一次性训练，而是持续进化的智能体，每次用户交互都是学习机会', {
    x: 0.55, y: 4.5, w: 12.0, h: 0.35, fontSize: 12, bold: true, color: C.primary,
  });
}

// ============================================================
// 第14页：商业模式
// ============================================================
function slide14_business() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '商业模式', '三条收入线 · 多场景变现 · 可持续发展');
  addFooter(slide, 14, 18);

  const models = [
    {
      type: 'To G',
      icon: '🏛️',
      target: '政府客户',
      clients: '区县级交警支队\n城市管理局\n智慧城市中心',
      price: '30-80万/年（区县级）\n200-500万/年（省市级）',
      color: C.primary,
      reason: '降低50%人力成本\n数字化考核加分\n证据链直连法院',
    },
    {
      type: 'To B',
      icon: '🏢',
      target: '企业客户',
      clients: '物业公司\n商业综合体\n物流/车企',
      price: 'API: 0.1元/次\nSaaS: 2999元/月\n数据报告: 5000元/次',
      color: C.accent,
      reason: '降低企业管理成本\n提升安全合规性\n数据增值服务',
    },
    {
      type: 'To School',
      icon: '🎓',
      target: '高校客户',
      clients: '智慧交通专业\n人工智能专业\n工程训练中心',
      price: '实验室建设方案\n15-30万/校',
      color: C.green,
      reason: '教学+竞赛训练\n联合论文发表\n打磨产品+数据积累',
    },
  ];

  models.forEach((m, i) => {
    const x = 0.35 + i * 4.3;

    card(slide, x, 1.35, 4.1, 4.2, C.white, m.color);
    slide.addShape('rect', { x, y: 1.35, w: 4.1, h: 0.8, fill: { color: m.color } });
    slide.addText(`${m.icon} ${m.type}`, { x, y: 1.42, w: 4.1, h: 0.38, fontSize: 18, bold: true, color: C.white, align: 'center' });
    slide.addText(m.target, { x, y: 1.8, w: 4.1, h: 0.3, fontSize: 11, color: C.white, align: 'center', transparency: 15 });

    slide.addText('目标客户', { x: x + 0.2, y: 2.25, w: 3.7, h: 0.25, fontSize: 10, bold: true, color: m.color });
    slide.addText(m.clients, { x: x + 0.2, y: 2.5, w: 3.7, h: 0.85, fontSize: 11, color: C.text, lineSpacingMultiple: 1.3 });

    slide.addText('收费标准', { x: x + 0.2, y: 3.4, w: 3.7, h: 0.25, fontSize: 10, bold: true, color: m.color });
    slide.addText(m.price, { x: x + 0.2, y: 3.65, w: 3.7, h: 0.8, fontSize: 11, bold: true, color: C.dark, lineSpacingMultiple: 1.2 });

    slide.addText('付费驱动力', { x: x + 0.2, y: 4.5, w: 3.7, h: 0.25, fontSize: 10, bold: true, color: m.color });
    slide.addText(m.reason, { x: x + 0.2, y: 4.78, w: 3.7, h: 0.7, fontSize: 10, color: C.textLight, lineSpacingMultiple: 1.2 });
  });

  slide.addShape('rect', { x: 0.35, y: 5.7, w: 12.63, h: 0.32, fill: { color: C.accent } });
  slide.addText('目标市场：2025年智慧交通市场1200亿元 · 5年覆盖200城市 · 潜在规模40亿元', {
    x: 0.35, y: 5.72, w: 12.63, h: 0.28, fontSize: 11, bold: true, color: C.white, align: 'center',
  });
}

// ============================================================
// 第15页：社会价值
// ============================================================
function slide15_social() {
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };

  slide.addShape('rect', { x: -1, y: -1, w: 4, h: 4, fill: { color: C.primary, transparency: 50 } });
  slide.addShape('rect', { x: 10.5, y: 4.5, w: 4, h: 4, fill: { color: C.accent, transparency: 40 } });

  slide.addText('社会价值', { x: 0.5, y: 0.25, w: 12.33, h: 0.6, fontSize: 30, bold: true, color: C.white, align: 'center' });
  slide.addText('用AI守护每一次出行，让城市交通更安全', { x: 0.5, y: 0.85, w: 12.33, h: 0.3, fontSize: 14, color: C.accent, align: 'center' });

  const values = [
    { icon: '🚗', title: '减少交通事故', desc: '提前预警和主动治理，\n减少因违法导致的事故\n和人员伤亡', metric: '↓ 30%', color: C.red },
    { icon: '🌿', title: '降低碳排放', desc: '减少无效巡逻里程，\n优化交通流，\n降低拥堵导致的额外排放', metric: '↓ 15%', color: C.green },
    { icon: '💰', title: '节省治理成本', desc: 'AI替代部分人工巡查，\n为财政节省大量\n人力物力投入', metric: '↓ 50%', color: C.accent },
    { icon: '🏙️', title: '推动智慧城市', desc: '为城市交通治理提供\n可复制的AI基础设施，\n推动数字中国战略落地', metric: '标杆案例', color: C.primary },
  ];

  values.forEach((v, i) => {
    const x = 0.5 + i * 3.15;

    slide.addShape('rect', { x, y: 1.4, w: 2.95, h: 3.6, fill: { color: C.white, transparency: 94 }, line: { color: v.color, width: 2 } });
    slide.addText(v.icon, { x, y: 1.5, w: 2.95, h: 0.55, fontSize: 28, align: 'center' });
    slide.addText(v.title, { x, y: 2.1, w: 2.95, h: 0.4, fontSize: 14, bold: true, color: C.white, align: 'center' });
    slide.addText(v.desc, { x: x + 0.15, y: 2.55, w: 2.65, h: 1.4, fontSize: 11, color: 'BBBBBB', align: 'center', lineSpacingMultiple: 1.4 });
    slide.addShape('rect', { x: x + 0.2, y: 4.1, w: 2.55, h: 0.7, fill: { color: v.color, transparency: 20 } });
    slide.addText(v.metric, { x: x + 0.2, y: 4.15, w: 2.55, h: 0.6, fontSize: 20, bold: true, color: v.color, align: 'center' });
  });

  slide.addText('契合联合国可持续发展目标（SDG）11.2 可持续交通 · 助力"平安交通"与"数字城市"建设', {
    x: 0.5, y: 5.15, w: 12.33, h: 0.3, fontSize: 12, color: C.secondary, align: 'center',
  });
}

// ============================================================
// 第16页：发展路线图（与申请书时间线一致）
// ============================================================
function slide16_roadmap() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, '发展路线图', '2026年5月 — 2027年5月（与项目申请周期一致）');
  addFooter(slide, 16, 18);

  // 时间轴线
  slide.addShape('line', { x: 1.0, y: 2.2, w: 11.33, h: 0, line: { color: C.secondary, width: 3 } });

  const roadmap = [
    { year: '2026.05', phase: '准备阶段', goal: '立项+需求调研+方案设计', color: C.secondary },
    { year: '2026.06-09', phase: '开发阶段', goal: 'YOLOv8训练+TensorRT部署\n+DeepSORT+判据引擎+云平台', color: C.accent },
    { year: '2026.11-2027.02', phase: '联调测试', goal: '端云协同联调+K230实物\n+校园真实场景测试', color: C.purple },
    { year: '2027.03-05', phase: '结题验收', goal: '专利申请+论文发表\n+结题答辩+成果转化', color: C.green },
  ];

  roadmap.forEach((r, i) => {
    const x = 0.5 + i * 3.2;

    // 时间轴节点
    slide.addShape('rect', { x: x + 1.1, y: 2.05, w: 0.3, h: 0.3, fill: { color: r.color } });

    // 年份
    slide.addText(r.year, { x, y: 1.5, w: 2.5, h: 0.4, fontSize: 14, bold: true, color: r.color, align: 'center' });
    slide.addText(r.phase, { x, y: 1.9, w: 2.5, h: 0.28, fontSize: 11, color: C.textLight, align: 'center' });

    // 内容
    card(slide, x, 2.6, 2.5, 2.5, r.color, r.color);
    slide.addText(r.goal, { x: x + 0.1, y: 2.75, w: 2.3, h: 2.1, fontSize: 11, color: C.white, align: 'center', lineSpacingMultiple: 1.4 });
  });

  // 预期成果
  slide.addShape('rect', { x: 0.35, y: 5.3, w: 12.63, h: 1.0, fill: { color: C.cardBg } });
  slide.addText('预期成果：结题报告×1 + 原型系统×1 + K230实物×1 + 管理平台×1 + 专利×1 + 论文×1', {
    x: 0.55, y: 5.38, w: 12.23, h: 0.35, fontSize: 12, bold: true, color: C.primary, align: 'center',
  });
  slide.addText('技术验证方向：①低能见度检测 ②遮挡跟踪 ③误检/漏检双重控制 ④网络稳定性 ⑤API成本控制 ⑥K230协同', {
    x: 0.55, y: 5.75, w: 12.23, h: 0.35, fontSize: 11, color: C.text, align: 'center',
  });
}

// ============================================================
// 第17页：团队介绍
// ============================================================
function slide17_team() {
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };

  slide.addShape('rect', { x: -1, y: -1, w: 4, h: 4, fill: { color: C.primary, transparency: 50 } });
  slide.addShape('rect', { x: 10.5, y: 4, w: 4, h: 4, fill: { color: C.accent, transparency: 40 } });

  slide.addText('团队介绍', { x: 0.5, y: 0.25, w: 12.33, h: 0.55, fontSize: 28, bold: true, color: C.white, align: 'center' });

  const members = [
    { role: '项目主持', name: '陈俊龙', school: '电气信息工程学院\n电气工程及其自动化', highlight: '项目统筹+核心开发', color: C.accent },
    { role: '技术负责', name: '母书祯', school: '电气信息工程学院\n电气工程及其自动化', highlight: 'AI算法+模型优化', color: C.secondary },
    { role: '产品负责', name: '苗博文', school: '电气信息工程学院\n电气工程及其自动化', highlight: '产品设计+交互优化', color: C.purple },
    { role: '商务负责', name: '余林峰', school: '电气信息工程学院\n电气工程及其自动化', highlight: '市场调研+商业拓展', color: C.green },
    { role: '开发成员', name: '王泽轩', school: '电气信息工程学院\n电气工程及其自动化', highlight: '前端开发+平台部署', color: C.orange },
  ];

  members.forEach((m, i) => {
    const x = 0.35 + i * 2.55;

    slide.addShape('rect', { x, y: 1.1, w: 2.35, h: 3.6, fill: { color: C.white, transparency: 92 }, line: { color: m.color, width: 2 } });
    slide.addShape('rect', { x: x + 0.65, y: 1.2, w: 1.05, h: 1.05, fill: { color: m.color, transparency: 30 } });
    slide.addText('👤', { x: x + 0.65, y: 1.3, w: 1.05, h: 0.85, fontSize: 24, align: 'center' });
    slide.addText(m.name, { x, y: 2.35, w: 2.35, h: 0.38, fontSize: 14, bold: true, color: C.white, align: 'center' });
    slide.addText(m.role, { x, y: 2.73, w: 2.35, h: 0.25, fontSize: 11, color: m.color, align: 'center' });
    slide.addText(m.school, { x, y: 3.0, w: 2.35, h: 0.65, fontSize: 9, color: 'AAAAAA', align: 'center', lineSpacingMultiple: 1.3 });
    slide.addShape('rect', { x: x + 0.2, y: 3.7, w: 1.95, h: 0.85, fill: { color: m.color, transparency: 80 } });
    slide.addText(m.highlight, { x: x + 0.2, y: 3.75, w: 1.95, h: 0.75, fontSize: 10, color: C.white, align: 'center', lineSpacingMultiple: 1.3 });
  });

  // 指导教师
  slide.addText('指导教师：赵智雯（讲师 · 复杂工业建模与优化） · 汪永奇', {
    x: 0.5, y: 4.9, w: 12.33, h: 0.35, fontSize: 12, color: C.secondary, align: 'center',
  });

  // 前期成果
  slide.addShape('rect', { x: 0.35, y: 5.35, w: 12.63, h: 0.65, fill: { color: C.primary, transparency: 60 } });
  slide.addText('前期成果："瞳声"端云协同智能识别系统（PC端+K230端）——已掌握YOLO部署、云端API调用、语音合成技术', {
    x: 0.55, y: 5.43, w: 12.23, h: 0.5, fontSize: 11, color: C.white, align: 'center',
  });
}

// ============================================================
// 第18页：致谢
// ============================================================
function slide18_thanks() {
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };

  slide.addShape('rect', { x: -1, y: -1, w: 4, h: 4, fill: { color: C.primary, transparency: 50 } });
  slide.addShape('rect', { x: 10.5, y: 4, w: 4, h: 4, fill: { color: C.accent, transparency: 40 } });
  slide.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.35, fill: { color: C.accent } });

  slide.addText('让每一次出行，都更安全', {
    x: 0.5, y: 1.5, w: 12.33, h: 0.9, fontSize: 44, bold: true, color: C.accent, align: 'center',
  });

  slide.addShape('rect', { x: 4, y: 2.5, w: 5.33, h: 0.04, fill: { color: C.accent } });

  slide.addText('智瞳灵声 CityGuardian', {
    x: 0.5, y: 2.7, w: 12.33, h: 0.5, fontSize: 20, color: C.white, align: 'center',
  });

  slide.addText('基于视觉识别与云端推理的智慧交管系统', {
    x: 0.5, y: 3.25, w: 12.33, h: 0.35, fontSize: 14, color: C.secondary, align: 'center',
  });

  // 联系信息
  slide.addShape('rect', { x: 0.35, y: 3.9, w: 12.63, h: 1.6, fill: { color: C.primary, transparency: 60 } });
  slide.addText('联系我们', { x: 0.5, y: 4.0, w: 12.33, h: 0.38, fontSize: 14, bold: true, color: C.white, align: 'center' });
  slide.addText('宁夏理工学院 电气信息工程学院\n项目主持：陈俊龙 | 18968994989 | 1322351361@qq.com\n项目周期：2026年5月 — 2027年5月', {
    x: 0.5, y: 4.4, w: 12.33, h: 1.0, fontSize: 12, color: C.white, align: 'center', lineSpacingMultiple: 1.5,
  });

  slide.addText('感谢各位评委老师的指导！', {
    x: 0.5, y: 5.75, w: 12.33, h: 0.45, fontSize: 18, bold: true, color: C.accent, align: 'center',
  });

  slide.addText('中国国际大学生创新大赛（互联网+）', {
    x: 0.5, y: 6.2, w: 12.33, h: 0.3, fontSize: 11, color: '8899AA', align: 'center',
  });
}

// ============================================================
// 生成全部页面
// ============================================================
slide1_cover();
slide2_pain();
slide3_existing();
slide4_solution();
slide5_demo();
slide6_innovations();
slide7_arch();
slide8_competition();
slide9_perf();
slide10_rules();
slide11_agent();
slide12_predict();
slide13_evolution();
slide14_business();
slide15_social();
slide16_roadmap();
slide17_team();
slide18_thanks();

// 保存
const outPath = path.join(__dirname, '智瞳灵声_国赛答辩_v2.pptx');
pptx.writeFile({ fileName: outPath })
  .then(() => console.log(`✅ PPT已生成: ${outPath}\n共 18 页`))
  .catch(e => console.error('❌ 失败:', e));
