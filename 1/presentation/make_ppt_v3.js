// 智瞳灵声 CityGuardian - 国赛答辩PPT v4 (宋体放大版 + 竞争力强化)
// 配色: 深蓝(#0F3460) + 青蓝(#16A085) + 灰白中性色
const pptxgen = require('pptxgenjs');
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.title = '智瞳灵声 · 国赛答辩 v4';
pptx.author = '宁夏理工学院';
const CN_FONT = '宋体';

const C = {
  primary: '0F3460', secondary: '16A085', accent: 'E55934',
  text: '1A1A2E', textLight: '5A5A7A', line: 'D8DEE9',
  bgLight: 'F8FAFC', bgCard: 'FFFFFF', bgDark: '0A1628'
};
// 字号放大版：正文 14-16，标题 18-28，大数字进一步加强
const FS = {
  micro: 11,    // 页脚/辅助
  small: 14,    // 次要正文
  body: 16,     // 标准正文
  sub: 18,      // 小标题
  title: 24,    // 主标题
  bigTitle: 32, // 大标题
  cover: 52,    // 封面主标题
  num: 40,      // 大数字
};
const TOTAL = 18;

function footer(slide, page) {
  slide.addText('智瞳灵声 CityGuardian', { x: 0.5, y: 7.28, w: 4, h: 0.2, fontSize: 9, color: C.textLight });
  slide.addText(page + ' / ' + TOTAL, { x: 12.0, y: 7.28, w: 0.8, h: 0.2, fontSize: 9, color: C.textLight, align: 'right' });
  slide.addShape('rect', { x: 0.5, y: 7.22, w: 12.33, h: 0.015, fill: { color: C.line } });
}
function titleBar(slide, title, subtitle) {
  slide.addText(title, { x: 0.5, y: 0.3, w: 12, h: 0.55, fontSize: 28, bold: true, color: C.primary });
  slide.addShape('rect', { x: 0.5, y: 0.9, w: 0.5, h: 0.04, fill: { color: C.secondary } });
  if (subtitle) slide.addText(subtitle, { x: 1.1, y: 0.82, w: 12, h: 0.35, fontSize: 13, color: C.textLight });
}
function card(slide, x, y, w, h) {
  slide.addShape('rect', { x: x, y: y, w: w, h: h, fill: { color: C.bgCard }, line: { color: C.line, width: 1 } });
}

// ===== P1 封面 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgDark };
  s.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.06, fill: { color: C.secondary } });
  s.addText('中国国际大学生创新大赛（互联网+）· 国家级立项', { x: 0.7, y: 0.4, w: 8, h: 0.3, fontSize: 10, color: '8E9AAF' });
  s.addText('智瞳灵声', { x: 0.7, y: 2.2, w: 12, h: 1.1, fontSize: 68, bold: true, color: 'FFFFFF' });
  s.addText('CityGuardian', { x: 0.75, y: 3.25, w: 12, h: 0.4, fontSize: 20, color: C.secondary, italic: true });
  s.addShape('rect', { x: 0.7, y: 3.8, w: 1.8, h: 0.03, fill: { color: C.secondary } });
  s.addText('基于视觉识别与云端推理的智慧交管系统', { x: 0.7, y: 4.0, w: 12, h: 0.45, fontSize: 20, color: 'E8ECF4' });
  s.addText('宁夏理工学院 · 电气信息工程学院', { x: 0.7, y: 5.6, w: 12, h: 0.3, fontSize: 13, color: '8E9AAF' });
  s.addText('项目周期：2026.05 — 2027.05', { x: 0.7, y: 5.95, w: 12, h: 0.25, fontSize: 11, color: '6E7B8F' });
}

// ===== P2 痛点 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '行业痛点', '交通治理正面临四个结构性难题');
  const pain = [
    { num: '01', big: '2.3 km', t: '警力严重不足', d: '平均每2.3公里道路\n才有1名交警，人工巡查盲区大' },
    { num: '02', big: '>70%', t: '被动响应为主', d: '70%以上执法依赖事后录像追责\n无法实时阻止违规行为' },
    { num: '03', big: '孤岛', t: '数据不互通', d: '各路段摄像头数据孤立\n无统一智能，资源被浪费' },
    { num: '04', big: '× 3', t: '治理成本高企', d: '传统电子警察建设与运维成本\n是AI方案的3倍以上' },
  ];
  pain.forEach((p, i) => {
    const x = 0.5 + i * 3.15;
    card(s, x, 1.45, 2.95, 5.4);
    s.addText(p.num, { x: x, y: 1.7, w: 2.95, h: 0.4, fontSize: 12, bold: true, color: C.secondary, align: 'center' });
    s.addText(p.big, { x: x, y: 2.2, w: 2.95, h: 0.9, fontSize: 36, bold: true, color: C.primary, align: 'center' });
    s.addText(p.t, { x: x, y: 3.15, w: 2.95, h: 0.4, fontSize: 14, bold: true, color: C.text, align: 'center' });
    s.addText(p.d, { x: x + 0.15, y: 3.75, w: 2.65, h: 2.5, fontSize: 11, color: C.textLight, align: 'center', lineSpacingMultiple: 1.5 });
  });
  s.addText('传统"人海战术"已无法应对现代城市交通治理，亟需 AI 驱动的智能化变革', { x: 0.5, y: 6.95, w: 12.33, h: 0.3, fontSize: 11, bold: true, color: C.primary, align: 'center' });
  footer(s, 2);
}

// ===== P3 现有方案对比 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '现有方案不足', '市场已有产品的真实局限');
  const rows = [
    ['对比维度', '传统电子警察', '云平台方案', '算法API', '智瞳灵声（我们）'],
    ['推理延迟', '>200 ms', '>500 ms', '>50 ms', '<50 ms'],
    ['断网能力', '仅录像', '完全失效', '有限', '离线可用'],
    ['违规预测', '无', '流量预测', '无', '违规趋势预测'],
    ['Agent协同', '无', '有限', '无', '四Agent闭环'],
    ['自进化', '版本固定', '平台迭代', '算法更新', '用户反馈驱动'],
    ['部署成本', '高（施工+硬件）', '高', '中', '低'],
  ];
  const colW = [2.1, 2.6, 2.6, 2.6, 2.8];
  const rowH = 0.72;
  rows.forEach((row, ri) => {
    let cx = 0.5;
    row.forEach((cell, ci) => {
      const isHeader = ri === 0;
      const isLastCol = ci === row.length - 1;
      const bg = isHeader ? C.primary : (isLastCol ? 'E8F4F1' : C.bgCard);
      const textColor = isHeader ? 'FFFFFF' : (isLastCol ? C.secondary : C.text);
      s.addShape('rect', { x: cx, y: 1.45 + ri * rowH, w: colW[ci], h: rowH, fill: { color: bg }, line: { color: C.line, width: 0.75 } });
      s.addText(cell, { x: cx + 0.12, y: 1.45 + ri * rowH, w: colW[ci] - 0.24, h: rowH, fontSize: isHeader ? 12 : 11, bold: isHeader || isLastCol, color: textColor, valign: 'middle', align: ci === 0 ? 'left' : 'center' });
      cx += colW[ci];
    });
  });
  s.addText('我们不做硬件，而是让每个摄像头都具备智能的 AI 大脑供应商', { x: 0.5, y: 6.9, w: 12.33, h: 0.3, fontSize: 11, bold: true, color: C.primary, align: 'center' });
  footer(s, 3);
}

// ===== P4 方案总览 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '整体方案', '端云协同架构 + 五层智能叠加');
  const layers = [
    { t: '感知层', s: '摄像头 / K230 / 无人机' },
    { t: '边缘层', s: 'YOLOv8 + DeepSORT' },
    { t: '云端层', s: '豆包大模型 · 规则引擎' },
    { t: 'Agent层', s: '感知/分析/预测/执法' },
    { t: '治理层', s: '后台 · 小程序 · 大屏' },
  ];
  const lw = 2.3, gap = 0.18;
  const sx = (13.33 - (lw * 5 + gap * 4)) / 2;
  layers.forEach((l, i) => {
    const x = sx + i * (lw + gap);
    card(s, x, 1.5, lw, 1.9);
    s.addText(String(i + 1), { x: x, y: 1.55, w: lw, h: 0.3, fontSize: 10, bold: true, color: C.secondary, align: 'center' });
    s.addText(l.t, { x: x, y: 1.9, w: lw, h: 0.5, fontSize: 16, bold: true, color: C.primary, align: 'center' });
    s.addText(l.s, { x: x, y: 2.55, w: lw, h: 0.75, fontSize: 10, color: C.textLight, align: 'center', lineSpacingMultiple: 1.3 });
    if (i < layers.length - 1) s.addText('\u2192', { x: x + lw, y: 2.25, w: gap, h: 0.4, fontSize: 16, color: C.secondary, align: 'center' });
  });
  const feats = [
    { t: '端云协同', d: '90% 本地推理\n10% 云端复核' },
    { t: 'Agent预测', d: '历史趋势预测\n提前预警治理' },
    { t: '自进化学习', d: '用户反馈驱动\n持续微调提升' },
  ];
  feats.forEach((f, i) => {
    const x = 2.2 + i * 3.0;
    card(s, x, 3.85, 2.8, 2.4);
    s.addText(f.t, { x: x, y: 4.0, w: 2.8, h: 0.5, fontSize: 14, bold: true, color: C.primary, align: 'center' });
    s.addShape('rect', { x: x + 1.2, y: 4.5, w: 0.4, h: 0.02, fill: { color: C.secondary } });
    s.addText(f.d, { x: x, y: 4.7, w: 2.8, h: 1.2, fontSize: 11, color: C.textLight, align: 'center', lineSpacingMultiple: 1.5 });
  });
  footer(s, 4);
}

// ===== P5 核心技术演示 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '核心技术演示', '端云协同 · 实时推理 · 多目标跟踪');
  // 左侧模拟检测界面
  card(s, 0.5, 1.45, 7.2, 5.3);
  s.addText('[ 系统截图占位：替换为真实 YOLO 检测界面 ]', { x: 0.5, y: 1.5, w: 7.2, h: 0.35, fontSize: 9, color: C.textLight, align: 'center' });
  s.addShape('rect', { x: 1.1, y: 2.1, w: 1.8, h: 2.4, fill: { color: 'F1F5F9' }, line: { color: C.secondary, width: 2 } });
  s.addText('car  94%', { x: 1.1, y: 4.55, w: 1.8, h: 0.25, fontSize: 9, bold: true, color: C.secondary, align: 'center' });
  s.addShape('rect', { x: 3.6, y: 2.5, w: 1.3, h: 1.6, fill: { color: 'F1F5F9' }, line: { color: C.primary, width: 2 } });
  s.addText('moto  89%', { x: 3.6, y: 4.15, w: 1.3, h: 0.25, fontSize: 9, bold: true, color: C.primary, align: 'center' });
  s.addShape('rect', { x: 5.5, y: 3.1, w: 1.3, h: 1.4, fill: { color: 'F1F5F9' }, line: { color: C.accent, width: 2 } });
  s.addText('no-helmet  82%', { x: 5.5, y: 4.55, w: 1.3, h: 0.25, fontSize: 9, bold: true, color: C.accent, align: 'center' });
  s.addShape('rect', { x: 0.5, y: 5.55, w: 7.2, h: 1.2, fill: { color: 'F1F5F9' } });
  s.addText('实时检测画面 · 30fps · RTX 4060 Laptop', { x: 0.6, y: 5.62, w: 7, h: 0.3, fontSize: 10, color: C.textLight });
  s.addText('检测目标：car · motorcycle · person · helmet · traffic_light', { x: 0.6, y: 5.9, w: 7, h: 0.3, fontSize: 10, color: C.text });
  s.addText('推理延迟 15 ms · 已识别违规 1,284 起 · 准确率 91%', { x: 0.6, y: 6.18, w: 7, h: 0.3, fontSize: 10, bold: true, color: C.primary });
  // 右侧 4 卡片
  const tech = [
    { t: 'YOLOv8 目标检测', d: 'COCO预训练 +\n交通场景微调' },
    { t: 'TensorRT 加速', d: '15ms / 帧\n速度提升 3 倍' },
    { t: 'DeepSORT 跟踪', d: '卡尔曼滤波\n遮挡场景稳定' },
    { t: '豆包大模型', d: '模糊样本\n深度二次确认' },
  ];
  tech.forEach((t, i) => {
    const y = 1.45 + i * 1.32;
    card(s, 8.1, y, 4.73, 1.18);
    s.addText(t.t, { x: 8.3, y: y + 0.08, w: 4.3, h: 0.4, fontSize: 13, bold: true, color: C.primary });
    s.addText(t.d, { x: 8.3, y: y + 0.55, w: 4.3, h: 0.55, fontSize: 10, color: C.textLight, lineSpacingMultiple: 1.3 });
  });
  footer(s, 5);
}

// ===== P6 六大创新 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '六大核心创新', '从识别到治理，系统性领先');
  const inno = [
    { n: '01', t: '端云协同架构', d: '高置信本地处置\n模糊样本云端复核' },
    { n: '02', t: '置信度分级响应', d: '0.6×检测 + 0.3×跟踪\n+ 0.1×环境适配度' },
    { n: '03', t: 'TensorRT 部署', d: '层融合 + 垂直融合\n15 ms/帧' },
    { n: '04', t: '自进化学习', d: '用户审核 \u2192 标注 \u2192 微调\nShadow 测试 \u2192 部署' },
    { n: '05', t: '多 Agent 协同', d: '感知/分析/预测/执法\n四 Agent 全链路协作' },
    { n: '06', t: '预测式治理', d: 'LSTM + GNN\n提前预警违规高发' },
  ];
  inno.forEach((it, i) => {
    const x = 0.5 + (i % 3) * 4.15;
    const y = 1.5 + Math.floor(i / 3) * 2.75;
    card(s, x, y, 3.95, 2.55);
    s.addText(it.n, { x: x, y: y + 0.15, w: 3.95, h: 0.5, fontSize: 14, bold: true, color: C.secondary, align: 'center' });
    s.addText(it.t, { x: x, y: y + 0.7, w: 3.95, h: 0.5, fontSize: 16, bold: true, color: C.primary, align: 'center' });
    s.addShape('rect', { x: x + 1.7, y: y + 1.25, w: 0.55, h: 0.02, fill: { color: C.secondary } });
    s.addText(it.d, { x: x + 0.15, y: y + 1.45, w: 3.65, h: 1.0, fontSize: 11, color: C.textLight, align: 'center', lineSpacingMultiple: 1.5 });
  });
  footer(s, 6);
}

// ===== P7 端云协同原理 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '端云协同架构原理', '本地求速度，云端求深度');
  // 左数据流
  const flow = [
    { t: '摄像头视频流', s: '30 fps · 1080P' },
    { t: 'YOLOv8 目标检测', s: '6类目标 · 15ms/帧' },
    { t: 'DeepSORT 轨迹跟踪', s: '卡尔曼滤波 + 外观特征' },
    { t: '综合置信度评估', s: '0.6×检测 + 0.3×跟踪 + 0.1×环境', hi: true },
    { t: '分级响应', s: '\u22650.8本地 · 0.5-0.8云端 · <0.5排除', hi: true },
  ];
  flow.forEach((f, i) => {
    const y = 1.5 + i * 0.95;
    s.addShape('rect', { x: 0.5, y: y, w: 5.8, h: 0.78, fill: { color: f.hi ? C.secondary : 'F1F5F9' }, line: { color: C.line, width: 0.75 } });
    s.addText(f.t, { x: 0.65, y: y + 0.05, w: 5.5, h: 0.35, fontSize: 12, bold: true, color: f.hi ? 'FFFFFF' : C.text });
    s.addText(f.s, { x: 0.65, y: y + 0.4, w: 5.5, h: 0.3, fontSize: 10, color: f.hi ? 'E8ECF4' : C.textLight });
  });
  // 右上本地/云端
  const comps = [
    { t: '本 地 端', sub: 'RTX 4060 Laptop', d: '处理约 90% 明确样本\n延迟 < 50 ms\n断网可用\n追求「快」与「稳」', color: C.secondary },
    { t: '云 端', sub: '豆包大模型 / 阿里云 ECS', d: '处理约 10% 模糊样本\n深度推理 3-5 s\n多模态语义理解\n追求「准」与「全」', color: C.primary },
  ];
  comps.forEach((c, i) => {
    const y = 1.5 + i * 2.8;
    card(s, 7.0, y, 5.83, 2.55);
    s.addShape('rect', { x: 7.0, y: y, w: 5.83, h: 0.5, fill: { color: c.color } });
    s.addText(c.t, { x: 7.1, y: y + 0.05, w: 2, h: 0.4, fontSize: 12, bold: true, color: 'FFFFFF' });
    s.addText(c.sub, { x: 9.3, y: y + 0.05, w: 3.5, h: 0.4, fontSize: 10, color: 'D8E8E3', align: 'right' });
    s.addText(c.d, { x: 7.2, y: y + 0.75, w: 5.5, h: 1.6, fontSize: 11, color: C.textLight, lineSpacingMultiple: 1.5 });
  });
  footer(s, 7);
}

// ===== P8 竞品对比重点页 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '市场竞品对比', '差异化竞争优势');
  const comps = [
    { t: 'vs 海康 / 大华', d: '我们不做硬件，不直接竞争\n我们提供的是 AI 大脑\n让现有摄像头更智能\n可与硬件厂商深度合作' },
    { t: 'vs 阿里云 / 百度云', d: '云方案重度依赖网络\n我们采用「边缘 + 云端」双通道\n断网仍可工作\n部署成本仅为其 1/10' },
    { t: 'vs 算法 API 厂商', d: '他们只卖算法能力\n我们交付完整可用系统\n含后台 / 小程序 / 大屏\n开箱即用，无需二次开发' },
    { t: 'vs 开源 YOLO 方案', d: '开源 Demo 无法投入商用\n我们提供稳定部署\n运维文档与持续进化\n是真正的生产级解决方案' },
  ];
  comps.forEach((c, i) => {
    const x = 0.5 + (i % 2) * 6.25;
    const y = 1.5 + Math.floor(i / 2) * 2.8;
    card(s, x, y, 6.05, 2.55);
    s.addText(c.t, { x: x + 0.25, y: y + 0.2, w: 5.8, h: 0.45, fontSize: 14, bold: true, color: C.primary });
    s.addShape('rect', { x: x + 0.25, y: y + 0.72, w: 0.6, h: 0.02, fill: { color: C.secondary } });
    s.addText(c.d, { x: x + 0.25, y: y + 0.9, w: 5.55, h: 1.5, fontSize: 11, color: C.textLight, lineSpacingMultiple: 1.55 });
  });
  footer(s, 8);
}

// ===== P9 性能数据 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '性能实测数据', '基于 NVIDIA RTX 4060 Laptop · 真实场景测试');
  // 左 横向条形对比
  s.addText('推理延迟对比', { x: 0.5, y: 1.55, w: 5.5, h: 0.3, fontSize: 12, bold: true, color: C.primary });
  s.addText('PyTorch 原生', { x: 0.5, y: 2.1, w: 2.0, h: 0.35, fontSize: 10, color: C.textLight });
  s.addShape('rect', { x: 2.6, y: 2.15, w: 4.0, h: 0.35, fill: { color: C.line } });
  s.addText('45 ms', { x: 6.7, y: 2.1, w: 0.7, h: 0.35, fontSize: 10, bold: true, color: C.textLight });
  s.addText('TensorRT 优化', { x: 0.5, y: 2.75, w: 2.0, h: 0.35, fontSize: 10, color: C.textLight });
  s.addShape('rect', { x: 2.6, y: 2.8, w: 1.33, h: 0.35, fill: { color: C.secondary } });
  s.addText('15 ms', { x: 6.7, y: 2.75, w: 0.7, h: 0.35, fontSize: 10, bold: true, color: C.secondary });
  s.addText('处理帧率 FPS', { x: 0.5, y: 3.55, w: 5.5, h: 0.3, fontSize: 12, bold: true, color: C.primary });
  s.addText('PyTorch', { x: 0.5, y: 4.1, w: 2.0, h: 0.35, fontSize: 10, color: C.textLight });
  s.addShape('rect', { x: 2.6, y: 4.15, w: 0.66, h: 0.35, fill: { color: C.line } });
  s.addText('22 FPS', { x: 3.4, y: 4.1, w: 1, h: 0.35, fontSize: 10, bold: true, color: C.textLight });
  s.addText('TensorRT', { x: 0.5, y: 4.75, w: 2.0, h: 0.35, fontSize: 10, color: C.textLight });
  s.addShape('rect', { x: 2.6, y: 4.8, w: 2.0, h: 0.35, fill: { color: C.secondary } });
  s.addText('66 FPS', { x: 4.7, y: 4.75, w: 1, h: 0.35, fontSize: 10, bold: true, color: C.secondary });
  // 右下徽章
  const badges = [
    { n: '15', unit: 'ms', l: '单帧推理' },
    { n: '66', unit: 'FPS', l: '实时帧率' },
    { n: '\u00d73', unit: '', l: '速度提升' },
    { n: '6', unit: '类', l: '目标检测' },
  ];
  badges.forEach((b, i) => {
    const y = 1.55 + i * 1.25;
    card(s, 7.8, y, 5.03, 1.12);
    s.addText(b.n, { x: 7.8, y: y + 0.1, w: 2.0, h: 0.7, fontSize: 32, bold: true, color: C.secondary, align: 'center' });
    s.addText(b.unit, { x: 9.8, y: y + 0.3, w: 0.6, h: 0.45, fontSize: 11, color: C.textLight });
    s.addText(b.l, { x: 10.4, y: y + 0.1, w: 2.3, h: 0.45, fontSize: 13, bold: true, color: C.primary });
    s.addText('端到端实测，持续优化中', { x: 10.4, y: y + 0.55, w: 2.3, h: 0.4, fontSize: 9, color: C.textLight });
  });
  footer(s, 9);
}

// ===== P10 违规判据引擎 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '违规判据引擎', '4类违规 · 规则 + AI 双验证');
  const rules = [
    { n: '01', t: '闯红灯', trig: '红灯亮起后车辆越过停止线\n且未立即停止', param: '越线阈值：10 像素' },
    { n: '02', t: '逆行', trig: '跟踪轨迹方向与车道方向\n夹角 > 150°', param: '夹角阈值：150°' },
    { n: '03', t: '未戴头盔', trig: '二轮车检测框内\n未检测到头盔', param: '置信度阈值：0.5' },
    { n: '04', t: '违法停车', trig: '禁停区域内目标\n停留 > 30 秒', param: '停留帧数阈值：30 帧' },
  ];
  rules.forEach((r, i) => {
    const y = 1.5 + i * 1.3;
    card(s, 0.5, y, 12.33, 1.15);
    s.addShape('rect', { x: 0.5, y: y, w: 1.3, h: 1.15, fill: { color: C.primary } });
    s.addText(r.n, { x: 0.5, y: y + 0.1, w: 1.3, h: 0.45, fontSize: 22, bold: true, color: 'FFFFFF', align: 'center' });
    s.addText(r.t, { x: 0.5, y: y + 0.6, w: 1.3, h: 0.45, fontSize: 12, bold: true, color: 'FFFFFF', align: 'center' });
    s.addText('触发条件', { x: 2.1, y: y + 0.1, w: 5.0, h: 0.3, fontSize: 10, bold: true, color: C.secondary });
    s.addText(r.trig, { x: 2.1, y: y + 0.4, w: 5.0, h: 0.7, fontSize: 11, color: C.text, lineSpacingMultiple: 1.35 });
    s.addText('关键参数', { x: 7.5, y: y + 0.1, w: 5.0, h: 0.3, fontSize: 10, bold: true, color: C.secondary });
    s.addText(r.param, { x: 7.5, y: y + 0.45, w: 5.0, h: 0.65, fontSize: 11, color: C.text });
  });
  footer(s, 10);
}

// ===== P11 Agent 架构 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '多 Agent 协同决策', '从单一识别升级为智能体协作');
  const agents = [
    { n: '1', t: '感知 Agent', d: '多源视频流融合\n目标检测跟踪\n异常行为识别', out: '标准化违规事件元数据' },
    { n: '2', t: '分析 Agent', d: '多模态深度理解\n违规自动分类\n置信度评估', out: '带证据链的违规报告' },
    { n: '3', t: '预测 Agent', d: 'LSTM 时序预测\nGNN 空间建模\n事件关联分析', out: '明日违规热力预测' },
    { n: '4', t: '执法 Agent', d: '自动生成文书\n证据区块链存证\n交管平台推送', out: '可直接提交电子证据包' },
  ];
  agents.forEach((a, i) => {
    const x = 0.5 + i * 3.15;
    card(s, x, 1.5, 2.95, 5.0);
    s.addShape('ellipse', { x: x + 1.15, y: 1.65, w: 0.65, h: 0.65, fill: { color: i % 2 === 0 ? C.primary : C.secondary } });
    s.addText(a.n, { x: x + 1.15, y: 1.68, w: 0.65, h: 0.65, fontSize: 18, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
    s.addText(a.t, { x: x, y: 2.5, w: 2.95, h: 0.45, fontSize: 15, bold: true, color: C.primary, align: 'center' });
    s.addShape('rect', { x: x + 1.2, y: 3.0, w: 0.55, h: 0.02, fill: { color: C.secondary } });
    s.addText(a.d, { x: x + 0.15, y: 3.2, w: 2.65, h: 1.2, fontSize: 10.5, color: C.textLight, align: 'center', lineSpacingMultiple: 1.45 });
    s.addShape('rect', { x: x + 0.2, y: 4.55, w: 2.55, h: 0.02, fill: { color: C.line } });
    s.addText('输出', { x: x + 0.2, y: 4.65, w: 2.55, h: 0.25, fontSize: 9, color: C.secondary, align: 'center' });
    s.addText(a.out, { x: x + 0.2, y: 4.9, w: 2.55, h: 1.0, fontSize: 10, bold: true, color: C.text, align: 'center', lineSpacingMultiple: 1.3 });
    if (i < agents.length - 1) {
      s.addText('\u2192', { x: x + 2.95, y: 3.1, w: 0.2, h: 0.6, fontSize: 18, color: C.secondary, align: 'center' });
    }
  });
  footer(s, 11);
}

// ===== P12 预测式治理 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '预测式主动治理', '从事后发现到事前预防');
  // 左侧输入源
  const inputs = [
    ['历史违规记录', '30 天滚动窗口'],
    ['实时路况 API', '每 5 分钟更新'],
    ['天气预报 API', '每小时更新'],
    ['节假日日历', '实时数据'],
    ['学校课表', '学期制'],
    ['大型活动', '提前录入'],
  ];
  inputs.forEach((it, i) => {
    const y = 1.55 + i * 0.72;
    card(s, 0.5, y, 3.8, 0.6);
    s.addText(it[0], { x: 0.65, y: y + 0.05, w: 2.2, h: 0.5, fontSize: 11, color: C.text });
    s.addText(it[1], { x: 2.85, y: y + 0.05, w: 1.35, h: 0.5, fontSize: 9, color: C.textLight, align: 'right' });
  });
  // 中间模型
  card(s, 4.6, 1.55, 3.5, 4.4);
  s.addText('模型融合层', { x: 4.6, y: 1.65, w: 3.5, h: 0.35, fontSize: 11, bold: true, color: C.secondary, align: 'center' });
  const models = ['LSTM · 时序规律', 'GNN · 空间关联', 'Transformer · 语义', 'MoE · 专家决策'];
  models.forEach((m, i) => {
    const y = 2.15 + i * 0.75;
    s.addShape('rect', { x: 4.85, y: y, w: 3.0, h: 0.55, fill: { color: 'F1F5F9' } });
    s.addText(m, { x: 4.85, y: y + 0.08, w: 3.0, h: 0.45, fontSize: 10, color: C.primary, align: 'center' });
  });
  // 右侧预测报告
  card(s, 8.5, 1.55, 4.33, 4.8);
  s.addShape('rect', { x: 8.5, y: 1.55, w: 4.33, h: 0.5, fill: { color: C.primary } });
  s.addText('明日治理预测报告', { x: 8.5, y: 1.6, w: 4.33, h: 0.4, fontSize: 11, bold: true, color: 'FFFFFF', align: 'center' });
  const items = [
    { level: '🚨', t: '人民路路口 · 17-19 时', d: '违停风险 92% · 提前巡逻机器人', color: 'FFF5F5', tc: C.accent },
    { level: '🔶', t: '科技大学南门 · 07:30-8:30', d: '逆行风险 75% · 铁骑值守', color: 'FFFAF0', tc: 'D97706' },
    { level: '🟡', t: '滨江公园东侧 · 全天', d: '违停风险 52% · 引导指示牌', color: 'F8FAFC', tc: C.textLight },
  ];
  items.forEach((it, i) => {
    const y = 2.25 + i * 1.35;
    s.addShape('rect', { x: 8.6, y: y, w: 4.13, h: 1.2, fill: { color: it.color } });
    s.addText(it.level + ' ' + it.t, { x: 8.75, y: y + 0.05, w: 3.8, h: 0.35, fontSize: 10, bold: true, color: it.tc });
    s.addText(it.d, { x: 8.75, y: y + 0.5, w: 3.8, h: 0.6, fontSize: 9.5, color: C.text, lineSpacingMultiple: 1.3 });
  });
  footer(s, 12);
}

// ===== P13 自进化数据图表 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '自进化持续学习', '用户反馈驱动，系统越用越聪明');
  // 上方流程
  const loop = ['① AI 检测', '② 用户审核', '③ 新增标注', '④ 模型微调', '⑤ Shadow 测试', '⑥ 线上部署'];
  loop.forEach((l, i) => {
    const x = 0.5 + i * 2.05;
    card(s, x, 1.5, 1.9, 0.75);
    s.addText(l, { x: x, y: 1.55, w: 1.9, h: 0.65, fontSize: 10, bold: true, color: C.primary, align: 'center' });
    if (i < loop.length - 1) s.addText('\u2192', { x: x + 1.9, y: 1.55, w: 0.15, h: 0.75, fontSize: 14, color: C.secondary, align: 'center' });
  });
  // 左侧 4 个提升卡片
  const impr = [
    { l: '检测准确率', v: '91%', f: '82% \u2192 91%' },
    { l: '日均事件数', v: '580', f: '120 \u2192 580' },
    { l: '误报率', v: '5%', f: '18% \u2192 5%' },
    { l: '执法耗时', v: '4.5 min', f: '30min \u2192 4.5min' },
  ];
  impr.forEach((m, i) => {
    const y = 2.7 + i * 0.82;
    card(s, 0.5, y, 6.0, 0.72);
    s.addText(m.l, { x: 0.65, y: y + 0.1, w: 2.0, h: 0.5, fontSize: 11, bold: true, color: C.text });
    s.addText(m.f, { x: 2.8, y: y + 0.1, w: 2.0, h: 0.5, fontSize: 11, color: C.textLight, align: 'center' });
    s.addText(m.v, { x: 4.9, y: y + 0.05, w: 1.5, h: 0.6, fontSize: 18, bold: true, color: C.secondary, align: 'right' });
  });
  // 右侧折线（模拟）
  card(s, 7.8, 2.7, 5.03, 3.3);
  s.addText('准确率随时间提升', { x: 7.8, y: 2.75, w: 5.03, h: 0.3, fontSize: 11, bold: true, color: C.primary, align: 'center' });
  // 网格
  for (let g = 0; g < 4; g++) {
    s.addShape('rect', { x: 8.0, y: 3.35 + g * 0.6, w: 4.65, h: 0.015, fill: { color: 'E8ECF4' } });
  }
  // 数据点 + 折线
  const dPts = [
    { x: 8.2, y: 5.2, v: '82%' },
    { x: 9.1, y: 4.9, v: '85%' },
    { x: 10.0, y: 4.5, v: '88%' },
    { x: 10.9, y: 4.1, v: '90%' },
    { x: 11.6, y: 3.8, v: '91%' },
  ];
  for (let k = 0; k < dPts.length - 1; k++) {
    s.addShape('line', { x: dPts[k].x, y: dPts[k].y, x2: dPts[k + 1].x, y2: dPts[k + 1].y, line: { color: C.secondary, width: 1.5 } });
  }
  dPts.forEach(p => {
    s.addShape('ellipse', { x: p.x - 0.08, y: p.y - 0.08, w: 0.18, h: 0.18, fill: { color: C.primary } });
  });
  s.addText('第1月', { x: 8.0, y: 5.75, w: 0.7, h: 0.2, fontSize: 9, color: C.textLight, align: 'center' });
  s.addText('第2月', { x: 9.9, y: 5.75, w: 0.7, h: 0.2, fontSize: 9, color: C.textLight, align: 'center' });
  s.addText('第3月', { x: 11.5, y: 5.75, w: 0.7, h: 0.2, fontSize: 9, color: C.textLight, align: 'center' });
  footer(s, 13);
}

// ===== P14 商业模式 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '商业模式', '三条收入线，可持续成长');
  const biz = [
    { t: 'To G · 政府客户', sub: '区县级交警支队 · 智慧城市中心', items: ['平台+定制化部署', '30-80 万/年 · 区县', '200-500 万/年 · 市级'], reason: '降低50%人力成本\n数字化考核加分\n证据链对接法院', color: C.primary },
    { t: 'To B · 企业客户', sub: '物业 · 商业综合体 · 物流', items: ['SaaS 订阅 2999 元/月', 'API 调用 0.1 元/次', '数据报告 5000 元/次'], reason: '降低管理成本\n提升安全合规\n创造数据增值', color: C.secondary },
    { t: 'To School · 高校', sub: 'AI / 交通专业院校', items: ['实验室建设方案', '15-30 万/校', '论文/竞赛训练'], reason: '教学实验平台\n学科竞赛训练\n联合研究成果', color: '4A5568' },
  ];
  biz.forEach((b, i) => {
    const x = 0.5 + i * 4.2;
    card(s, x, 1.5, 4.05, 5.2);
    s.addShape('rect', { x: x, y: 1.5, w: 4.05, h: 0.6, fill: { color: b.color } });
    s.addText(b.t, { x: x, y: 1.55, w: 4.05, h: 0.5, fontSize: 13, bold: true, color: 'FFFFFF', align: 'center' });
    s.addText(b.sub, { x: x + 0.15, y: 2.25, w: 3.75, h: 0.4, fontSize: 10, color: C.textLight, align: 'center' });
    s.addText('收费方式', { x: x + 0.15, y: 2.75, w: 3.75, h: 0.25, fontSize: 10, bold: true, color: b.color });
    b.items.forEach((it, j) => {
      s.addText(it, { x: x + 0.3, y: 3.05 + j * 0.3, w: 3.5, h: 0.28, fontSize: 10, color: C.text });
    });
    s.addShape('rect', { x: x + 0.15, y: 4.15, w: 3.75, h: 0.015, fill: { color: C.line } });
    s.addText('客户付费驱动力', { x: x + 0.15, y: 4.35, w: 3.75, h: 0.25, fontSize: 10, bold: true, color: b.color });
    s.addText(b.reason, { x: x + 0.15, y: 4.6, w: 3.75, h: 1.8, fontSize: 10, color: C.textLight, lineSpacingMultiple: 1.5 });
  });
  footer(s, 14);
}

// ===== P15 社会价值 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '社会价值', '让每一次出行都更安全');
  const vals = [
    { big: '30%', l: '交通事故死亡率', icon: '🚗', d: '实时预警 + 主动劝阻\n降低违规事故率' },
    { big: '15%', l: '拥堵碳排放', icon: '🌿', d: '减少无效巡逻里程\n交通流整体优化' },
    { big: '50%', l: '治理人力成本', icon: '💰', d: 'AI 替代人工巡查\n财政开支更高效' },
    { big: '标杆', l: '智慧城市建设', icon: '🏙️', d: '可复制 AI 治理基础设施\n支持平安交通建设' },
  ];
  vals.forEach((v, i) => {
    const x = 0.5 + i * 3.15;
    card(s, x, 1.5, 2.95, 5.2);
    s.addText(v.icon, { x: x, y: 1.6, w: 2.95, h: 0.7, fontSize: 34, align: 'center' });
    s.addText(v.big, { x: x, y: 2.4, w: 2.95, h: 0.9, fontSize: 30, bold: true, color: C.secondary, align: 'center' });
    s.addText(v.l, { x: x, y: 3.25, w: 2.95, h: 0.35, fontSize: 12, bold: true, color: C.primary, align: 'center' });
    s.addShape('rect', { x: x + 1.2, y: 3.75, w: 0.55, h: 0.02, fill: { color: C.line } });
    s.addText(v.d, { x: x + 0.15, y: 3.95, w: 2.65, h: 1.5, fontSize: 10, color: C.textLight, align: 'center', lineSpacingMultiple: 1.45 });
  });
  footer(s, 15);
}

// ===== P16 发展路线图 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '发展路线图', '2026.05 — 2027.05 · 与申请书一致');
  s.addShape('rect', { x: 0.8, y: 3.0, w: 11.7, h: 0.04, fill: { color: C.line } });
  const nodes = [
    { date: '2026.05', phase: '准备阶段', d: '立项与需求\n调研方案设计' },
    { date: '2026.06-11', phase: '开发阶段', d: 'YOLO训练\nTensorRT 部署\n判据引擎' },
    { date: '2026.11-\n2027.02', phase: '联调测试', d: '端云联调\nK230实物\n校园实场景' },
    { date: '2027.03-05', phase: '结题验收', d: '专利申请\n论文发表\n成果转化' },
  ];
  nodes.forEach((n, i) => {
    const x = 0.8 + i * 3.1;
    s.addShape('ellipse', { x: x + 1.1, y: 2.85, w: 0.35, h: 0.35, fill: { color: i === 0 ? C.secondary : C.primary } });
    s.addText(n.date, { x: x, y: 2.1, w: 2.6, h: 0.5, fontSize: 11, bold: true, color: C.primary, align: 'center', lineSpacingMultiple: 1.2 });
    card(s, x, 3.3, 2.6, 2.5);
    s.addText(n.phase, { x: x, y: 3.35, w: 2.6, h: 0.4, fontSize: 12, bold: true, color: C.primary, align: 'center' });
    s.addShape('rect', { x: x + 1.05, y: 3.8, w: 0.5, h: 0.02, fill: { color: C.secondary } });
    s.addText(n.d, { x: x + 0.15, y: 3.95, w: 2.3, h: 1.6, fontSize: 10, color: C.textLight, align: 'center', lineSpacingMultiple: 1.45 });
  });
  // 底部预期成果
  s.addText('预期成果', { x: 0.5, y: 6.0, w: 2.0, h: 0.3, fontSize: 11, bold: true, color: C.primary });
  const out = ['结题报告×1', '可演示原型×1', 'K230 实物×1', '实用新型专利×1', '学术论文×1'];
  out.forEach((o, i) => {
    s.addShape('rect', { x: 2.8 + i * 2.0, y: 6.0, w: 1.9, h: 0.4, fill: { color: 'F1F5F9' } });
    s.addText(o, { x: 2.8 + i * 2.0, y: 6.05, w: 1.9, h: 0.35, fontSize: 10, bold: true, color: C.textLight, align: 'center' });
  });
  footer(s, 16);
}

// ===== P17 团队 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '团队介绍', '跨专业融合 · 扎实落地');
  // 成员 5 人
  const mem = [
    { n: '陈俊龙', r: '项目主持' },
    { n: '母书祯', r: '技术负责' },
    { n: '苗博文', r: '产品负责' },
    { n: '余林峰', r: '商务负责' },
    { n: '王泽轩', r: '开发成员' },
  ];
  mem.forEach((m, i) => {
    const x = 0.5 + i * 2.52;
    card(s, x, 1.5, 2.3, 2.8);
    s.addShape('ellipse', { x: x + 0.75, y: 1.7, w: 0.8, h: 0.8, fill: { color: C.primary } });
    s.addText(m.n, { x: x, y: 2.7, w: 2.3, h: 0.5, fontSize: 14, bold: true, color: C.primary, align: 'center' });
    s.addText(m.r, { x: x, y: 3.15, w: 2.3, h: 0.3, fontSize: 11, color: C.textLight, align: 'center' });
    s.addText('电气工程及其自动化\n宁夏理工学院', { x: x + 0.15, y: 3.55, w: 2.0, h: 0.5, fontSize: 10, color: C.textLight, align: 'center', lineSpacingMultiple: 1.4 });
  });
  // 指导教师
  card(s, 0.5, 4.8, 6.0, 1.8);
  s.addText('指导教师', { x: 0.5, y: 4.85, w: 6.0, h: 0.35, fontSize: 12, bold: true, color: C.primary, align: 'center' });
  s.addText('赵智雯 讲师 · 研究方向：复杂工业建模与优化\n汪永奇', { x: 0.5, y: 5.25, w: 6.0, h: 0.8, fontSize: 11, color: C.text, align: 'center', lineSpacingMultiple: 1.5 });
  // 前期成果
  card(s, 6.8, 4.8, 6.0, 1.8);
  s.addText('前期技术积累', { x: 6.8, y: 4.85, w: 6.0, h: 0.35, fontSize: 12, bold: true, color: C.secondary, align: 'center' });
  s.addText('"瞳声"端云协同智能识别系统（PC端+K230端\n已掌握 YOLO部署 · 云端API调用 · 语音合成 · 嵌入式调试', { x: 6.8, y: 5.25, w: 6.0, h: 1.0, fontSize: 11, color: C.text, align: 'center', lineSpacingMultiple: 1.5 });
  footer(s, 17);
}

// ===== P18 致谢 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgDark };
  s.addText('让每一次出行，都更安全。', { x: 0.5, y: 2.5, w: 12.33, h: 1.0, fontSize: 42, bold: true, color: 'FFFFFF', align: 'center' });
  s.addShape('rect', { x: 5.2, y: 3.7, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  s.addText('智瞳灵声 · CityGuardian', { x: 0.5, y: 4.0, w: 12.33, h: 0.5, fontSize: 20, bold: true, color: C.secondary, align: 'center' });
  s.addText('基于视觉识别与云端推理的智慧交管系统', { x: 0.5, y: 4.55, w: 12.33, h: 0.4, fontSize: 14, color: 'B8C5D6', align: 'center' });
  s.addText('宁夏理工学院 · 电气信息工程学院', { x: 0.5, y: 5.5, w: 12.33, h: 0.35, fontSize: 12, color: '8E9AAF', align: 'center' });
  s.addText('感谢各位评委老师的指导与支持', { x: 0.5, y: 6.3, w: 12.33, h: 0.35, fontSize: 11, color: '6E7B8F', align: 'center' });
}

// ===== 生成文件 =====
pptx.writeFile({ fileName: '智瞳灵声_国赛答辩_v3.pptx' });
console.log('PPT v3 生成完成: 智瞳灵声_国赛答辩_v3.pptx');

