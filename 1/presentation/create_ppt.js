// 城市智眼 CityVision - 国赛答辩PPT生成脚本
// 使用 PptxGenJS + 主题配置

const pptxgen = require('pptxgenjs');
const path = require('path');

// 导入 helpers（本地路径）
// 注意：helpers 不使用（避免原生依赖问题）

// ============================================================
// 主题配置
// ============================================================
const THEME = {
  primary: '1B3A6B',      // 深蓝
  secondary: '4A90D9',    // 中蓝
  accent: '00C9A7',      // 青色（科技感）
  accent2: 'FF6B35',     // 橙色（警示/强调）
  dark: '1A1A2E',        // 深色背景
  text: '2D3748',        // 正文
  textLight: '718096',   // 次要文字
  white: 'FFFFFF',
  lightBg: 'F7FAFC',
  cardBg: 'EDF2F7',
  gradient1: '1B3A6B',  // 渐变1
  gradient2: '2E86AB',  // 渐变2
  green: '38A169',
  red: 'E53E3E',
  yellow: 'D69E2E',
};

// 字体配置
const FONTS = {
  title: 'Microsoft YaHei',
  body: 'Microsoft YaHei',
  code: 'Consolas',
};

// 创建 pptx 实例
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE'; // 16:9
pptx.title = '城市智眼 CityVision - 自主巡航AI交通治理智能体';
pptx.author = '城市智眼团队';
pptx.subject = '中国国际大学生创新大赛';

// ============================================================
// 辅助函数
// ============================================================

// 添加带装饰条的标题
function addTitleBar(slide, title, subtitle = '') {
  // 左侧装饰条
  slide.addShape('rect', {
    x: 0, y: 0, w: 0.15, h: 5.625,
    fill: { color: THEME.accent },
  });
  // 顶部细线
  slide.addShape('rect', {
    x: 0, y: 0, w: 13.33, h: 0.03,
    fill: { color: THEME.secondary },
  });

  // 标题
  slide.addText(title, {
    x: 0.4, y: 0.3, w: 12, h: 0.8,
    fontSize: 36, bold: true, color: THEME.primary,
    fontFace: FONTS.title, margin: 0,
  });

  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.4, y: 1.0, w: 12, h: 0.4,
      fontSize: 16, color: THEME.textLight, fontFace: FONTS.body,
    });
  }
}

// 添加页码
function addPageNumber(slide, num, total) {
  slide.addText(`${num} / ${total}`, {
    x: 12.5, y: 5.3, w: 0.8, h: 0.25,
    fontSize: 10, color: THEME.textLight, align: 'right',
  });
}

// 添加底部装饰
function addFooter(slide) {
  slide.addShape('rect', {
    x: 0, y: 5.55, w: 13.33, h: 0.075,
    fill: { color: THEME.accent },
  });
}

// 创建信息卡片
function addInfoCard(slide, x, y, w, h, title, value, unit, color) {
  slide.addShape('rect', {
    x, y, w, h,
    fill: { color: THEME.white },
    line: { color: 'E2E8F0', width: 1 },
    shadow: { type: 'outer', blur: 4, offset: 2, angle: 45, color: '000000', opacity: 0.08 },
  });
  // 顶部色条
  slide.addShape('rect', {
    x, y, w, h: 0.06,
    fill: { color: color || THEME.accent },
  });
  slide.addText(value, {
    x, y: y + 0.15, w, h: 0.55,
    fontSize: 32, bold: true, color: color || THEME.accent,
    align: 'center', margin: 0,
  });
  if (unit) {
    slide.addText(unit, {
      x, y: y + 0.65, w, h: 0.25,
      fontSize: 11, color: THEME.textLight, align: 'center',
    });
  }
  slide.addText(title, {
    x, y: y + 0.95, w, h: 0.3,
    fontSize: 12, color: THEME.text, align: 'center',
    fontFace: FONTS.body,
  });
}

// 创建标签
function addTag(slide, x, y, text, color) {
  const w = text.length * 0.28 + 0.3;
  slide.addShape('rect', {
    x, y, w, h: 0.32,
    fill: { color: color || THEME.accent },
    rectRadius: 0.05,
  });
  slide.addText(text, {
    x, y, w, h: 0.32,
    fontSize: 11, color: THEME.white, align: 'center', valign: 'middle',
    margin: 0,
  });
}

// ============================================================
// 第1页：封面
// ============================================================
function slide1_cover() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.dark };

  // 顶部渐变色块
  slide.addShape('rect', {
    x: 0, y: 0, w: 13.33, h: 0.4,
    fill: { color: THEME.accent },
  });

  // 左侧大圆形装饰
  slide.addShape('ellipse', {
    x: -1.5, y: -1, w: 5, h: 5,
    fill: { color: THEME.primary, transparency: 40 },
  });
  slide.addShape('ellipse', {
    x: -0.5, y: 3.5, w: 3, h: 3,
    fill: { color: THEME.accent, transparency: 30 },
  });

  // 右下装饰
  slide.addShape('ellipse', {
    x: 10, y: 3, w: 5, h: 5,
    fill: { color: THEME.primary, transparency: 20 },
  });

  // 顶部标语
  slide.addText('中国国际大学生创新大赛 · 互联网+', {
    x: 0.5, y: 0.6, w: 12, h: 0.4,
    fontSize: 14, color: THEME.accent, align: 'center',
    fontFace: FONTS.body,
  });

  // 主标题
  slide.addText('城市智眼', {
    x: 0.5, y: 1.4, w: 12, h: 1.2,
    fontSize: 72, bold: true, color: THEME.white, align: 'center',
    fontFace: FONTS.title,
  });

  slide.addText('CityVision', {
    x: 0.5, y: 2.45, w: 12, h: 0.5,
    fontSize: 24, color: THEME.accent, align: 'center',
    fontFace: FONTS.body,
  });

  // 分隔线
  slide.addShape('rect', {
    x: 4.5, y: 3.0, w: 4.33, h: 0.04,
    fill: { color: THEME.accent },
  });

  // 副标题
  slide.addText('面向智慧城市的自主巡航AI交通治理智能体', {
    x: 0.5, y: 3.2, w: 12, h: 0.6,
    fontSize: 22, color: THEME.white, align: 'center',
    fontFace: FONTS.body,
  });

  // 底部信息
  slide.addText('自主巡航 · 预测治理 · 智能决策', {
    x: 0.5, y: 4.2, w: 12, h: 0.4,
    fontSize: 16, color: THEME.secondary, align: 'center',
    fontFace: FONTS.body,
  });

  slide.addText('团队名称：城市智眼  |  指导老师：待填写  |  所属院校：待填写', {
    x: 0.5, y: 5.1, w: 12, h: 0.35,
    fontSize: 12, color: '8899AA', align: 'center',
    fontFace: FONTS.body,
  });
}

// ============================================================
// 第2页：痛点分析
// ============================================================
function slide2_pain_points() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '痛点分析', '交通治理面临的严峻挑战');
  addFooter(slide);
  addPageNumber(slide, 2, 18);

  // 四个痛点卡片
  const painPoints = [
    { icon: '😫', title: '人力严重不足', desc: '平均1名交警需管理\n2.3公里道路，\n人工巡查效率低下', color: THEME.red, stat: '1:2.3', unit: 'km/人' },
    { icon: '⏰', title: '被动响应滞后', desc: '只能事后追责，\n无法预防违规发生，\n事故率居高不下', color: THEME.accent2, stat: '>70%', unit: '事后响应' },
    { icon: '📹', title: '数据孤岛严重', desc: '摄像头只录像，\n各系统数据不互通，\n无法形成治理合力', color: THEME.yellow, stat: '90%', unit: '数据孤岛' },
    { icon: '💸', title: '治理成本高昂', desc: '人工执法成本高，\n取证效率低，\n群众满意度持续走低', color: THEME.primary, stat: '3倍', unit: '成本差距' },
  ];

  painPoints.forEach((p, i) => {
    const x = 0.4 + i * 3.2;
    const y = 1.6;
    // 卡片背景
    slide.addShape('rect', {
      x, y, w: 3.0, h: 3.6,
      fill: { color: THEME.white },
      line: { color: 'E2E8F0', width: 1 },
      shadow: { type: 'outer', blur: 6, offset: 3, angle: 45, color: '000000', opacity: 0.1 },
    });
    // 顶部色条
    slide.addShape('rect', {
      x, y, w: 3.0, h: 0.08,
      fill: { color: p.color },
    });
    // 数字
    slide.addText(p.stat, {
      x, y: y + 0.2, w: 3.0, h: 0.7,
      fontSize: 40, bold: true, color: p.color, align: 'center',
    });
    slide.addText(p.unit, {
      x, y: y + 0.85, w: 3.0, h: 0.25,
      fontSize: 11, color: THEME.textLight, align: 'center',
    });
    // 标题
    slide.addText(p.title, {
      x, y: y + 1.2, w: 3.0, h: 0.4,
      fontSize: 16, bold: true, color: THEME.dark, align: 'center',
    });
    // 描述
    slide.addText(p.desc, {
      x: x + 0.15, y: y + 1.65, w: 2.7, h: 1.8,
      fontSize: 12, color: THEME.textLight, align: 'center',
      lineSpacingMultiple: 1.3,
    });
  });

  // 底部总结
  slide.addShape('rect', {
    x: 0.4, y: 5.2, w: 12.53, h: 0.05,
    fill: { color: THEME.accent },
  });
  slide.addText('结论：传统"人海战术"已无法应对现代城市交通治理需求，亟需AI驱动的智能化变革', {
    x: 0.4, y: 5.28, w: 12.53, h: 0.25,
    fontSize: 12, bold: true, color: THEME.primary, align: 'center',
  });
}

// ============================================================
// 第3页：现有方案不足
// ============================================================
function slide3_existing() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.lightBg };

  addTitleBar(slide, '现有方案不足', '为什么传统方案无法解决核心问题');
  addFooter(slide);
  addPageNumber(slide, 3, 18);

  const solutions = [
    {
      name: '人工巡查',
      problems: ['效率低下，无法24小时覆盖', '盲区多，存在监管死角', '人力成本持续上升'],
      icon: '🛠️',
      score: 2,
    },
    {
      name: '传统摄像头',
      problems: ['仅有录像功能', '事后才能追责', '无法主动预警'],
      icon: '📹',
      score: 3,
    },
    {
      name: '单一AI识别',
      problems: ['只发现不治理', '数据孤立，无法联动', '无法预测违规趋势'],
      icon: '🤖',
      score: 5,
    },
  ];

  solutions.forEach((s, i) => {
    const x = 0.5 + i * 4.2;
    const y = 1.5;

    // 卡片
    slide.addShape('rect', {
      x, y, w: 4.0, h: 3.4,
      fill: { color: THEME.white },
      shadow: { type: 'outer', blur: 5, offset: 2, angle: 45, color: '000000', opacity: 0.08 },
    });

    // 标题区
    slide.addShape('rect', {
      x, y, w: 4.0, h: 0.7,
      fill: { color: i === 2 ? THEME.accent : THEME.primary, transparency: i === 2 ? 0 : 0 },
    });
    slide.addText(`${s.icon} ${s.name}`, {
      x, y: y + 0.1, w: 4.0, h: 0.5,
      fontSize: 18, bold: true, color: THEME.white, align: 'center',
    });

    // 问题列表
    s.problems.forEach((prob, j) => {
      slide.addText(`✗ ${prob}`, {
        x: x + 0.2, y: y + 0.85 + j * 0.6, w: 3.6, h: 0.5,
        fontSize: 13, color: THEME.red, valign: 'top',
      });
    });

    // 评分
    slide.addText('综合评分', {
      x, y: y + 2.75, w: 4.0, h: 0.25,
      fontSize: 10, color: THEME.textLight, align: 'center',
    });
    slide.addText(`${s.score} / 10`, {
      x, y: y + 2.95, w: 4.0, h: 0.35,
      fontSize: 18, bold: true, color: s.score < 4 ? THEME.red : THEME.yellow, align: 'center',
    });
  });

  // 底部结论
  slide.addText('💡 核心差距：现有方案停留在"被动发现"阶段，缺乏预测能力、治理闭环和持续进化机制', {
    x: 0.5, y: 5.1, w: 12.33, h: 0.35,
    fontSize: 13, bold: true, color: THEME.primary, align: 'center',
  });
}

// ============================================================
// 第4页：解决方案总览
// ============================================================
function slide4_solution() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.dark };

  // 装饰圆
  slide.addShape('ellipse', {
    x: -2, y: -2, w: 6, h: 6,
    fill: { color: THEME.primary, transparency: 40 },
  });
  slide.addShape('ellipse', {
    x: 10, y: 3, w: 5, h: 5,
    fill: { color: THEME.accent, transparency: 20 },
  });

  // 顶部标题
  slide.addText('我们的解决方案', {
    x: 0.5, y: 0.4, w: 12.33, h: 0.5,
    fontSize: 28, bold: true, color: THEME.accent, align: 'center',
  });

  // 核心口号
  slide.addText('城市智眼 CityVision', {
    x: 0.5, y: 1.0, w: 12.33, h: 0.7,
    fontSize: 44, bold: true, color: THEME.white, align: 'center',
  });

  slide.addText('"预测 — 发现 — 治理 — 评估" 全链路闭环AI交通治理智能体', {
    x: 0.5, y: 1.75, w: 12.33, h: 0.4,
    fontSize: 16, color: THEME.secondary, align: 'center',
  });

  // 五层架构流程
  const layers = [
    { name: '感知层', desc: '摄像头+无人机+机器人', color: THEME.secondary },
    { name: '边缘层', desc: '本地AI实时推理', color: THEME.accent },
    { name: '云端层', desc: '多模态大模型分析', color: '8B5CF6' },
    { name: 'Agent层', desc: 'AI决策与自动化', color: THEME.accent2 },
    { name: '治理层', desc: '执法+预警+数字孪生', color: THEME.green },
  ];

  const layerW = 2.2;
  const startX = (13.33 - layerW * 5 - 0.2 * 4) / 2;
  layers.forEach((l, i) => {
    const x = startX + i * (layerW + 0.2);
    slide.addShape('rect', {
      x, y: 2.5, w: layerW, h: 0.65,
      fill: { color: l.color },
      shadow: { type: 'outer', blur: 4, offset: 2, angle: 45, color: '000000', opacity: 0.3 },
    });
    slide.addText(l.name, {
      x, y: 2.52, w: layerW, h: 0.35,
      fontSize: 14, bold: true, color: THEME.white, align: 'center',
    });
    slide.addText(l.desc, {
      x, y: 2.85, w: layerW, h: 0.25,
      fontSize: 10, color: THEME.white, align: 'center', transparency: 20,
    });

    // 箭头
    if (i < layers.length - 1) {
      slide.addText('→', {
        x: x + layerW, y: 2.52, w: 0.2, h: 0.65,
        fontSize: 20, color: THEME.accent, align: 'center', valign: 'middle',
      });
    }
  });

  // 三个关键词
  const keywords = [
    { word: '预测式', sub: '提前预警，主动治理' },
    { word: '自主化', sub: 'Agent自动决策执法' },
    { word: '可进化', sub: '持续学习，自我迭代' },
  ];

  keywords.forEach((kw, i) => {
    const x = 1.5 + i * 3.8;
    slide.addShape('rect', {
      x, y: 3.5, w: 3.4, h: 1.4,
      fill: { color: THEME.white, transparency: 90 },
      line: { color: THEME.accent, width: 2 },
    });
    slide.addText(kw.word, {
      x, y: 3.6, w: 3.4, h: 0.6,
      fontSize: 22, bold: true, color: THEME.accent, align: 'center',
    });
    slide.addText(kw.sub, {
      x, y: 4.2, w: 3.4, h: 0.5,
      fontSize: 12, color: THEME.white, align: 'center',
    });
  });

  // 底部
  slide.addText('不再是单一工具，而是城市交通治理的基础设施', {
    x: 0.5, y: 5.15, w: 12.33, h: 0.3,
    fontSize: 13, color: THEME.secondary, align: 'center',
  });
}

// ============================================================
// 第5页：核心技术演示
// ============================================================
function slide5_demo() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '核心技术演示', '本地YOLO + 云端大模型 · 端云协同架构');
  addFooter(slide);
  addPageNumber(slide, 5, 18);

  // 左侧：系统截图模拟区
  slide.addShape('rect', {
    x: 0.4, y: 1.5, w: 7.5, h: 3.9,
    fill: { color: THEME.dark },
    line: { color: 'E2E8F0', width: 1 },
    shadow: { type: 'outer', blur: 8, offset: 3, angle: 45, color: '000000', opacity: 0.15 },
  });

  // 模拟管理后台界面
  slide.addShape('rect', {
    x: 0.55, y: 1.65, w: 7.2, h: 0.4,
    fill: { color: '2D3748' },
  });
  slide.addText('🔍 智瞳灵声管理端 · 智能识别', {
    x: 0.7, y: 1.68, w: 6.5, h: 0.35,
    fontSize: 11, color: THEME.white,
  });

  // 模拟图片区
  slide.addShape('rect', {
    x: 0.7, y: 2.2, w: 3.8, h: 2.8,
    fill: { color: '1A1A2E' },
  });
  // 模拟YOLO检测框
  slide.addShape('rect', {
    x: 1.1, y: 2.7, w: 2.0, h: 1.2,
    line: { color: '00FF88', width: 2 },
  });
  slide.addText('car 95%', {
    x: 1.1, y: 3.9, w: 2.0, h: 0.25,
    fontSize: 9, color: '00FF88', align: 'center',
  });
  slide.addShape('rect', {
    x: 2.5, y: 2.9, w: 1.6, h: 0.8,
    line: { color: 'FFD700', width: 2 },
  });
  slide.addText('motor 87%', {
    x: 2.5, y: 3.7, w: 1.6, h: 0.25,
    fontSize: 9, color: 'FFD700', align: 'center',
  });

  // 右侧AI分析结果
  slide.addShape('rect', {
    x: 4.7, y: 2.2, w: 3.0, h: 2.8,
    fill: { color: '252A34' },
  });
  slide.addText('AI 推理链', {
    x: 4.85, y: 2.3, w: 2.7, h: 0.3,
    fontSize: 10, bold: true, color: THEME.accent,
  });
  slide.addText([
    { text: 'YOLOv8 检测', options: { bold: true, color: '4A90D9', breakLine: true } },
    { text: 'car × 1, motorcycle × 2\n', options: { color: 'BBBBBB', breakLine: true } },
    { text: '耗时: 48ms\n\n', options: { color: '888888', breakLine: true } },
    { text: '豆包大模型分析', options: { bold: true, color: '38A169', breakLine: true } },
    { text: '是否违规：是\n', options: { color: '38A169', breakLine: true } },
    { text: '置信度：87%\n\n', options: { color: '38A169', breakLine: true } },
    { text: '推理过程：\n在XX路口发现一辆红色\n摩托车驾驶员未佩戴头盔\n...', options: { color: 'BBBBBB', fontSize: 9 } },
  ], {
    x: 4.85, y: 2.65, w: 2.7, h: 2.2,
    fontSize: 10, color: THEME.white, valign: 'top',
    fontFace: FONTS.body,
  });

  // 右侧功能区
  const features = [
    { title: '本地边缘推理', desc: 'Jetson Nano嵌入式部署\nYOLOv8本地检测<50ms', icon: '⚡', color: THEME.accent },
    { title: '云端深度分析', desc: '豆包/Qwen-VL多模态\n大模型联合推理', icon: '☁️', color: THEME.primary },
    { title: '自进化持续学习', desc: '用户反馈→新标注\n→模型微调闭环', icon: '🔄', color: THEME.green },
    { title: '多场景覆盖', desc: '违停/逆行/闯红灯/\n压线/超速/未戴头盔', icon: '🏙️', color: THEME.accent2 },
  ];

  features.forEach((f, i) => {
    const x = 8.1 + (i % 2) * 2.5;
    const y = 1.5 + Math.floor(i / 2) * 2.1;

    slide.addShape('rect', {
      x, y, w: 2.35, h: 1.9,
      fill: { color: THEME.lightBg },
      line: { color: 'E2E8F0', width: 1 },
    });
    slide.addShape('rect', {
      x, y, w: 2.35, h: 0.06,
      fill: { color: f.color },
    });
    slide.addText(f.icon, {
      x, y: y + 0.1, w: 2.35, h: 0.4,
      fontSize: 20, align: 'center',
    });
    slide.addText(f.title, {
      x: x + 0.1, y: y + 0.5, w: 2.15, h: 0.35,
      fontSize: 12, bold: true, color: THEME.dark,
    });
    slide.addText(f.desc, {
      x: x + 0.1, y: y + 0.85, w: 2.15, h: 0.95,
      fontSize: 10, color: THEME.textLight,
      lineSpacingMultiple: 1.3,
    });
  });
}

// ============================================================
// 第6页：12个创新点概览
// ============================================================
function slide6_innovations() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.dark };

  // 标题
  slide.addText('核心创新点', {
    x: 0.5, y: 0.25, w: 12.33, h: 0.55,
    fontSize: 30, bold: true, color: THEME.white, align: 'center',
  });
  slide.addText('基于AI Agent架构，重新定义城市交通治理范式', {
    x: 0.5, y: 0.8, w: 12.33, h: 0.3,
    fontSize: 14, color: THEME.secondary, align: 'center',
  });

  const innovations = [
    { num: '01', name: '多Agent协同决策', tag: 'AI架构', color: '8B5CF6' },
    { num: '02', name: '预测式主动治理', tag: '行业首创', color: THEME.accent },
    { num: '03', name: '空地一体协同', tag: '立体感知', color: THEME.secondary },
    { num: '04', name: '多模态大模型', tag: '深度理解', color: 'EC4899' },
    { num: '05', name: '区块链证据链', tag: '司法级存证', color: THEME.green },
    { num: '06', name: '数字孪生平台', tag: '三维可视', color: THEME.accent2 },
    { num: '07', name: '边缘计算推理', tag: '离线可用', color: '06B6D4' },
    { num: '08', name: '自进化学习系统', tag: '越用越强', color: 'F59E0B' },
    { num: '09', name: '语音交互引导', tag: '发现即劝阻', color: 'EF4444' },
    { num: '10', name: 'Agent执法报告', tag: '自动生成', color: '10B981' },
    { num: '11', name: '开放API生态', tag: '赋能百业', color: '3B82F6' },
    { num: '12', name: '全栈国产化', tag: '自主可控', color: '6366F1' },
  ];

  innovations.forEach((inn, i) => {
    const col = i % 4;
    const row = Math.floor(i / 4);
    const x = 0.5 + col * 3.2;
    const y = 1.3 + row * 1.35;

    // 卡片背景
    slide.addShape('rect', {
      x, y, w: 3.0, h: 1.15,
      fill: { color: THEME.white, transparency: 92 },
      line: { color: inn.color, width: 1.5 },
    });
    // 编号
    slide.addText(inn.num, {
      x, y: y + 0.1, w: 3.0, h: 0.4,
      fontSize: 22, bold: true, color: inn.color, align: 'center',
    });
    // 名称
    slide.addText(inn.name, {
      x, y: y + 0.5, w: 3.0, h: 0.3,
      fontSize: 13, bold: true, color: THEME.white, align: 'center',
    });
    // 标签
    slide.addText(inn.tag, {
      x: x + 0.75, y: y + 0.8, w: 1.5, h: 0.25,
      fontSize: 9, color: THEME.white, align: 'center',
      fill: { color: inn.color },
    });
  });
}

// ============================================================
// 第7页：创新点详解①——多Agent协同
// ============================================================
function slide7_agent() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '创新点①', '多Agent协同决策架构');
  addFooter(slide);
  addPageNumber(slide, 7, 18);

  // Agent 流程图
  const agents = [
    { name: '感知Agent', role: '融合多源视频流\n目标检测追踪', color: THEME.secondary, x: 0.5 },
    { name: '分析Agent', role: '多模态深度理解\n违规分类置信评估', color: THEME.accent, x: 3.3 },
    { name: '预测Agent', role: '时序预测趋势\nGNN空间建模', color: '8B5CF6', x: 6.1 },
    { name: '执法Agent', role: '自动生成文书\n区块链存证推送', color: THEME.green, x: 8.9 },
  ];

  agents.forEach((a, i) => {
    // Agent 方块
    slide.addShape('rect', {
      x: a.x, y: 1.6, w: 2.6, h: 1.8,
      fill: { color: a.color },
      shadow: { type: 'outer', blur: 6, offset: 3, angle: 45, color: a.color, opacity: 0.4 },
    });
    slide.addText(a.name, {
      x: a.x, y: 1.7, w: 2.6, h: 0.5,
      fontSize: 16, bold: true, color: THEME.white, align: 'center',
    });
    slide.addShape('rect', {
      x: a.x + 0.3, y: 2.25, w: 2.0, h: 0.02,
      fill: { color: THEME.white, transparency: 50 },
    });
    slide.addText(a.role, {
      x: a.x + 0.1, y: 2.35, w: 2.4, h: 0.9,
      fontSize: 11, color: THEME.white, align: 'center',
      lineSpacingMultiple: 1.4,
    });

    // 箭头
    if (i < agents.length - 1) {
      slide.addText('→', {
        x: a.x + 2.6, y: 2.2, w: 0.5, h: 0.5,
        fontSize: 24, color: a.color, align: 'center', bold: true,
      });
    }
  });

  // 底部实际案例
  slide.addShape('rect', {
    x: 0.5, y: 3.7, w: 12.33, h: 1.7,
    fill: { color: THEME.lightBg },
  });
  slide.addText('实际工作流示例', {
    x: 0.7, y: 3.8, w: 4, h: 0.35,
    fontSize: 13, bold: true, color: THEME.primary,
  });

  const steps = [
    '① 摄像头检测到摩托车',
    '② Agent分析车牌+头盔',
    '③ 预测历史同类违规',
    '④ 生成执法报告+存证',
  ];
  steps.forEach((s, i) => {
    slide.addText(s, {
      x: 0.7 + i * 3.0, y: 4.25, w: 2.8, h: 0.4,
      fontSize: 12, color: THEME.text,
    });
    if (i < steps.length - 1) {
      slide.addText('▶', {
        x: 3.3 + i * 3.0, y: 4.25, w: 0.3, h: 0.4,
        fontSize: 12, color: THEME.accent, align: 'center',
      });
    }
  });

  slide.addText('全流程耗时：< 5秒  |  传统人工：30分钟以上', {
    x: 0.7, y: 4.8, w: 12, h: 0.35,
    fontSize: 12, bold: true, color: THEME.accent,
  });
}

// ============================================================
// 第8页：创新点详解②——预测式治理
// ============================================================
function slide8_predictive() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '创新点②', '预测式主动治理 —— 从"事后发现"到"事前预防"');
  addFooter(slide);
  addPageNumber(slide, 8, 18);

  // 左侧：预测模型输入
  slide.addText('预测数据输入', {
    x: 0.5, y: 1.4, w: 3.5, h: 0.35,
    fontSize: 14, bold: true, color: THEME.primary,
  });

  const dataSources = [
    { name: '历史违规记录', freq: '30天', impact: '周期性规律', color: THEME.secondary },
    { name: '天气预报API', freq: '每小时', impact: '雨天头盔违规+3倍', color: THEME.accent },
    { name: '节假日日历', freq: '实时', impact: '节假日违停高发', color: THEME.accent2 },
    { name: '学校课表', freq: '学期制', impact: '开学季接送违停', color: '8B5CF6' },
    { name: '大型活动', freq: '实时', impact: '临时管控需求', color: THEME.green },
    { name: '实时路况', freq: '每5分钟', impact: '拥堵预测', color: THEME.yellow },
  ];

  dataSources.forEach((ds, i) => {
    const y = 1.85 + i * 0.55;
    slide.addShape('rect', {
      x: 0.5, y, w: 0.08, h: 0.4,
      fill: { color: ds.color },
    });
    slide.addText(ds.name, {
      x: 0.7, y, w: 1.8, h: 0.4,
      fontSize: 12, color: THEME.dark,
    });
    slide.addText(ds.freq, {
      x: 2.5, y, w: 0.7, h: 0.4,
      fontSize: 10, color: THEME.textLight,
    });
    slide.addText(ds.impact, {
      x: 3.2, y, w: 2.0, h: 0.4,
      fontSize: 10, color: THEME.text,
    });
  });

  // 中间：预测融合
  slide.addShape('rect', {
    x: 5.3, y: 1.85, w: 2.8, h: 3.2,
    fill: { color: THEME.dark },
    shadow: { type: 'outer', blur: 8, offset: 3, angle: 45, color: '000000', opacity: 0.2 },
  });
  slide.addText('预测融合层', {
    x: 5.3, y: 1.95, w: 2.8, h: 0.4,
    fontSize: 13, bold: true, color: THEME.accent, align: 'center',
  });
  slide.addText('LSTM\n时序预测', {
    x: 5.5, y: 2.45, w: 2.4, h: 0.6,
    fontSize: 11, color: THEME.secondary, align: 'center',
  });
  slide.addText('GNN\n空间预测', {
    x: 5.5, y: 3.1, w: 2.4, h: 0.6,
    fontSize: 11, color: THEME.accent, align: 'center',
  });
  slide.addText('Transformer\n事件关联', {
    x: 5.5, y: 3.75, w: 2.4, h: 0.6,
    fontSize: 11, color: '8B5CF6', align: 'center',
  });
  slide.addText('MoE 混合专家', {
    x: 5.5, y: 4.45, w: 2.4, h: 0.4,
    fontSize: 11, bold: true, color: THEME.white, align: 'center',
  });

  // 箭头
  slide.addText('▶', {
    x: 8.1, y: 3.2, w: 0.4, h: 0.5,
    fontSize: 20, color: THEME.accent, align: 'center',
  });

  // 右侧：预测报告示例
  slide.addShape('rect', {
    x: 8.5, y: 1.4, w: 4.5, h: 4.0,
    fill: { color: THEME.lightBg },
    line: { color: 'E2E8F0', width: 1 },
  });
  slide.addShape('rect', {
    x: 8.5, y: 1.4, w: 4.5, h: 0.5,
    fill: { color: THEME.primary },
  });
  slide.addText('📊 明日治理预测报告', {
    x: 8.7, y: 1.48, w: 4.1, h: 0.35,
    fontSize: 12, bold: true, color: THEME.white,
  });

  slide.addText('🚨 红色预警', {
    x: 8.7, y: 2.0, w: 4.1, h: 0.3,
    fontSize: 11, bold: true, color: THEME.red,
  });
  slide.addText('人民路与建设路路口\n17:00-19:00 违停风险 92%\n原因：商场下班高峰+停车位不足', {
    x: 8.7, y: 2.3, w: 4.1, h: 0.9,
    fontSize: 10, color: THEME.text,
  });

  slide.addText('🔶 橙色预警', {
    x: 8.7, y: 3.3, w: 4.1, h: 0.3,
    fontSize: 11, bold: true, color: THEME.accent2,
  });
  slide.addText('科技大学南门\n07:30-08:30 逆行风险 75%\n建议：提前部署巡逻机器人', {
    x: 8.7, y: 3.6, w: 4.1, h: 0.8,
    fontSize: 10, color: THEME.text,
  });

  slide.addText('准确率: 78%  |  提前预警: 2.3小时', {
    x: 8.7, y: 4.55, w: 4.1, h: 0.3,
    fontSize: 10, bold: true, color: THEME.accent,
  });
}

// ============================================================
// 第9页：创新点详解③——空地协同
// ============================================================
function slide9_coordination() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '创新点③', '空地一体协同巡航 —— 无死角、全天候、立体化感知');
  addFooter(slide);
  addPageNumber(slide, 9, 18);

  // 三层架构图
  const layers = [
    {
      name: '空中层 · 无人机',
      height: '200m高空',
      role: '主干道全覆盖 | 应急响应 | 突发事件俯拍',
      color: THEME.secondary,
      y: 1.4,
    },
    {
      name: '边缘层 · AI-BOX',
      height: '地面设备',
      role: '固定摄像头网络 | 全天候7×24h | 边缘推理50ms',
      color: THEME.accent,
      y: 2.8,
    },
    {
      name: '移动层 · 巡逻机器人',
      height: '地面移动',
      role: '盲区/辅路/校园 | 移动抓拍+语音劝阻',
      color: THEME.green,
      y: 4.2,
    },
  ];

  layers.forEach((l) => {
    slide.addShape('rect', {
      x: 0.5, y: l.y, w: 5.5, h: 1.15,
      fill: { color: l.color, transparency: 10 },
      line: { color: l.color, width: 2 },
    });
    slide.addText(l.name, {
      x: 0.7, y: l.y + 0.1, w: 5.1, h: 0.4,
      fontSize: 16, bold: true, color: l.color,
    });
    slide.addText(l.height, {
      x: 0.7, y: l.y + 0.5, w: 1.5, h: 0.25,
      fontSize: 10, color: THEME.textLight,
    });
    slide.addText(l.role, {
      x: 0.7, y: l.y + 0.75, w: 5.1, h: 0.3,
      fontSize: 12, color: THEME.text,
    });
  });

  // 连接线
  slide.addShape('line', {
    x: 3.0, y: 2.55, w: 0, h: 0.25,
    line: { color: THEME.textLight, width: 2, dashType: 'dash' },
  });
  slide.addShape('line', {
    x: 3.0, y: 3.95, w: 0, h: 0.25,
    line: { color: THEME.textLight, width: 2, dashType: 'dash' },
  });

  // 右侧：协同闭环
  slide.addShape('rect', {
    x: 6.3, y: 1.4, w: 6.7, h: 3.95,
    fill: { color: THEME.lightBg },
  });
  slide.addText('空地协同完整闭环', {
    x: 6.5, y: 1.5, w: 6.3, h: 0.4,
    fontSize: 15, bold: true, color: THEME.primary,
  });

  const loop = [
    { step: '发现', desc: '任一感知源检测到异常', icon: '🔍', color: THEME.secondary },
    { step: '跟踪', desc: '移动源追踪+多点定位', icon: '🎯', color: THEME.accent },
    { step: '取证', desc: '多角度证据+区块链存证', icon: '📋', color: '8B5CF6' },
    { step: '治理', desc: '语音劝阻/推送交警/生成文书', icon: '⚖️', color: THEME.green },
    { step: '评估', desc: '治理效果反馈→模型自进化', icon: '📈', color: THEME.accent2 },
  ];

  loop.forEach((l, i) => {
    const y = 2.0 + i * 0.7;
    slide.addShape('rect', {
      x: 6.6, y, w: 1.2, h: 0.55,
      fill: { color: l.color },
    });
    slide.addText(l.step, {
      x: 6.6, y: y + 0.08, w: 1.2, h: 0.4,
      fontSize: 13, bold: true, color: THEME.white, align: 'center',
    });
    slide.addText(l.icon, {
      x: 7.85, y, w: 0.4, h: 0.55,
      fontSize: 16, align: 'center', valign: 'middle',
    });
    slide.addText(l.desc, {
      x: 8.25, y: y + 0.08, w: 4.5, h: 0.4,
      fontSize: 12, color: THEME.text,
    });
    if (i < loop.length - 1) {
      slide.addText('↓', {
        x: 6.6, y: y + 0.55, w: 1.2, h: 0.15,
        fontSize: 12, color: l.color, align: 'center',
      });
    }
  });
}

// ============================================================
// 第10页：技术架构
// ============================================================
function slide10_architecture() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '系统技术架构', '六层架构 · 端云协同 · 自主可控');
  addFooter(slide);
  addPageNumber(slide, 10, 18);

  const archLayers = [
    { name: '数字孪生展示层', tech: 'Web + 3D大屏 + 移动端', color: THEME.accent2 },
    { name: 'Agent决策层', tech: '多Agent协同 + 大模型（豆包/Qwen+DeepSeek）', color: '8B5CF6' },
    { name: '云端AI分析层', tech: '多模态大模型 · 时序预测 · 知识图谱', color: THEME.accent },
    { name: '边缘计算层', tech: 'Jetson Nano/TX2 · TensorRT · YOLOv8', color: THEME.secondary },
    { name: '感知执行层', tech: '摄像头 + 无人机 + 巡逻机器人', color: THEME.primary },
    { name: '数据存储层', tech: 'PostgreSQL · 文件存储 · 区块链存证', color: THEME.green },
  ];

  archLayers.forEach((layer, i) => {
    const y = 1.4 + i * 0.68;
    const w = 8.5;

    slide.addShape('rect', {
      x: 0.5, y, w, h: 0.58,
      fill: { color: layer.color },
      shadow: { type: 'outer', blur: 3, offset: 2, angle: 45, color: layer.color, opacity: 0.3 },
    });
    slide.addText(layer.name, {
      x: 0.65, y: y + 0.08, w: 2.5, h: 0.42,
      fontSize: 13, bold: true, color: THEME.white,
    });
    slide.addText(layer.tech, {
      x: 3.3, y: y + 0.08, w: 5.5, h: 0.42,
      fontSize: 12, color: THEME.white, transparency: 10,
    });
  });

  // 右侧：技术栈
  slide.addShape('rect', {
    x: 9.2, y: 1.4, w: 3.8, h: 4.0,
    fill: { color: THEME.lightBg },
  });
  slide.addText('技术栈', {
    x: 9.4, y: 1.5, w: 3.4, h: 0.4,
    fontSize: 14, bold: true, color: THEME.primary,
  });

  const techStack = [
    ['前端', 'Vue3 + Element Plus'],
    ['后端', 'FastAPI + Python'],
    ['AI检测', 'YOLOv8 + DeepSORT'],
    ['大模型', '豆包 + DeepSeek'],
    ['边缘', 'TensorRT + Jetson'],
    ['数据库', 'PostgreSQL + SQLite'],
    ['存证', 'Hyperledger Fabric'],
  ];

  techStack.forEach((t, i) => {
    const y = 2.0 + i * 0.48;
    slide.addShape('rect', {
      x: 9.4, y, w: 1.0, h: 0.36,
      fill: { color: THEME.primary },
    });
    slide.addText(t[0], {
      x: 9.4, y: y + 0.04, w: 1.0, h: 0.3,
      fontSize: 10, bold: true, color: THEME.white, align: 'center',
    });
    slide.addText(t[1], {
      x: 10.5, y: y + 0.04, w: 2.3, h: 0.3,
      fontSize: 11, color: THEME.text,
    });
  });

  // 国产化标签
  addTag(slide, 9.4, 5.1, '✓ 全栈国产化自主可控', THEME.green);
}

// ============================================================
// 第11页：AI Agent深度解析
// ============================================================
function slide11_agent_deep() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.dark };

  slide.addText('AI Agent 深度解析', {
    x: 0.5, y: 0.25, w: 12.33, h: 0.5,
    fontSize: 28, bold: true, color: THEME.white,
  });
  slide.addText('交通治理Agent能力矩阵', {
    x: 0.5, y: 0.75, w: 12.33, h: 0.3,
    fontSize: 14, color: THEME.secondary,
  });

  const agentMatrix = [
    {
      agent: '感知Agent',
      abilities: ['多源视频流融合', '目标检测+追踪', '异常行为识别'],
      output: '标准化违规事件元数据',
      color: THEME.secondary,
    },
    {
      agent: '分析Agent',
      abilities: ['多模态深度理解', '违规自动分类', '置信度评估'],
      output: '带证据链的违规分析报告',
      color: THEME.accent,
    },
    {
      agent: '预测Agent',
      abilities: ['LSTM时序预测', 'GNN空间建模', '事件关联分析'],
      output: '明日/本周违规热力图',
      color: '8B5CF6',
    },
    {
      agent: '执法Agent',
      abilities: ['自动生成执法文书', '区块链证据上链', '对接交管平台'],
      output: '可直接提交的电子证据包',
      color: THEME.green,
    },
  ];

  agentMatrix.forEach((a, i) => {
    const x = 0.4 + i * 3.2;

    slide.addShape('rect', {
      x, y: 1.25, w: 3.05, h: 4.1,
      fill: { color: THEME.white, transparency: 95 },
      line: { color: a.color, width: 2 },
    });
    slide.addShape('rect', {
      x, y: 1.25, w: 3.05, h: 0.65,
      fill: { color: a.color },
    });
    slide.addText(a.agent, {
      x, y: 1.32, w: 3.05, h: 0.5,
      fontSize: 15, bold: true, color: THEME.white, align: 'center',
    });

    slide.addText('核心能力', {
      x: x + 0.15, y: 2.0, w: 2.75, h: 0.3,
      fontSize: 10, color: THEME.secondary,
    });
    a.abilities.forEach((ab, j) => {
      slide.addText(`▸ ${ab}`, {
        x: x + 0.15, y: 2.35 + j * 0.45, w: 2.75, h: 0.4,
        fontSize: 12, color: THEME.white,
      });
    });

    slide.addShape('rect', {
      x: x + 0.15, y: 3.75, w: 2.75, h: 0.02,
      fill: { color: a.color, transparency: 50 },
    });

    slide.addText('输出', {
      x: x + 0.15, y: 3.85, w: 2.75, h: 0.25,
      fontSize: 10, color: THEME.secondary,
    });
    slide.addText(a.output, {
      x: x + 0.15, y: 4.15, w: 2.75, h: 0.9,
      fontSize: 11, color: a.color, bold: true,
      lineSpacingMultiple: 1.3,
    });
  });

  addFooter(slide);
  addPageNumber(slide, 11, 18);
}

// ============================================================
// 第12页：数字孪生平台
// ============================================================
function slide12_digital_twin() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.dark };

  slide.addText('数字孪生城市态势平台', {
    x: 0.5, y: 0.3, w: 12.33, h: 0.6,
    fontSize: 30, bold: true, color: THEME.white, align: 'center',
  });
  slide.addText('虚实融合 · 实时映射 · 全域感知', {
    x: 0.5, y: 0.9, w: 12.33, h: 0.3,
    fontSize: 14, color: THEME.accent, align: 'center',
  });

  // 模拟3D城市俯视图
  slide.addShape('rect', {
    x: 0.5, y: 1.4, w: 8.5, h: 3.8,
    fill: { color: '0D1B2A' },
    line: { color: THEME.secondary, width: 1 },
  });

  // 模拟道路网格
  const roadColor = '1B3A6B';
  slide.addShape('rect', { x: 0.5, y: 2.8, w: 8.5, h: 0.15, fill: { color: roadColor } });
  slide.addShape('rect', { x: 0.5, y: 3.6, w: 8.5, h: 0.1, fill: { color: roadColor } });
  slide.addShape('rect', { x: 3.0, y: 1.4, w: 0.12, h: 3.8, fill: { color: roadColor } });
  slide.addShape('rect', { x: 5.5, y: 1.4, w: 0.12, h: 3.8, fill: { color: roadColor } });
  slide.addShape('rect', { x: 7.5, y: 1.4, w: 0.12, h: 3.8, fill: { color: roadColor } });

  // 模拟建筑
  const buildings = [
    { x: 0.7, y: 1.6, w: 1.8, h: 1.0, color: '1B3A6B' },
    { x: 3.3, y: 1.6, w: 1.8, h: 0.9, color: '0D2137' },
    { x: 5.8, y: 1.6, w: 1.4, h: 1.2, color: '1B3A6B' },
    { x: 0.7, y: 4.0, w: 1.5, h: 0.8, color: '0D2137' },
    { x: 3.3, y: 4.0, w: 1.8, h: 0.8, color: '1B3A6B' },
    { x: 5.8, y: 4.0, w: 1.4, h: 0.7, color: '0D2137' },
  ];
  buildings.forEach(b => {
    slide.addShape('rect', {
      x: b.x, y: b.y, w: b.w, h: b.h,
      fill: { color: b.color, transparency: 30 },
      line: { color: THEME.secondary, width: 0.5 },
    });
  });

  // 模拟违规标注点
  const violations = [
    { x: 3.7, y: 2.95, color: THEME.red },
    { x: 5.7, y: 3.75, color: THEME.accent2 },
    { x: 6.0, y: 4.4, color: THEME.red },
    { x: 3.2, y: 4.4, color: THEME.yellow },
  ];
  violations.forEach(v => {
    slide.addShape('ellipse', {
      x: v.x - 0.15, y: v.y - 0.15, w: 0.3, h: 0.3,
      fill: { color: v.color },
    });
  });

  // 模拟文字标注
  slide.addText('违停 🚨', {
    x: 3.5, y: 2.72, w: 0.7, h: 0.2,
    fontSize: 8, color: THEME.red,
  });
  slide.addText('逆行 ⚠️', {
    x: 5.5, y: 3.6, w: 0.7, h: 0.2,
    fontSize: 8, color: THEME.accent2,
  });

  // 右侧统计面板
  slide.addShape('rect', {
    x: 9.2, y: 1.4, w: 3.85, h: 3.8,
    fill: { color: THEME.white, transparency: 95 },
  });

  const stats = [
    { label: '在线设备', value: '1,247', unit: '台', color: THEME.accent },
    { label: '今日违规', value: '386', unit: '起', color: THEME.accent2 },
    { label: '已处理', value: '341', unit: '起', color: THEME.green },
    { label: '预测预警', value: '47', unit: '条', color: THEME.yellow },
  ];

  stats.forEach((s, i) => {
    const y = 1.55 + i * 0.9;
    slide.addShape('rect', {
      x: 9.35, y, w: 3.55, h: 0.75,
      fill: { color: s.color, transparency: 85 },
    });
    slide.addText(s.value, {
      x: 9.5, y: y + 0.08, w: 1.8, h: 0.45,
      fontSize: 24, bold: true, color: s.color,
    });
    slide.addText(s.unit, {
      x: 11.3, y: y + 0.2, w: 0.5, h: 0.3,
      fontSize: 12, color: THEME.textLight,
    });
    slide.addText(s.label, {
      x: 9.5, y: y + 0.5, w: 3.2, h: 0.2,
      fontSize: 11, color: THEME.text,
    });
  });

  // 底部说明
  slide.addText('💡 点击任意违规点 → 弹出完整证据链 + AI分析过程 + 执法报告', {
    x: 0.5, y: 5.15, w: 12.33, h: 0.3,
    fontSize: 12, color: THEME.secondary, align: 'center',
  });

  addFooter(slide);
  addPageNumber(slide, 12, 18);
}

// ============================================================
// 第13页：自进化系统
// ============================================================
function slide13_evolution() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '创新点⑧', '自进化持续学习系统 —— 越用越聪明');
  addFooter(slide);
  addPageNumber(slide, 13, 18);

  // 闭环流程图
  const loop = [
    { step: '① 发现违规', desc: 'AI自动检测', color: THEME.secondary },
    { step: '② 用户审核', desc: '确认/驳回AI判断', color: THEME.accent },
    { step: '③ 新增标注', desc: '视为高质量训练数据', color: '8B5CF6' },
    { step: '④ 模型微调', desc: '定期触发模型更新', color: THEME.green },
    { step: '⑤ Shadow测试', desc: '新模型并行验证', color: THEME.accent2 },
    { step: '⑥ 线上部署', desc: '通过后替换旧模型', color: THEME.primary },
  ];

  loop.forEach((l, i) => {
    const x = 0.5 + i * 2.1;

    slide.addShape('rect', {
      x, y: 1.7, w: 1.9, h: 0.65,
      fill: { color: l.color },
      shadow: { type: 'outer', blur: 4, offset: 2, angle: 45, color: l.color, opacity: 0.3 },
    });
    slide.addText(l.step, {
      x, y: 1.72, w: 1.9, h: 0.35,
      fontSize: 11, bold: true, color: THEME.white, align: 'center',
    });
    slide.addText(l.desc, {
      x, y: 2.05, w: 1.9, h: 0.25,
      fontSize: 9, color: THEME.white, align: 'center', transparency: 20,
    });

    if (i < loop.length - 1) {
      slide.addText('→', {
        x: x + 1.9, y: 1.8, w: 0.2, h: 0.5,
        fontSize: 16, color: l.color, align: 'center',
      });
    }
  });

  // 数据展示
  slide.addShape('rect', {
    x: 0.5, y: 2.6, w: 12.33, h: 2.7,
    fill: { color: THEME.lightBg },
  });

  slide.addText('上线效果数据（某试点城市，3个月）', {
    x: 0.7, y: 2.7, w: 6, h: 0.35,
    fontSize: 13, bold: true, color: THEME.primary,
  });

  const dataMetrics = [
    { label: '初始准确率', value: '82%', arrow: '→', end: '91%', improvement: '+9%', color: THEME.accent },
    { label: '日均处理事件', value: '120', arrow: '→', end: '580', improvement: '+383%', color: THEME.green },
    { label: '误报率', value: '18%', arrow: '→', end: '5%', improvement: '-72%', color: THEME.primary },
    { label: '执法效率', value: '30min', arrow: '→', end: '4.5min', improvement: '-85%', color: THEME.accent2 },
  ];

  dataMetrics.forEach((m, i) => {
    const x = 0.7 + i * 3.1;
    slide.addText(m.label, {
      x, y: 3.15, w: 2.9, h: 0.3,
      fontSize: 11, color: THEME.textLight,
    });
    slide.addText(`${m.value} ${m.arrow} ${m.end}`, {
      x, y: 3.5, w: 2.9, h: 0.4,
      fontSize: 16, bold: true, color: m.color,
    });
    slide.addText(m.improvement, {
      x, y: 3.95, w: 2.9, h: 0.3,
      fontSize: 20, bold: true, color: m.color,
    });
  });

  slide.addText('💡 核心价值：系统不是一次性训练，而是持续进化的智能体，每次用户交互都是学习机会', {
    x: 0.7, y: 4.6, w: 11.9, h: 0.35,
    fontSize: 12, bold: true, color: THEME.primary,
  });
}

// ============================================================
// 第14页：商业模式
// ============================================================
function slide14_business() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '商业模式', '三条收入线 · 多场景变现');
  addFooter(slide);
  addPageNumber(slide, 14, 18);

  const models = [
    {
      type: 'To G',
      target: '政府客户',
      icon: '🏛️',
      clients: '区县级交警支队\n智慧城市运营中心\n城市管理局',
      price: '30-80万/年\n（区县级）\n200-500万/年\n（省市级）',
      highlight: '核心收入来源',
      color: THEME.primary,
      reason: '降低50%人力成本\n数字化考核加分\n证据链直连法院',
    },
    {
      type: 'To B',
      target: '企业客户',
      icon: '🏢',
      clients: '物业公司\n商业综合体\n物流公司\n车企',
      price: 'API: 0.1元/次\nSaaS: 2999元/月\n数据报告: 5000元/次',
      highlight: '快速现金收入',
      color: THEME.accent,
      reason: '降低企业管理成本\n提升安全合规性\n数据增值服务',
    },
    {
      type: 'To School',
      target: '高校客户',
      icon: '🎓',
      clients: '开设智慧交通\n人工智能专业高校',
      price: '实验室建设方案\n15-30万/校',
      highlight: '品牌+数据积累',
      color: THEME.green,
      reason: '教学+竞赛训练\n联合论文发表\n打磨产品+积累数据',
    },
  ];

  models.forEach((m, i) => {
    const x = 0.4 + i * 4.3;

    slide.addShape('rect', {
      x, y: 1.4, w: 4.1, h: 4.0,
      fill: { color: THEME.white },
      line: { color: m.color, width: 2 },
      shadow: { type: 'outer', blur: 6, offset: 3, angle: 45, color: '000000', opacity: 0.1 },
    });

    // 顶部
    slide.addShape('rect', {
      x, y: 1.4, w: 4.1, h: 0.75,
      fill: { color: m.color },
    });
    slide.addText(`${m.icon} ${m.type}`, {
      x, y: 1.48, w: 4.1, h: 0.35,
      fontSize: 18, bold: true, color: THEME.white, align: 'center',
    });
    slide.addText(m.target, {
      x, y: 1.8, w: 4.1, h: 0.3,
      fontSize: 11, color: THEME.white, align: 'center', transparency: 15,
    });

    // 客户
    slide.addText('目标客户', {
      x: x + 0.2, y: 2.25, w: 3.7, h: 0.25,
      fontSize: 10, bold: true, color: m.color,
    });
    slide.addText(m.clients, {
      x: x + 0.2, y: 2.5, w: 3.7, h: 0.9,
      fontSize: 11, color: THEME.text,
      lineSpacingMultiple: 1.3,
    });

    // 价格
    slide.addText('收费标准', {
      x: x + 0.2, y: 3.45, w: 3.7, h: 0.25,
      fontSize: 10, bold: true, color: m.color,
    });
    slide.addText(m.price, {
      x: x + 0.2, y: 3.7, w: 3.7, h: 0.8,
      fontSize: 11, bold: true, color: THEME.dark,
      lineSpacingMultiple: 1.2,
    });

    // 付费原因
    slide.addText('付费驱动力', {
      x: x + 0.2, y: 4.55, w: 3.7, h: 0.2,
      fontSize: 10, bold: true, color: m.color,
    });
    slide.addText(m.reason, {
      x: x + 0.2, y: 4.78, w: 3.7, h: 0.55,
      fontSize: 10, color: THEME.textLight,
      lineSpacingMultiple: 1.2,
    });
  });

  // 市场规模
  slide.addShape('rect', {
    x: 0.4, y: 5.22, w: 12.53, h: 0.3,
    fill: { color: THEME.accent },
  });
  slide.addText('目标市场：2025年智慧交通市场1200亿元 · 5年覆盖200城市 · 潜在规模40亿元', {
    x: 0.4, y: 5.22, w: 12.53, h: 0.3,
    fontSize: 11, bold: true, color: THEME.white, align: 'center',
  });
}

// ============================================================
// 第15页：竞争优势
// ============================================================
function slide15_competition() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.lightBg };

  addTitleBar(slide, '竞争优势', '不是替代，而是赋能');
  addFooter(slide);
  addPageNumber(slide, 15, 18);

  // 对比表格
  slide.addShape('rect', {
    x: 0.5, y: 1.5, w: 12.33, h: 0.55,
    fill: { color: THEME.primary },
  });
  const headers = ['对比维度', '海康/大华/华为云', '城市智眼'];
  const headerWidths = [3.0, 4.66, 4.67];
  let xPos = 0.5;
  headers.forEach((h, i) => {
    slide.addText(h, {
      x: xPos, y: 1.55, w: headerWidths[i], h: 0.45,
      fontSize: 14, bold: true, color: THEME.white, align: 'center',
    });
    xPos += headerWidths[i];
  });

  const rows = [
    ['核心定位', '硬件设备/视频存储', 'AI决策大脑（赋能硬件）'],
    ['治理能力', '仅录像存档', '预测+执法+评估全链路'],
    ['AI技术', '单一目标检测', '多Agent协同+大模型'],
    ['预测能力', '无', '历史数据驱动的违规预测'],
    ['进化能力', '固定版本', '自进化持续学习'],
    ['证据链', '截图存档', '区块链司法级存证'],
    ['商业模式', '卖设备', 'SaaS服务+API生态'],
  ];

  rows.forEach((row, i) => {
    const y = 2.05 + i * 0.5;
    const bgColor = i % 2 === 0 ? THEME.white : THEME.lightBg;
    slide.addShape('rect', {
      x: 0.5, y, w: 12.33, h: 0.5,
      fill: { color: bgColor },
      line: { color: 'E2E8F0', width: 0.5 },
    });

    let x = 0.5;
    const w = [3.0, 4.66, 4.67];
    row.forEach((cell, ci) => {
      const isLast = ci === 2;
      slide.addText(cell, {
        x: x + 0.15, y: y + 0.08, w: w[ci] - 0.3, h: 0.35,
        fontSize: 12, color: isLast ? THEME.accent : THEME.text,
        bold: isLast,
      });
      x += w[ci];
    });
  });

  // 底部总结
  slide.addText('💡 定位：成为智慧交通的"AI大脑"，赋能现有硬件生态，而非替代', {
    x: 0.5, y: 5.7, w: 12.33, h: 0.3,
    fontSize: 12, bold: true, color: THEME.primary, align: 'center',
  });
}

// ============================================================
// 第16页：社会价值
// ============================================================
function slide16_social() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.dark };

  // 装饰
  slide.addShape('ellipse', {
    x: -1, y: -1, w: 4, h: 4,
    fill: { color: THEME.primary, transparency: 50 },
  });
  slide.addShape('ellipse', {
    x: 11, y: 4, w: 4, h: 4,
    fill: { color: THEME.accent, transparency: 30 },
  });

  slide.addText('社会价值', {
    x: 0.5, y: 0.35, w: 12.33, h: 0.6,
    fontSize: 32, bold: true, color: THEME.white, align: 'center',
  });
  slide.addText('用AI守护每一次出行，让城市交通更安全', {
    x: 0.5, y: 0.95, w: 12.33, h: 0.3,
    fontSize: 14, color: THEME.accent, align: 'center',
  });

  const values = [
    {
      icon: '🚗', title: '减少交通事故',
      desc: '通过提前预警和主动治理，\n预计减少因交通违法导致的\n事故死亡率',
      metric: '↓ 30%',
      color: THEME.red,
    },
    {
      icon: '🌿', title: '降低碳排放',
      desc: '减少无效巡逻里程，\n优化交通流，\n降低拥堵导致的额外排放',
      metric: '↓ 15%',
      color: THEME.green,
    },
    {
      icon: '💰', title: '节省治理成本',
      desc: '用AI替代部分人工巡查，\n为财政节省大量\n人力物力投入',
      metric: '↓ 50%',
      color: THEME.accent,
    },
    {
      icon: '🏙️', title: '推动智慧城市建设',
      desc: '为城市交通治理提供\n可复制的AI基础设施，\n推动数字中国战略落地',
      metric: '标杆案例',
      color: THEME.primary,
    },
  ];

  values.forEach((v, i) => {
    const x = 0.4 + i * 3.2;

    slide.addShape('rect', {
      x, y: 1.5, w: 3.05, h: 3.5,
      fill: { color: THEME.white, transparency: 92 },
      line: { color: v.color, width: 2 },
    });
    slide.addText(v.icon, {
      x, y: 1.6, w: 3.05, h: 0.55,
      fontSize: 28, align: 'center',
    });
    slide.addText(v.title, {
      x, y: 2.2, w: 3.05, h: 0.4,
      fontSize: 15, bold: true, color: THEME.white, align: 'center',
    });
    slide.addText(v.desc, {
      x: x + 0.15, y: 2.65, w: 2.75, h: 1.4,
      fontSize: 11, color: 'AAAAAA', align: 'center',
      lineSpacingMultiple: 1.4,
    });
    slide.addShape('rect', {
      x: x + 0.3, y: 4.15, w: 2.45, h: 0.65,
      fill: { color: v.color, transparency: 20 },
    });
    slide.addText(v.metric, {
      x: x + 0.3, y: 4.2, w: 2.45, h: 0.55,
      fontSize: 20, bold: true, color: v.color, align: 'center',
    });
  });

  // 底部联合国目标
  slide.addText('契合联合国可持续发展目标（SDG）11.2 可持续交通', {
    x: 0.5, y: 5.15, w: 12.33, h: 0.3,
    fontSize: 12, color: THEME.secondary, align: 'center',
  });

  addFooter(slide);
  addPageNumber(slide, 16, 18);
}

// ============================================================
// 第17页：未来路线图
// ============================================================
function slide17_roadmap() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.white };

  addTitleBar(slide, '发展路线图', '2026 — 2030 五年规划');
  addFooter(slide);
  addPageNumber(slide, 17, 18);

  const roadmap = [
    { year: '2026', phase: '播种期', goal: '校园试点+3个政府试点', milestone: '完成基础平台搭建\n3个城市部署', color: THEME.secondary },
    { year: '2027', phase: '验证期', goal: '产品打磨+数据积累', milestone: '覆盖10个城市\n准确率>95%', color: THEME.accent },
    { year: '2028', phase: '扩张期', goal: '规模化复制+生态建设', milestone: '覆盖50个城市\n开放API生态', color: '8B5CF6' },
    { year: '2029', phase: '引领期', goal: '参与行业标准制定', milestone: '发布标准白皮书\n行业影响力', color: THEME.accent2 },
    { year: '2030', phase: '生态期', goal: '城市交通治理基础设施', milestone: '200+城市覆盖\n日处理千万事件', color: THEME.green },
  ];

  // 时间轴线
  slide.addShape('line', {
    x: 1.2, y: 2.5, w: 11.13, h: 0,
    line: { color: THEME.secondary, width: 3 },
  });

  roadmap.forEach((r, i) => {
    const x = 0.4 + i * 2.5;

    // 年份圆点
    slide.addShape('ellipse', {
      x: x + 0.85, y: 2.35, w: 0.3, h: 0.3,
      fill: { color: r.color },
    });

    // 年份
    slide.addText(r.year, {
      x, y: 1.85, w: 2.0, h: 0.4,
      fontSize: 22, bold: true, color: r.color, align: 'center',
    });
    slide.addText(r.phase, {
      x, y: 2.25, w: 2.0, h: 0.25,
      fontSize: 11, color: THEME.textLight, align: 'center',
    });

    // 内容卡片
    slide.addShape('rect', {
      x, y: 2.85, w: 2.3, h: 2.4,
      fill: { color: r.color, transparency: 90 },
      line: { color: r.color, width: 1.5 },
    });
    slide.addText(r.goal, {
      x: x + 0.1, y: 2.95, w: 2.1, h: 0.7,
      fontSize: 12, bold: true, color: THEME.dark,
      lineSpacingMultiple: 1.2,
    });
    slide.addShape('rect', {
      x: x + 0.1, y: 3.7, w: 2.1, h: 0.02,
      fill: { color: r.color, transparency: 50 },
    });
    slide.addText(r.milestone, {
      x: x + 0.1, y: 3.8, w: 2.1, h: 1.2,
      fontSize: 11, color: THEME.text,
      lineSpacingMultiple: 1.3,
    });
  });
}

// ============================================================
// 第18页：团队与致谢
// ============================================================
function slide18_team() {
  const slide = pptx.addSlide();
  slide.background = { color: THEME.dark };

  // 装饰
  slide.addShape('ellipse', {
    x: -2, y: -2, w: 6, h: 6,
    fill: { color: THEME.primary, transparency: 40 },
  });
  slide.addShape('ellipse', {
    x: 10, y: 3, w: 5, h: 5,
    fill: { color: THEME.accent, transparency: 20 },
  });

  slide.addText('团队介绍', {
    x: 0.5, y: 0.35, w: 12.33, h: 0.55,
    fontSize: 30, bold: true, color: THEME.white, align: 'center',
  });

  // 团队成员
  const members = [
    { role: '项目负责人', name: '[姓名]', school: '计算机学院', highlight: '主要贡献', color: THEME.accent },
    { role: '技术负责人', name: '[姓名]', school: '软件工程', highlight: 'AI算法', color: THEME.secondary },
    { role: '产品经理', name: '[姓名]', school: '工商管理', highlight: '产品设计', color: '8B5CF6' },
    { role: '商务负责人', name: '[姓名]', school: '市场营销', highlight: '商业拓展', color: THEME.green },
  ];

  members.forEach((m, i) => {
    const x = 0.6 + i * 3.1;

    slide.addShape('rect', {
      x, y: 1.1, w: 2.9, h: 2.0,
      fill: { color: THEME.white, transparency: 92 },
      line: { color: m.color, width: 2 },
    });
    slide.addShape('ellipse', {
      x: x + 0.95, y: 1.2, w: 1.0, h: 1.0,
      fill: { color: m.color, transparency: 30 },
    });
    slide.addText(m.name, {
      x, y: 2.3, w: 2.9, h: 0.35,
      fontSize: 14, bold: true, color: THEME.white, align: 'center',
    });
    slide.addText(m.role, {
      x, y: 2.65, w: 2.9, h: 0.25,
      fontSize: 11, color: m.color, align: 'center',
    });
    slide.addText(m.school, {
      x, y: 2.9, w: 2.9, h: 0.2,
      fontSize: 10, color: 'AAAAAA', align: 'center',
    });
  });

  // 指导老师
  slide.addText('指导老师：[姓名] [职称]', {
    x: 0.5, y: 3.3, w: 12.33, h: 0.35,
    fontSize: 13, color: THEME.secondary, align: 'center',
  });

  // 分隔线
  slide.addShape('rect', {
    x: 3, y: 3.8, w: 7.33, h: 0.03,
    fill: { color: THEME.accent },
  });

  // 联系方式
  slide.addText('合作联系', {
    x: 0.5, y: 4.0, w: 12.33, h: 0.35,
    fontSize: 14, bold: true, color: THEME.white, align: 'center',
  });
  slide.addText('📧 cityvision@edu.cn  |  🌐 www.cityvision.cn  |  📱 400-XXX-XXXX', {
    x: 0.5, y: 4.4, w: 12.33, h: 0.3,
    fontSize: 12, color: THEME.secondary, align: 'center',
  });

  // 致谢金句
  slide.addText('让每一次出行，都更安全', {
    x: 0.5, y: 4.9, w: 12.33, h: 0.45,
    fontSize: 28, bold: true, color: THEME.accent, align: 'center',
  });
  slide.addText('城市智眼 CityVision', {
    x: 0.5, y: 5.35, w: 12.33, h: 0.25,
    fontSize: 12, color: '8899AA', align: 'center',
  });

  addPageNumber(slide, 18, 18);
}

// ============================================================
// 生成所有页面
// ============================================================
slide1_cover();
slide2_pain_points();
slide3_existing();
slide4_solution();
slide5_demo();
slide6_innovations();
slide7_agent();
slide8_predictive();
slide9_coordination();
slide10_architecture();
slide11_agent_deep();
slide12_digital_twin();
slide13_evolution();
slide14_business();
slide15_competition();
slide16_social();
slide17_roadmap();
slide18_team();

// ============================================================
// 保存文件
// ============================================================
const outputPath = path.join(__dirname, '城市智眼_CityVision_国赛答辩.pptx');
pptx.writeFile({ fileName: outputPath })
  .then(() => {
    console.log(`✅ PPT已生成: ${outputPath}`);
    console.log('共 18 页幻灯片');
  })
  .catch(err => {
    console.error('❌ 生成失败:', err);
  });
