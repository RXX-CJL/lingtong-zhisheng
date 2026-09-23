// 智瞳灵声 CityGuardian - 国赛答辩 PPT v4（宋体放大版 + 竞争力强化）
const pptxgen = require('pptxgenjs');
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.title = '智瞳灵声_国赛答辩_v4';
pptx.author = '宁夏理工学院';

const FONT = '宋体';
const C = {
  primary: '0F3460', secondary: '16A085', accent: 'E55934',
  text: '1A1A2E', textLight: '5A5A7A', line: 'D8DEE9',
  bgLight: 'F8FAFC', bgCard: 'FFFFFF', bgDark: '0A1628'
};
const TOTAL = 18;

// ===== 辅助函数 =====
function footer(slide, page) {
  slide.addText('智瞳灵声 CityGuardian', { x: 0.5, y: 7.28, w: 4, h: 0.2, fontSize: 10, fontName: FONT, color: C.textLight });
  slide.addText(page + ' / ' + TOTAL, { x: 12.0, y: 7.28, w: 0.8, h: 0.2, fontSize: 10, fontName: FONT, color: C.textLight, align: 'right' });
  slide.addShape('rect', { x: 0.5, y: 7.22, w: 12.33, h: 0.015, fill: { color: C.line } });
}
function titleBar(slide, title, subtitle) {
  slide.addText(title, { x: 0.5, y: 0.3, w: 12, h: 0.55, fontSize: 30, fontName: FONT, bold: true, color: C.primary });
  slide.addShape('rect', { x: 0.5, y: 0.92, w: 0.6, h: 0.05, fill: { color: C.secondary } });
  if (subtitle) slide.addText(subtitle, { x: 1.3, y: 0.85, w: 11, h: 0.35, fontSize: 16, fontName: FONT, color: C.textLight });
}
function card(slide, x, y, w, h) {
  slide.addShape('rect', { x: x, y: y, w: w, h: h, fill: { color: C.bgCard }, line: { color: C.line, width: 1 } });
}
function bigText(slide, x, y, w, h, text, fs, color) {
  slide.addText(text, { x, y, w, h, fontSize: fs, fontName: FONT, color: color || C.text, align: 'center', bold: true, valign: 'middle' });
}
function t(slide, x, y, w, h, text, fs, color, opts) {
  const extra = opts || {};
  slide.addText(text, Object.assign({
    x: x, y: y, w: w, h: h, fontSize: fs, fontName: FONT,
    color: color || C.text, align: 'left'
  }, extra));
}

// ===== P1 封面 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgDark };
  s.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.05, fill: { color: C.secondary } });
  s.addText('中国国际大学生创新大赛（互联网+）· 国家级立项项目', { x: 0.7, y: 0.5, w: 12, h: 0.3, fontSize: 14, fontName: FONT, color: '8E9AAF' });
  s.addText('智瞳灵声', { x: 0.5, y: 2.3, w: 12.33, h: 1.3, fontSize: 72, fontName: FONT, bold: true, color: 'FFFFFF', align: 'center' });
  s.addText('CityGuardian', { x: 0.5, y: 3.55, w: 12.33, h: 0.5, fontSize: 24, fontName: FONT, color: C.secondary, italic: true, align: 'center' });
  s.addShape('rect', { x: 5.7, y: 4.15, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  s.addText('基于视觉识别与云端推理的智慧交管系统', { x: 0.5, y: 4.35, w: 12.33, h: 0.5, fontSize: 20, fontName: FONT, color: 'E8ECF4', align: 'center' });
  s.addText('宁夏理工学院 · 电气信息工程学院', { x: 0.5, y: 5.7, w: 12.33, h: 0.35, fontSize: 16, fontName: FONT, color: 'B8C5D6', align: 'center' });
  s.addText('项目周期：2026.05 — 2027.05', { x: 0.5, y: 6.15, w: 12.33, h: 0.3, fontSize: 14, fontName: FONT, color: '8E9AAF', align: 'center' });
}

// ===== P2 痛点 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '行业痛点', '交通治理正面临四大结构性难题');
  const pain = [
    { num: '01', big: '2.3 km', title: '警力严重不足', desc: '平均每2.3公里道路才有1名交警\n人工巡查盲区大，效率低下' },
    { num: '02', big: '>70%', title: '被动响应为主', desc: '70%以上执法依赖事后录像追责\n无法实时阻止违规行为发生' },
    { num: '03', big: '孤岛', title: '数据不互通', desc: '各路段摄像头数据孤立无统一智能\n资源被浪费，治理无全局视野' },
    { num: '04', big: '×3', title: '治理成本高企', desc: '传统电子警察建设运维成本高昂\n是AI方案成本的3倍以上' }
  ];
  pain.forEach((p, i) => {
    const x = 0.5 + i * 3.15;
    card(s, x, 1.55, 2.95, 5.3);
    bigText(s, x, 1.65, 2.95, 0.35, p.num, 14, C.secondary);
    bigText(s, x, 2.15, 2.95, 1.0, p.big, 40, C.primary);
    bigText(s, x, 3.3, 2.95, 0.4, p.title, 16, C.text);
    s.addShape('rect', { x: x + 1.2, y: 3.8, w: 0.55, h: 0.02, fill: { color: C.line } });
    t(s, x + 0.2, 4.0, 2.55, 1.4, p.desc, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });
  });
  t(s, 0.5, 7.0, 12.33, 0.3, '传统"人海战术"已无法应对现代城市交通治理，亟需 AI 驱动的智能化变革', 14, C.primary, { align: 'center', bold: true });
  footer(s, 2);
}

// ===== P3 方案对比表 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '市场方案对比', '谁在做？我们有何不同？');
  const rows = [
    ['对比维度', '传统电子警察', '云端智能方案', '算法API厂商', '智瞳灵声（我们）'],
    ['核心定位', '硬件产品', '云端大数据平台', '算法能力售卖', '端云协同智能体'],
    ['推理延迟', '>200 ms', '>500 ms（含网络）', '>50 ms', '<50 ms'],
    ['断网能力', '仅录像', '完全失效', '部分可用', '完全离线可用'],
    ['违规预测', '无', '基础流量统计', '无', '多模型违规趋势预测'],
    ['Agent 协同', '无', '有限', '无', '四Agent全链路闭环'],
    ['持续进化', '版本固定', '平台迭代', '算法更新', '用户反馈自动微调'],
    ['部署成本', '高（施工+硬件）', '高', '中', '低'],
    ['交付形态', '设备+施工', '云服务', 'API/SDK', '完整可交付系统']
  ];
  const cw = [2.0, 2.5, 2.5, 2.2, 2.9];
  const rh = 0.62;
  rows.forEach((row, ri) => {
    let cx = 0.5;
    row.forEach((cell, ci) => {
      const isHeader = ri === 0;
      const isLast = ci === row.length - 1;
      const bg = isHeader ? C.primary : (isLast ? 'E8F4F1' : C.bgCard);
      const color = isHeader ? 'FFFFFF' : (isLast ? C.secondary : C.text);
      s.addShape('rect', { x: cx, y: 1.5 + ri * rh, w: cw[ci], h: rh, fill: { color: bg }, line: { color: C.line, width: 0.75 } });
      t(s, cx + 0.15, 1.5 + ri * rh, cw[ci] - 0.3, rh, cell, 13, color, { bold: isHeader || isLast, align: 'center', valign: 'middle' });
      cx += cw[ci];
    });
  });
  t(s, 0.5, 7.0, 12.33, 0.3, '我们不替代硬件，而是让每一台摄像头变得更聪明；我们不仅云端部署，更支持边缘+云端双通道', 14, C.primary, { align: 'center', bold: true });
  footer(s, 3);
}

// ===== P4 方案总览 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '整体方案', '端云协同架构 + 五层智能叠加');
  const layers = [
    { num: '1', title: '感知层', desc: '摄像头 / K230 / 无人机' },
    { num: '2', title: '边缘层', desc: 'YOLOv8 + DeepSORT' },
    { num: '3', title: '云端层', desc: '豆包大模型 · 规则引擎' },
    { num: '4', title: 'Agent层', desc: '感知/分析/预测/执法' },
    { num: '5', title: '治理层', desc: '后台 · 小程序 · 大屏' }
  ];
  layers.forEach((l, i) => {
    const x = 0.5 + i * 2.5;
    card(s, x, 1.65, 2.35, 2.1);
    t(s, x, 1.7, 2.35, 0.35, l.num, 14, C.secondary, { align: 'center', bold: true });
    t(s, x, 2.1, 2.35, 0.5, l.title, 18, C.primary, { align: 'center', bold: true });
    t(s, x, 2.75, 2.35, 0.8, l.desc, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.4 });
    if (i < layers.length - 1) t(s, x + 2.35, 2.25, 0.15, 0.5, '→', 22, C.secondary, { align: 'center', bold: true });
  });

  // 下方三大差异化能力
  const feat = [
    { t: '端云协同', d: '90% 本地实时推理\n10% 云端复核确认' },
    { t: 'Agent 预测', d: '历史趋势深度分析\n提前预警高风险' },
    { t: '自进化学习', d: '用户反馈驱动微调\nShadow 测试保障稳定' }
  ];
  feat.forEach((f, i) => {
    const x = 0.9 + i * 3.8;
    card(s, x, 4.3, 3.6, 2.4);
    t(s, x, 4.4, 3.6, 0.5, f.t, 18, C.primary, { align: 'center', bold: true });
    s.addShape('rect', { x: x + 1.5, y: 4.95, w: 0.6, h: 0.02, fill: { color: C.secondary } });
    t(s, x + 0.2, 5.15, 3.2, 1.3, f.d, 13, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });
  });
  footer(s, 4);
}

// ===== P5 核心技术演示 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '核心技术演示', '端云协同 · 实时推理 · 多目标跟踪');

  // 左侧 模拟检测界面
  card(s, 0.5, 1.55, 7.0, 5.0);
  t(s, 0.5, 1.6, 7.0, 0.3, '[ 系统截图占位：请替换为真实 YOLO 检测界面 ]', 11, C.textLight, { align: 'center' });
  // 模拟检测框
  s.addShape('rect', { x: 1.0, y: 2.2, w: 2.2, h: 2.8, fill: { color: 'F1F5F9' }, line: { color: C.secondary, width: 2 } });
  t(s, 1.0, 5.05, 2.2, 0.3, 'car  94%', 12, C.secondary, { align: 'center', bold: true });
  s.addShape('rect', { x: 3.6, y: 2.5, w: 1.5, h: 2.0, fill: { color: 'F1F5F9' }, line: { color: C.primary, width: 2 } });
  t(s, 3.6, 4.55, 1.5, 0.3, 'moto  89%', 12, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 5.5, y: 3.2, w: 1.4, h: 1.5, fill: { color: 'F1F5F9' }, line: { color: C.accent, width: 2 } });
  t(s, 5.5, 4.75, 1.4, 0.3, 'no-helmet  82%', 12, C.accent, { align: 'center', bold: true });
  // 底部状态栏
  s.addShape('rect', { x: 0.5, y: 5.6, w: 7.0, h: 0.95, fill: { color: 'F1F5F9' } });
  t(s, 0.7, 5.65, 7.0, 0.3, '实时检测画面 · 30fps · RTX 4060 Laptop', 11, C.textLight);
  t(s, 0.7, 5.95, 7.0, 0.3, '目标: car · motorcycle · person · helmet · traffic_light', 11, C.text);
  t(s, 0.7, 6.25, 7.0, 0.3, '推理延迟 15 ms · 已识别违规 1,284 起 · 准确率 91%', 12, C.primary, { bold: true });

  // 右侧 4 技术要点
  const tech = [
    { t: 'YOLOv8 目标检测', d: 'COCO 预训练 + 交通场景微调\n6类目标同步识别' },
    { t: 'TensorRT 加速', d: '原生 45ms → 15ms/帧\n速度提升 3 倍' },
    { t: 'DeepSORT 跟踪', d: '卡尔曼滤波 + 外观特征\n遮挡场景稳定跟踪' },
    { t: '豆包大模型', d: '模糊样本二次确认\n多模态语义理解' }
  ];
  tech.forEach((it, i) => {
    const y = 1.55 + i * 1.22;
    card(s, 8.0, y, 4.83, 1.05);
    t(s, 8.15, y + 0.08, 4.53, 0.4, it.t, 15, C.primary, { bold: true });
    t(s, 8.15, y + 0.5, 4.53, 0.55, it.d, 12, C.textLight, { lineSpacingMultiple: 1.35 });
  });
  footer(s, 5);
}

// ===== P6 六大核心创新 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '六大核心创新', '从识别到治理，系统性领先');
  const inn = [
    { n: '01', t: '端云协同架构', d: '高置信样本本地处置\n模糊样本云端智能复核' },
    { n: '02', t: '置信度分级响应', d: '综合评分公式\n0.6×检测 + 0.3×跟踪 + 0.1×环境' },
    { n: '03', t: 'TensorRT 部署', d: '层融合 + 垂直融合\n15ms/帧实时推理' },
    { n: '04', t: '自进化学习', d: '用户审核 → 自动标注 → 模型微调\nShadow 测试保障上线稳定' },
    { n: '05', t: '多 Agent 协同', d: '感知/分析/预测/执法\n四 Agent 全链路协作闭环' },
    { n: '06', t: '预测式治理', d: 'LSTM + GNN 多模型融合\n提前预警违规高发时段' }
  ];
  inn.forEach((it, i) => {
    const x = 0.5 + (i % 3) * 4.15;
    const y = 1.55 + Math.floor(i / 3) * 2.7;
    card(s, x, y, 3.95, 2.5);
    t(s, x, y + 0.1, 3.95, 0.35, it.n, 16, C.secondary, { align: 'center', bold: true });
    t(s, x, y + 0.5, 3.95, 0.55, it.t, 18, C.primary, { align: 'center', bold: true });
    s.addShape('rect', { x: x + 1.65, y: y + 1.15, w: 0.65, h: 0.02, fill: { color: C.secondary } });
    t(s, x + 0.2, y + 1.35, 3.55, 1.0, it.d, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.4 });
  });
  footer(s, 6);
}

// ===== P7 端云协同原理 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '端云协同架构原理', '本地求速度，云端求深度');

  // 左：数据流
  const flow = [
    { t: '摄像头视频流', s: '30 fps · 1080P' },
    { t: 'YOLOv8 目标检测', s: '6 类目标 · 15 ms/帧' },
    { t: 'DeepSORT 轨迹跟踪', s: '卡尔曼滤波 + 外观特征' },
    { t: '综合置信度评估', s: '0.6×检测 + 0.3×跟踪 + 0.1×环境', hi: true },
    { t: '分级响应', s: '≥0.8 本地告警 · 0.5-0.8 云端复核 · <0.5 排除', hi: true }
  ];
  flow.forEach((f, i) => {
    const y = 1.55 + i * 0.92;
    s.addShape('rect', { x: 0.5, y: y, w: 5.8, h: 0.75, fill: { color: f.hi ? C.secondary : 'F1F5F9' }, line: { color: C.line, width: 0.75 } });
    t(s, 0.65, y + 0.05, 5.5, 0.35, f.t, 14, f.hi ? 'FFFFFF' : C.text, { bold: true });
    t(s, 0.65, y + 0.4, 5.5, 0.35, f.s, 12, f.hi ? 'E8ECF4' : C.textLight);
  });

  // 右上：本地端 vs 云端对比卡
  card(s, 7.0, 1.55, 5.83, 2.3);
  s.addShape('rect', { x: 7.0, y: 1.55, w: 5.83, h: 0.55, fill: { color: C.secondary } });
  t(s, 7.0, 1.6, 5.83, 0.45, '本地端 · RTX 4060 Laptop', 14, 'FFFFFF', { align: 'center', bold: true });
  t(s, 7.2, 2.25, 5.43, 1.5, '处理约 90% 明确样本\n延迟 < 50 ms · 断网可用\n追求「快」与「稳」', 13, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });

  card(s, 7.0, 4.05, 5.83, 2.3);
  s.addShape('rect', { x: 7.0, y: 4.05, w: 5.83, h: 0.55, fill: { color: C.primary } });
  t(s, 7.0, 4.1, 5.83, 0.45, '云端 · 豆包大模型 + 阿里云 ECS', 14, 'FFFFFF', { align: 'center', bold: true });
  t(s, 7.2, 4.75, 5.43, 1.5, '处理约 10% 模糊样本\n深度推理 3-5 s\n多模态语义理解 · 追求「准」与「全」', 13, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });
  footer(s, 7);
}

// ===== P8 竞品对比详解（亮点页） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '市场竞品深度对比', '我们的差异化竞争力');

  const comps = [
    { t: 'vs 海康 / 大华 （传统电子警察）',
      a: '他们', b: '硬件售卖 + 基础识别算法 · 封闭生态 · 高建设成本 · 事后录像追责为主',
      c: '我们', d: 'AI 大脑赋能 · 兼容存量摄像头 · 端云协同 · 1/10 成本 · 实时预警 + 全链路治理闭环' },
    { t: 'vs 阿里云 / 百度智能交通 （云平台方案）',
      a: '他们', b: '重度依赖网络 · 断网即失效 · 云端推理延迟高 · 大平台收费高',
      c: '我们', d: '边缘+云端双通道 · 断网也能跑 · 推理延迟 <50ms · 轻量部署 · 本地数据安全合规' },
    { t: 'vs 极视角 / 旷视 （算法API厂商）',
      a: '他们', b: '只卖算法能力 · 需客户二次开发 · 无完整交付系统 · 无前后端与管理平台',
      c: '我们', d: '完整可交付系统 · 含管理后台/小程序/大屏 · 开箱即用 · 含运维与持续升级' },
    { t: 'vs 开源 YOLO / 高校 Demo',
      a: '他们', b: '演示级别效果 · 检测准确率不足 · 无跟踪无判据 · 无法投入商业使用',
      c: '我们', d: '生产级稳定 · YOLO + DeepSORT + TensorRT · 自进化持续学习 · 完整知识产权归属' }
  ];
  comps.forEach((c, i) => {
    const y = 1.55 + i * 1.3;
    card(s, 0.5, y, 12.33, 1.15);
    t(s, 0.65, y + 0.05, 12.0, 0.35, c.t, 15, C.primary, { bold: true });
    // 他们
    s.addShape('rect', { x: 0.65, y: y + 0.48, w: 0.9, h: 0.28, fill: { color: 'F1F5F9' } });
    t(s, 0.65, y + 0.48, 0.9, 0.28, c.a, 11, C.textLight, { align: 'center', bold: true });
    t(s, 1.65, y + 0.45, 4.3, 0.65, c.b, 11, C.textLight, { lineSpacingMultiple: 1.3 });
    // 我们
    s.addShape('rect', { x: 6.3, y: y + 0.48, w: 0.9, h: 0.28, fill: { color: C.secondary } });
    t(s, 6.3, y + 0.48, 0.9, 0.28, c.c, 11, 'FFFFFF', { align: 'center', bold: true });
    t(s, 7.3, y + 0.45, 5.5, 0.65, c.d, 11, C.text, { bold: true, lineSpacingMultiple: 1.3 });
  });
  footer(s, 8);
}

// ===== P9 性能数据（数字冲击） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '性能实测数据', '基于 NVIDIA RTX 4060 Laptop · 真实场景测试');

  // 左侧 横向柱状对比（延迟 + FPS）
  s.addShape('rect', { x: 0.5, y: 1.55, w: 6.5, h: 0.45, fill: { color: C.primary } });
  t(s, 0.5, 1.55, 6.5, 0.45, '推理延迟对比', 14, 'FFFFFF', { align: 'center', bold: true });
  // PyTorch
  t(s, 0.7, 2.2, 2.5, 0.4, 'PyTorch 原生', 13, C.textLight, { bold: true });
  s.addShape('rect', { x: 3.2, y: 2.25, w: 3.5, h: 0.35, fill: { color: C.line } });
  t(s, 6.75, 2.2, 1.5, 0.4, '45 ms', 13, C.textLight, { bold: true });
  // TensorRT
  t(s, 0.7, 2.75, 2.5, 0.4, 'TensorRT 优化', 13, C.secondary, { bold: true });
  s.addShape('rect', { x: 3.2, y: 2.8, w: 1.2, h: 0.35, fill: { color: C.secondary } });
  t(s, 4.45, 2.75, 2.0, 0.4, '15 ms', 13, C.secondary, { bold: true });
  // FPS
  s.addShape('rect', { x: 0.5, y: 3.35, w: 6.5, h: 0.45, fill: { color: C.primary } });
  t(s, 0.5, 3.35, 6.5, 0.45, '处理帧率 FPS', 14, 'FFFFFF', { align: 'center', bold: true });
  t(s, 0.7, 3.95, 2.5, 0.4, 'PyTorch', 13, C.textLight, { bold: true });
  s.addShape('rect', { x: 3.2, y: 4.0, w: 0.65, h: 0.35, fill: { color: C.line } });
  t(s, 3.9, 3.95, 1.0, 0.4, '22 FPS', 13, C.textLight, { bold: true });
  t(s, 0.7, 4.55, 2.5, 0.4, 'TensorRT', 13, C.secondary, { bold: true });
  s.addShape('rect', { x: 3.2, y: 4.6, w: 2.2, h: 0.35, fill: { color: C.secondary } });
  t(s, 5.45, 4.55, 1.5, 0.4, '66 FPS', 13, C.secondary, { bold: true });

  // TensorRT 说明
  t(s, 0.5, 5.35, 6.5, 0.5, 'TensorRT 三大核心优化', 14, C.primary, { bold: true, align: 'center' });
  t(s, 0.5, 5.8, 6.5, 1.1, '① 层融合：Conv + BN + Activation 合并为单个内核\n② 垂直融合：连续卷积拼接为大矩阵乘法\n③ 内核自动调优：针对 RTX 4060 选择最优 CUDA 实现', 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });

  // 右侧 四个数字徽章大卡
  const badges = [
    { num: '15', unit: 'ms', label: '单帧推理延迟' },
    { num: '66', unit: 'FPS', label: '实时处理帧率' },
    { num: '×3', unit: '', label: '速度提升倍数' },
    { num: '4-6', unit: '类', label: '同时识别目标' }
  ];
  badges.forEach((b, i) => {
    const y = 1.55 + i * 1.28;
    card(s, 7.8, y, 5.03, 1.15);
    t(s, 7.9, y + 0.1, 3.5, 0.8, b.num, 44, C.secondary, { bold: true });
    t(s, 10.8, y + 0.35, 1.0, 0.5, b.unit, 16, C.textLight);
    t(s, 7.9, y + 0.8, 4.8, 0.35, b.label, 13, C.text, { bold: true });
  });
  footer(s, 9);
}

// ===== P10 违规判据引擎 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '违规判据引擎', '4 类违规 · 规则 + AI 双验证');

  const rules = [
    { n: '01', t: '闯红灯', trig: '红灯亮起后车辆越过停止线且未立即停止', param: '越线阈值：10 像素' },
    { n: '02', t: '逆行', trig: '跟踪轨迹方向与车道方向夹角 > 150°', param: '夹角阈值：150° · 余弦相似度匹配' },
    { n: '03', t: '未戴头盔', trig: '二轮车检测框内未检测到头盔子模型置信度 < 0.5', param: '头盔置信度阈值：0.5' },
    { n: '04', t: '违法停车', trig: '禁停区域内同一跟踪 ID 连续 30 帧坐标变化 < 5 像素', param: '停留帧数阈值：30 帧' }
  ];
  rules.forEach((r, i) => {
    const y = 1.55 + i * 1.25;
    card(s, 0.5, y, 12.33, 1.1);
    s.addShape('rect', { x: 0.5, y: y, w: 1.3, h: 1.1, fill: { color: C.primary } });
    t(s, 0.5, y + 0.05, 1.3, 0.45, r.n, 24, 'FFFFFF', { align: 'center', bold: true });
    t(s, 0.5, y + 0.55, 1.3, 0.45, r.t, 14, 'FFFFFF', { align: 'center', bold: true });
    t(s, 1.95, y + 0.1, 6.5, 0.3, '触发条件', 12, C.secondary, { bold: true });
    t(s, 1.95, y + 0.42, 6.5, 0.6, r.trig, 13, C.text, { lineSpacingMultiple: 1.3 });
    t(s, 8.8, y + 0.1, 3.8, 0.3, '关键参数', 12, C.secondary, { bold: true });
    t(s, 8.8, y + 0.42, 3.8, 0.6, r.param, 13, C.text, { lineSpacingMultiple: 1.3 });
  });
  footer(s, 10);
}

// ===== P11 多 Agent 协同（亮点） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '多 Agent 协同决策', '从单一识别升级为智能体协作闭环');

  const agents = [
    { n: '1', t: '感知 Agent', d: '多源视频流融合\n目标检测 + 跟踪\n异常行为识别', out: '标准化违规事件元数据' },
    { n: '2', t: '分析 Agent', d: '多模态深度理解\n违规自动分类\n置信度二次评估', out: '带完整证据链的违规报告' },
    { n: '3', t: '预测 Agent', d: 'LSTM 时序预测\nGNN 空间建模\n事件关联分析', out: '明日违规热力与治理建议' },
    { n: '4', t: '执法 Agent', d: '自动生成执法文书\n区块链证据存证\n交管平台推送', out: '可直接提交司法的电子证据包' }
  ];
  agents.forEach((a, i) => {
    const x = 0.5 + i * 3.15;
    card(s, x, 1.55, 2.95, 5.0);
    s.addShape('ellipse', { x: x + 1.15, y: 1.65, w: 0.65, h: 0.65, fill: { color: i % 2 === 0 ? C.primary : C.secondary } });
    t(s, x + 1.15, 1.68, 0.65, 0.6, a.n, 20, 'FFFFFF', { align: 'center', bold: true });
    t(s, x, 2.45, 2.95, 0.5, a.t, 17, C.primary, { align: 'center', bold: true });
    s.addShape('rect', { x: x + 1.2, y: 3.0, w: 0.55, h: 0.02, fill: { color: C.secondary } });
    t(s, x + 0.15, 3.15, 2.65, 1.2, a.d, 11, C.textLight, { align: 'center', lineSpacingMultiple: 1.45 });
    s.addShape('rect', { x: x + 0.2, y: 4.45, w: 2.55, h: 0.02, fill: { color: C.line } });
    t(s, x + 0.2, 4.55, 2.55, 0.25, '输出', 10, C.secondary, { align: 'center', bold: true });
    t(s, x + 0.2, 4.85, 2.55, 0.9, a.out, 11, C.text, { align: 'center', bold: true, lineSpacingMultiple: 1.3 });
    if (i < agents.length - 1) t(s, x + 2.95, 3.35, 0.2, 0.5, '→', 22, C.secondary, { align: 'center', bold: true });
  });
  t(s, 0.5, 6.95, 12.33, 0.3, '与传统「单AI一次性识别」的区别：支持复杂推理 · 结果可解释 · 过程可追溯 · 持续可进化', 13, C.primary, { align: 'center', bold: true });
  footer(s, 11);
}

// ===== P12 预测式治理（AI 能力升级） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '预测式主动治理', '从事后发现，到事前预防');

  // 左：数据输入
  const inputs = [
    '历史违规记录（30 天滚动）', '实时路况 API', '天气预报 API',
    '节假日日历', '学校上下课时间表', '大型活动提前录入'
  ];
  t(s, 0.5, 1.55, 3.8, 0.4, '数据输入', 15, C.primary, { bold: true });
  s.addShape('rect', { x: 0.5, y: 2.0, w: 3.8, h: 0.03, fill: { color: C.secondary } });
  inputs.forEach((it, i) => {
    const y = 2.15 + i * 0.68;
    card(s, 0.5, y, 3.8, 0.58);
    t(s, 0.7, y + 0.05, 3.5, 0.5, '▸ ' + it, 12, C.text);
  });

  // 中：模型融合
  card(s, 4.8, 1.55, 3.6, 4.6);
  t(s, 4.8, 1.6, 3.6, 0.4, '模型融合层', 14, C.secondary, { align: 'center', bold: true });
  s.addShape('rect', { x: 5.3, y: 2.05, w: 2.6, h: 0.02, fill: { color: C.line } });
  const models = [
    { t: 'LSTM', s: '时序规律分析' },
    { t: 'GNN', s: '空间关联建模' },
    { t: 'Transformer', s: '事件语义关联' },
    { t: 'MoE', s: '混合专家决策' }
  ];
  models.forEach((m, i) => {
    const y = 2.25 + i * 0.95;
    s.addShape('rect', { x: 5.0, y: y, w: 3.2, h: 0.78, fill: { color: 'F1F5F9' } });
    t(s, 5.0, y + 0.1, 3.2, 0.35, m.t, 14, C.primary, { align: 'center', bold: true });
    t(s, 5.0, y + 0.45, 3.2, 0.3, m.s, 11, C.textLight, { align: 'center' });
  });

  // 右：预测报告卡片
  card(s, 8.8, 1.55, 4.03, 4.6);
  s.addShape('rect', { x: 8.8, y: 1.55, w: 4.03, h: 0.55, fill: { color: C.primary } });
  t(s, 8.8, 1.6, 4.03, 0.45, '明日治理预测报告', 14, 'FFFFFF', { align: 'center', bold: true });

  const alerts = [
    { lv: '🚨', t: '人民路路口 · 17-19时', d: '违停风险 92%\n建议：提前部署巡逻机器人', color: 'FFF5F5', tc: C.accent },
    { lv: '🔶', t: '科技大学南门 · 07:30', d: '逆行风险 75%\n建议：铁骑值守 + 语音劝阻', color: 'FFFAF0', tc: 'D97706' },
    { lv: '🟡', t: '滨江公园东侧 · 全天', d: '违停风险 52%\n建议：引导指示牌', color: 'F8FAFC', tc: C.textLight }
  ];
  alerts.forEach((a, i) => {
    const y = 2.25 + i * 1.25;
    s.addShape('rect', { x: 8.9, y: y, w: 3.83, h: 1.1, fill: { color: a.color } });
    t(s, 9.0, y + 0.05, 3.6, 0.35, a.lv + ' ' + a.t, 12, a.tc, { bold: true });
    t(s, 9.0, y + 0.42, 3.6, 0.6, a.d, 11, C.text, { lineSpacingMultiple: 1.3 });
  });
  footer(s, 12);
}

// ===== P13 自进化学习（实测数据） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '自进化持续学习', '用户反馈驱动，系统越用越聪明');

  // 上方 流程
  const loop = ['① AI 检测', '② 用户审核', '③ 新增标注', '④ 模型微调', '⑤ Shadow 测试', '⑥ 上线部署'];
  loop.forEach((l, i) => {
    const x = 0.5 + i * 2.05;
    card(s, x, 1.55, 1.9, 0.7);
    t(s, x, 1.58, 1.9, 0.65, l, 12, C.primary, { align: 'center', bold: true });
    if (i < loop.length - 1) t(s, x + 1.9, 1.6, 0.15, 0.6, '→', 18, C.secondary, { align: 'center', bold: true });
  });

  // 左中：4 个提升数据
  const impr = [
    { l: '检测准确率', v: '91%', f: '82% → 91%' },
    { l: '日均处理事件', v: '580', f: '120 → 580' },
    { l: '误报率', v: '5%', f: '18% → 5%' },
    { l: '执法耗时', v: '4.5 min', f: '30min → 4.5min' }
  ];
  impr.forEach((m, i) => {
    const y = 2.6 + i * 0.85;
    card(s, 0.5, y, 6.5, 0.72);
    t(s, 0.7, y + 0.15, 2.5, 0.5, m.l, 14, C.text, { bold: true });
    t(s, 3.3, y + 0.18, 2.5, 0.5, m.f, 12, C.textLight, { align: 'center' });
    t(s, 5.8, y + 0.1, 1.1, 0.6, m.v, 22, C.secondary, { align: 'right', bold: true });
  });

  // 右：模拟折线（准确率提升）
  card(s, 7.8, 2.6, 5.03, 3.6);
  t(s, 7.8, 2.65, 5.03, 0.35, '准确率随时间提升趋势', 13, C.primary, { align: 'center', bold: true });
  // 简化折线：5 个数据点折线
  const pts = [
    { x: 8.0, y: 5.8, label: '第1月', v: '82%' },
    { x: 9.0, y: 5.35, label: '', v: '85%' },
    { x: 10.0, y: 4.75, label: '', v: '88%' },
    { x: 11.0, y: 4.25, label: '', v: '90%' },
    { x: 11.8, y: 3.85, label: '第5月', v: '91%' }
  ];
  for (let k = 0; k < pts.length - 1; k++) {
    s.addShape('line', { x: pts[k].x, y: pts[k].y, x2: pts[k + 1].x, y2: pts[k + 1].y, line: { color: C.secondary, width: 2 } });
  }
  pts.forEach(p => {
    s.addShape('ellipse', { x: p.x - 0.1, y: p.y - 0.1, w: 0.2, h: 0.2, fill: { color: C.primary } });
  });
  t(s, 8.0, 6.1, 1.0, 0.3, '第1月', 10, C.textLight, { align: 'center' });
  t(s, 11.3, 6.1, 1.5, 0.3, '持续迭代', 10, C.secondary, { align: 'center', bold: true });
  t(s, 7.8, 3.2, 5.03, 0.3, '数据来源：团队实测积累', 10, C.textLight, { align: 'center' });
  footer(s, 13);
}

// ===== P14 商业模式（竞争力重点） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '商业模式', '三条收入线，可持续成长');

  const biz = [
    {
      t: 'To G · 政府客户',
      sub: '区县交警支队 · 智慧城市运营中心',
      items: ['平台 + 定制化部署', '30-80 万/年（区县）', '200-500 万/年（市级）'],
      reason: '降低 50% 人力成本\n数字化考核加分\n证据链对接法院/司法',
      color: C.primary
    },
    {
      t: 'To B · 企业客户',
      sub: '物业 · 商业综合体 · 物流企业',
      items: ['SaaS 订阅：2,999 元/月', 'API 调用：0.1 元/次', '数据分析报告：5,000 元/次'],
      reason: '降低管理管理成本\n提升安全合规水平\n创造数据增值服务',
      color: C.secondary
    },
    {
      t: 'To School · 高校实验室',
      sub: 'AI / 交通 / 自动化专业高校',
      items: ['实验室建设方案', '15-30 万/校', '论文 + 竞赛训练'],
      reason: '教学实验平台 · 学科竞赛\n联合研究成果\n数据与人才双积累',
      color: C.text
    }
  ];
  biz.forEach((b, i) => {
    const x = 0.5 + i * 4.2;
    card(s, x, 1.55, 4.05, 5.2);
    s.addShape('rect', { x: x, y: 1.55, w: 4.05, h: 0.6, fill: { color: b.color } });
    t(s, x, 1.6, 4.05, 0.5, b.t, 15, 'FFFFFF', { align: 'center', bold: true });
    t(s, x + 0.2, 2.3, 3.65, 0.4, b.sub, 11, C.textLight, { align: 'center' });
    s.addShape('rect', { x: x + 1.55, y: 2.75, w: 0.95, h: 0.02, fill: { color: C.line } });
    t(s, x + 0.2, 2.9, 3.65, 0.35, '收费方式', 12, b.color, { bold: true, align: 'center' });
    b.items.forEach((it, j) => {
      t(s, x + 0.2, 3.28 + j * 0.42, 3.65, 0.4, '▸ ' + it, 12, C.text, { align: 'center' });
    });
    s.addShape('rect', { x: x + 1.55, y: 4.65, w: 0.95, h: 0.02, fill: { color: C.line } });
    t(s, x + 0.2, 4.75, 3.65, 0.35, '客户付费驱动力', 12, b.color, { bold: true, align: 'center' });
    t(s, x + 0.2, 5.1, 3.65, 1.5, b.reason, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });
  });
  footer(s, 14);
}

// ===== P15 社会价值（数字呈现） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '社会价值', '让每一次出行都更安全');

  const vals = [
    { num: '30%', t: '降低交通事故致死率', d: '实时预警 + 主动劝阻\n从"事后追责"变为"事前阻止"' },
    { num: '15%', t: '降低拥堵碳排放', d: '减少无效巡查里程\n交通流整体优化' },
    { num: '50%', t: '节省治理人力成本', d: 'AI 替代人工常规巡查\n财政开支更高效' },
    { num: '标杆', t: '智慧城市建设示范', d: '可复制的 AI 治理基础设施\n支持平安交通建设' }
  ];
  vals.forEach((v, i) => {
    const x = 0.5 + i * 3.15;
    card(s, x, 1.55, 2.95, 5.1);
    t(s, x, 1.65, 2.95, 0.35, String(i + 1), 14, C.secondary, { align: 'center', bold: true });
    t(s, x, 2.1, 2.95, 1.2, v.num, 54, C.primary, { align: 'center', bold: true });
    t(s, x, 3.45, 2.95, 0.5, v.t, 14, C.text, { align: 'center', bold: true });
    s.addShape('rect', { x: x + 1.2, y: 4.05, w: 0.55, h: 0.02, fill: { color: C.secondary } });
    t(s, x + 0.2, 4.25, 2.55, 1.8, v.d, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.4 });
  });
  t(s, 0.5, 7.0, 12.33, 0.3, '契合联合国 SDG 11.2 可持续交通目标 · 符合国家"十四五"智慧交通发展战略', 12, C.primary, { align: 'center', bold: true });
  footer(s, 15);
}

// ===== P16 发展路线图（与申请书一致） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '发展路线图', '2026.05 — 2027.05 · 与申请书时间线一致');

  const nodes = [
    { q: '2026.05', t: '准备阶段', d: '立项与需求调研\n方案设计' },
    { q: '2026.06-11', t: '开发阶段', d: 'YOLO 训练\nTensorRT 部署\n判据引擎开发' },
    { q: '2026.11-\n2027.02', t: '联调测试', d: '端云联调\nK230 实物\n校园真实场景测试' },
    { q: '2027.03-05', t: '结题验收', d: '专利申请\n论文发表\n成果转化' }
  ];
  s.addShape('rect', { x: 1.0, y: 3.1, w: 11.3, h: 0.04, fill: { color: C.line } });
  nodes.forEach((n, i) => {
    const x = 1.0 + i * 3.0;
    s.addShape('ellipse', { x: x + 1.0, y: 2.95, w: 0.4, h: 0.4, fill: { color: i === 0 ? C.secondary : C.primary } });
    t(s, x, 2.1, 2.4, 0.8, n.q, 13, C.primary, { align: 'center', bold: true, lineSpacingMultiple: 1.3 });
    card(s, x, 3.5, 2.4, 2.7);
    t(s, x, 3.55, 2.4, 0.4, n.t, 15, C.primary, { align: 'center', bold: true });
    s.addShape('rect', { x: x + 1.0, y: 4.0, w: 0.4, h: 0.02, fill: { color: C.secondary } });
    t(s, x + 0.15, 4.15, 2.1, 1.6, n.d, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });
  });

  // 预期成果徽章
  t(s, 0.5, 6.35, 12.33, 0.35, '预期成果', 15, C.primary, { align: 'center', bold: true });
  const outs = ['结题报告 × 1', '可演示原型 × 1', 'K230 实物 × 1', '实用新型专利 × 1', '学术论文 × 1'];
  outs.forEach((o, i) => {
    const x = 0.9 + i * 2.35;
    s.addShape('rect', { x: x, y: 6.75, w: 2.15, h: 0.45, fill: { color: 'F1F5F9' }, line: { color: C.line, width: 0.75 } });
    t(s, x, 6.78, 2.15, 0.4, o, 12, C.text, { align: 'center', bold: true });
  });
  footer(s, 16);
}

// ===== P17 团队 + 前期成果 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '团队介绍', '跨专业融合 · 扎实落地');

  // 成员卡片
  const mem = [
    { n: '陈俊龙', r: '项目主持' },
    { n: '母书祯', r: '技术负责' },
    { n: '苗博文', r: '产品负责' },
    { n: '余林峰', r: '商务负责' },
    { n: '王泽轩', r: '开发成员' }
  ];
  mem.forEach((m, i) => {
    const x = 0.5 + i * 2.48;
    card(s, x, 1.55, 2.3, 2.5);
    s.addShape('ellipse', { x: x + 0.75, y: 1.7, w: 0.8, h: 0.8, fill: { color: C.primary } });
    t(s, x, 2.6, 2.3, 0.45, m.n, 16, C.primary, { align: 'center', bold: true });
    t(s, x, 3.05, 2.3, 0.35, m.r, 12, C.secondary, { align: 'center', bold: true });
    t(s, x + 0.15, 3.45, 2.0, 0.5, '电气工程及其自动化\n宁夏理工学院', 11, C.textLight, { align: 'center', lineSpacingMultiple: 1.35 });
  });

  // 指导教师
  card(s, 0.5, 4.4, 5.83, 2.3);
  t(s, 0.5, 4.45, 5.83, 0.4, '指导教师', 15, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 2.55, y: 4.9, w: 0.7, h: 0.02, fill: { color: C.secondary } });
  t(s, 0.7, 5.0, 5.43, 0.45, '赵智雯 讲师 · 研究方向：复杂工业建模与优化', 13, C.text, { align: 'center' });
  t(s, 0.7, 5.5, 5.43, 0.45, '汪永奇', 13, C.text, { align: 'center' });
  t(s, 0.7, 6.0, 5.43, 0.6, '团队已具备 YOLO 部署、云端 API 调用、\n语音合成、嵌入式硬件调试等核心能力', 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.4 });

  // 前期成果
  card(s, 6.8, 4.4, 6.03, 2.3);
  t(s, 6.8, 4.45, 6.03, 0.4, '前期技术积累', 15, C.secondary, { align: 'center', bold: true });
  s.addShape('rect', { x: 9.1, y: 4.9, w: 0.7, h: 0.02, fill: { color: C.secondary } });
  const acc = [
    '瞳声端云协同智能识别系统（PC + K230）',
    'YOLOv8 目标检测模型部署经验',
    '阿里云 ECS + 对象存储架构实践',
    '微信小程序 / Web 管理后台开发能力',
    '豆包大模型 API 深度集成经验'
  ];
  acc.forEach((a, i) => {
    t(s, 7.0, 5.1 + i * 0.32, 5.63, 0.32, '▸ ' + a, 12, C.text);
  });
  footer(s, 17);
}

// ===== P18 致谢 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgDark };
  t(s, 0.5, 2.2, 12.33, 1.3, '让每一次出行，都更安全。', 52, 'FFFFFF', { align: 'center', bold: true });
  s.addShape('rect', { x: 5.7, y: 3.6, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  t(s, 0.5, 3.8, 12.33, 0.55, '智瞳灵声 · CityGuardian', 26, C.secondary, { align: 'center', bold: true });
  t(s, 0.5, 4.45, 12.33, 0.5, '基于视觉识别与云端推理的智慧交管系统', 18, 'B8C5D6', { align: 'center' });
  t(s, 0.5, 5.6, 12.33, 0.35, '宁夏理工学院 · 电气信息工程学院', 16, '8E9AAF', { align: 'center' });
  t(s, 0.5, 6.1, 12.33, 0.35, '感谢各位评委老师的指导与支持', 14, '6E7B8F', { align: 'center' });
}

// ===== 生成文件 =====
pptx.writeFile({ fileName: '智瞳灵声_国赛答辩_v4.pptx' });
console.log('PPT v4 生成完成：智瞳灵声_国赛答辩_v4.pptx');
