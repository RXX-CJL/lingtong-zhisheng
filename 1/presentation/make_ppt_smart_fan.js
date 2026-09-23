// Smart_Fan v2.3 - 智能风扇控制系统 答辩 PPT（15页版）
// 基于 STM32 + OLED + DHT11 + 人体感应 + 编码器 + PWM 调速
// 参考智瞳灵声风格，宋体 + 蓝绿主色
const pptxgen = require('pptxgenjs');
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.title = 'Smart_Fan_v2.3_答辩';
pptx.author = '项目团队';

const FONT = '宋体';
const C = {
  primary: '0F3460', secondary: '16A085', accent: 'E55934',
  text: '1A1A2E', textLight: '5A5A7A', line: 'D8DEE9',
  bgLight: 'F8FAFC', bgCard: 'FFFFFF', bgDark: '0A1628'
};
const TOTAL = 15;

// ===== 辅助函数 =====
function footer(slide, page) {
  slide.addText('Smart_Fan v2.3', { x: 0.5, y: 7.28, w: 4, h: 0.2, fontSize: 10, fontName: FONT, color: C.textLight });
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
  slide.addText(text, Object.assign({ x: x, y: y, w: w, h: h, fontSize: fs, fontName: FONT, color: color || C.text, align: 'left' }, extra));
}

// ===== P1 封面 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgDark };
  s.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.05, fill: { color: C.secondary } });
  s.addText('智能传感 · 智能调速 · 智能人机', { x: 0.7, y: 0.5, w: 12, h: 0.3, fontSize: 14, fontName: FONT, color: '8E9AAF', align: 'center' });
  s.addText('Smart_Fan v2.3', { x: 0.5, y: 2.3, w: 12.33, h: 1.3, fontSize: 72, fontName: FONT, bold: true, color: 'FFFFFF', align: 'center' });
  s.addText('基于 STM32 的多模式智能风扇控制系统', { x: 0.5, y: 3.65, w: 12.33, h: 0.5, fontSize: 22, fontName: FONT, color: C.secondary, italic: true, align: 'center' });
  s.addShape('rect', { x: 5.7, y: 4.25, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  s.addText('定时 · 手动 · 自动 · 温湿度感应 · 人体感应 · OLED 菜单交互', { x: 0.5, y: 4.45, w: 12.33, h: 0.5, fontSize: 16, fontName: FONT, color: 'E8ECF4', align: 'center' });
  s.addText('项目团队 · 嵌入式课程设计', { x: 0.5, y: 5.8, w: 12.33, h: 0.35, fontSize: 16, fontName: FONT, color: 'B8C5D6', align: 'center' });
  s.addText('开发周期：2024', { x: 0.5, y: 6.25, w: 12.33, h: 0.3, fontSize: 14, fontName: FONT, color: '8E9AAF', align: 'center' });
}

// ===== P2 项目背景与痛点 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '项目背景与痛点', '普通风扇为何需要智能化');
  const pain = [
    { num: '01', big: '手动', title: '操作不便', desc: '传统风扇档位固定档位少，每次调整需起身\n夜间起身操作，影响休息' },
    { num: '02', big: '无感知', title: '环境无感', desc: '不感知温度湿度变化\n温度高转速不感知环境，温度高风速不变' },
    { num: '03', big: '浪费', title: '能耗浪费', desc: '无人时继续运转\n长时间忘记关闭造成浪费' },
    { num: '04', big: '单一', title: '功能单一', desc: '仅手动按键调速\n不智能、无定时、无自动调节' }
  ];
  pain.forEach((p, i) => {
    const x = 0.5 + i * 3.15;
    card(s, x, 1.55, 2.95, 5.3);
    bigText(s, x, 1.65, 2.95, 0.35, p.num, 14, C.secondary);
    bigText(s, x, 2.15, 2.95, 1.0, p.big, 44, C.primary);
    bigText(s, x, 3.3, 2.95, 0.4, p.title, 16, C.text);
    s.addShape('rect', { x: x + 1.2, y: 3.8, w: 0.55, h: 0.02, fill: { color: C.line } });
    t(s, x + 0.2, 4.0, 2.55, 1.4, p.desc, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });
  });
  t(s, 0.5, 7.0, 12.33, 0.3, 'Smart_Fan v2.3：让风扇「听得懂」环境，「看得懂」人', 14, C.primary, { align: 'center', bold: true });
  footer(s, 2);
}

// ===== P3 功能总览（大卡） =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '系统功能总览', '四类工作模式，覆盖全场景');

  const modes = [
    { num: '01', title: '定时模式', desc: '可设置时/分/秒倒计时结束自动停止支持任意转速', color: C.primary },
    { num: '02', title: '手动模式', desc: '旋转编码器无极调速旋钮一键锁定防止误触支持 0-100 无级调节', color: C.secondary },
    { num: '03', title: '自动模式', desc: '温度控制（滞回保护）/ 湿度控制（滞回保护）/ 人体感应节能', color: C.accent },
    { num: '04', title: '测速模式', desc: '手动调速+实时RPM反馈传感器数据实时显示旋钮可锁定', color: 'E55934' }
  ];
  modes.forEach((m, i) => {
    const x = 0.5 + i * 3.1;
    card(s, x, 1.55, 2.9, 3.0);
    t(s, x, 1.65, 2.9, 0.6, m.num, 18, m.color, { align: 'center', bold: true });
    t(s, x, 2.3, 2.9, 0.55, m.title, 18, C.primary, { align: 'center', bold: true });
    s.addShape('rect', { x: x + 1.2, y: 2.95, w: 0.5, h: 0.02, fill: { color: C.secondary } });
    t(s, x + 0.1, 3.15, 2.7, 1.0, m.desc, 11, C.textLight, { align: 'center', lineSpacingMultiple: 1.5 });
  });

  // 下方特色徽章
  const feat = [
    { t: 'OLED 菜单交互', d: '0.96寸 I2C OLED 中文菜单多级导航反色高亮' },
    { t: '多传感器融合', d: 'DHT11 温湿度 · HC-SR505 人体 · 光敏/热敏 ADC' },
    { t: 'PWM 精准调速', d: 'TIM2 硬件 PWM 0-100 级精准调速支持正反转' },
    { t: '滞回保护', d: '温湿度临界值防抖动算法保护电机延长寿命' }
  ];
  feat.forEach((f, i) => {
    const x = 0.5 + i * 3.15;
    card(s, x, 5.4, 2.95, 1.4);
    t(s, x, 5.55, 2.95, 0.4, f.t, 14, C.primary, { align: 'center', bold: true });
    t(s, x, 5.95, 2.95, 0.8, f.d, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.3 });
  });
  footer(s, 3);
}

// ===== P4 硬件架构 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '系统硬件架构', 'STM32 主控 + 模块化外设');

  // 硬件列表
  const hw = [
    { n: 'MCU', t: 'STM32F103C8', d: 'ARM Cortex-M3\n72 MHz · 64KB Flash\n20KB SRAM' },
    { n: '显示', t: 'OLED 0.96"', d: 'I2C 接口 · SSD1306\n128×64 像素\n支持中文显示' },
    { n: '传感', t: 'DHT11', d: '单总线协议\n温度 0-50°C\n湿度 20-90% RH' },
    { n: '人体', t: 'HC-SR505', d: '红外感应\n感应距离 3m\n感应延迟可调' },
    { n: '输入', t: '旋转编码器', d: '两相脉冲 + 按键\nEXTI 中断\n按键防抖' },
    { n: '执行', t: '直流电机', d: 'PWM 驱动 (TIM2 CH3)\nAIN1/AIN2 正反转\n转速反馈 ADC' },
    { n: '光感', t: '光敏 / 热敏', d: 'ADC 采集\n光照强度采集\n环境温度感知' },
    { n: '时钟', t: '定时器', d: 'TIM3 定时中断\n毫秒级精度\n倒计时自动停止' }
  ];
  hw.forEach((h, i) => {
    const x = 0.5 + (i % 4) * 3.15;
    const y = 1.55 + Math.floor(i / 4) * 2.7;
    card(s, x, y, 2.95, 2.5);
    s.addShape('rect', { x: x + 1.15, y: y + 0.15, w: 0.65, h: 0.65, fill: { color: C.primary } });
    t(s, x + 1.15, y + 0.15, 0.65, 0.65, h.n, 14, 'FFFFFF', { align: 'center', bold: true, valign: 'middle' });
    t(s, x, y + 1.1, 2.95, 0.5, h.t, 16, C.primary, { align: 'center', bold: true });
    t(s, x + 0.2, y + 1.65, 2.55, 1.0, h.d, 11, C.textLight, { align: 'center', lineSpacingMultiple: 1.4 });
  });
  footer(s, 4);
}

// ===== P5 软件系统架构 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '软件系统架构', '分层架构 · 模块化设计');

  // 数据流从下往上
  const layers = [
    { t: '应用层', items: ['主菜单调度', '定时模式', '手动模式', '自动模式'], color: C.primary },
    { t: '业务逻辑层', items: ['温度控制算法', '湿度控制算法', '人体感应判断', '编码器输入处理'], color: C.secondary },
    { t: '驱动层', items: ['OLED I2C 驱动', 'DHT11 单总线', 'TIM PWM 驱动', 'ADC 采集'], color: C.text },
    { t: '硬件层', items: ['STM32F103', 'GPIO / EXTI', 'TIM / ADC', 'I2C'], color: '64748B' }
  ];

  layers.forEach((l, i) => {
    const y = 1.55 + i * 1.35;
    s.addShape('rect', { x: 0.5, y: y, w: 12.33, h: 1.2, fill: { color: l.color }, line: { color: C.line, width: 0.75 } });
    t(s, 0.5, y, 12.33, 1.2, l.t, 16, 'FFFFFF', { bold: true, align: 'left', valign: 'middle' });
    l.items.forEach((it, j) => {
      t(s, 2.8 + j * 2.5, y, 2.4, 1.2, it, 13, 'FFFFFF', { valign: 'middle' });
    });
  });
  t(s, 0.5, 7.0, 12.33, 0.3, '主循环：菜单按键扫描 → 菜单显示 → 传感器数据更新 → OLED 刷新（每秒一次）', 13, C.primary, { align: 'center', bold: true });
  footer(s, 5);
}

// ===== P6 OLED 菜单交互 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, 'OLED 菜单交互系统', '多级中文菜单 · 反色指针导航');

  // 左侧 模拟 OLED 屏幕
  card(s, 0.5, 1.55, 5.5, 5.0);
  t(s, 0.5, 1.6, 5.5, 0.4, '[ OLED 屏幕实时显示示例', 12, C.textLight, { align: 'center' });
  // 模拟屏幕
  s.addShape('rect', { x: 1.0, y: 2.0, w: 4.5, h: 4.0, fill: { color: '0A1628' } });
  t(s, 1.0, 2.2, 4.5, 0.6, '主菜单', 18, '16A085', { align: 'center', bold: true });
  t(s, 1.0, 3.0, 4.5, 0.5, '● 定时模式', 14, 'FFFFFF', { align: 'center' });
  t(s, 1.0, 3.6, 4.5, 0.5, '  手动模式', 14, 'B8C5D6', { align: 'center' });
  t(s, 1.0, 4.2, 4.5, 0.5, '  自动模式', 14, 'B8C5D6', { align: 'center' });
  t(s, 1.0, 5.2, 4.5, 0.5, '温度：25.3°C', 12, '16A085', { align: 'center' });

  // 右侧 菜单树
  t(s, 7.0, 1.55, 5.83, 0.4, '菜单结构', 16, C.primary, { bold: true });
  const tree = [
    { lvl: '主菜单', c: C.primary, items: '定时 / 手动 / 自动 / 测速模式' },
    { lvl: '定时模式', c: C.secondary, items: '设置时/分/秒 + 转速 → 启动 → 倒计时运行' },
    { lvl: '手动模式', c: C.secondary, items: '编码器调节转速 (0-100) → 旋钮可锁定' },
    { lvl: '自动-温度', c: C.secondary, items: '滞回保护启动>=28C关闭<=25C公式：T*3-12' },
    { lvl: '自动-湿度', c: C.secondary, items: '滞回保护启动>=55%关闭<=50%公式：H*1.5-1' },
    { lvl: '测速模式', c: C.secondary, items: '编码器调速+旋钮锁定+实时RPM反馈+传感器' }
  ];
  tree.forEach((n, i) => {
    const y = 2.1 + i * 0.75;
    s.addShape('rect', { x: 7.0, y: y, w: 5.83, h: 0.55, fill: { color: 'F1F5F9' } });
    t(s, 7.15, y + 0.1, 2.0, 0.5, n.lvl, 13, n.c, { bold: true });
    t(s, 9.15, y + 0.1, 3.53, 0.5, n.items, 11, C.text);
  });
  footer(s, 6);
}

// ===== P7 核心算法 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '核心控制算法（含滞回保护）', '环境感知 → 智能决策 → PWM 输出');

  // 温度控制公式卡
  card(s, 0.5, 1.55, 6.0, 5.0);
  t(s, 0.5, 1.6, 6.0, 0.4, '温度控制策略（滞回保护）', 14, C.primary, { bold: true, align: 'center' });
  s.addShape('rect', { x: 2.5, y: 2.05, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  t(s, 0.7, 2.3, 5.6, 0.4, '滞回区间：3°C（防抖动）', 12, C.accent, { bold: true });
  t(s, 0.7, 2.7, 5.6, 0.6, '启动：温度 >= 28°C 且有人\n关闭：温度 <= 25°C 或 < 15°C\n滞回区间内保持当前转速不变', 11, C.text, { lineSpacingMultiple: 1.4 });
  t(s, 0.7, 3.5, 5.6, 0.4, '转速计算公式', 13, C.secondary, { bold: true });
  s.addShape('rect', { x: 0.7, y: 3.95, w: 5.6, h: 0.7, fill: { color: 'F1F5F9' } });
  t(s, 0.7, 4.0, 5.6, 0.7, 'Speed = Temp_int x 3 - 12\n上限：min(Speed, 100)', 13, C.primary, { align: 'center', bold: true });
  t(s, 0.7, 4.85, 5.6, 0.4, '示例：25C → 25x3-12=63档（不触发启停）', 11, C.textLight);
  t(s, 0.7, 5.3, 5.6, 0.4, '示例：28C → 28x3-12=72档（启动风扇）', 11, C.secondary, { bold: true });
  t(s, 0.7, 5.8, 5.6, 0.4, '无人感应 → 立即停机节能', 11, C.textLight);

  // 湿度控制公式卡
  card(s, 7.0, 1.55, 5.83, 5.0);
  t(s, 7.0, 1.6, 5.83, 0.4, '湿度控制策略（滞回保护）', 14, C.primary, { bold: true, align: 'center' });
  s.addShape('rect', { x: 9.0, y: 2.05, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  t(s, 7.2, 2.3, 5.43, 0.4, '滞回区间：5%RH（防抖动）', 12, C.accent, { bold: true });
  t(s, 7.2, 2.7, 5.43, 0.6, '启动：湿度 >= 55% RH 且有人\n关闭：湿度 <= 50% RH 或 < 20% RH\n滞回区间内保持当前转速不变', 11, C.text, { lineSpacingMultiple: 1.4 });
  t(s, 7.2, 3.5, 5.43, 0.4, '转速计算公式', 13, C.secondary, { bold: true });
  s.addShape('rect', { x: 7.2, y: 3.95, w: 5.43, h: 0.7, fill: { color: 'F1F5F9' } });
  t(s, 7.2, 4.0, 5.43, 0.7, 'Speed = Humi_int x 1.5 - 1\n上限：min(Speed, 100)', 13, C.primary, { align: 'center', bold: true });
  t(s, 7.2, 4.85, 5.43, 0.4, '示例：52%RH → 保持（滞回区间内）', 11, C.textLight);
  t(s, 7.2, 5.3, 5.43, 0.4, '示例：55%RH → 55x1.5-1=81档（启动）', 11, C.secondary, { bold: true });
  t(s, 7.2, 5.8, 5.43, 0.4, '无人感应 → 立即停机节能', 11, C.textLight);
  footer(s, 7);
}

// ===== P8 PWM 调速原理 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, 'PWM 精准调速原理', '硬件定时器驱动 · 0-100 级无级调速');

  // 左上：PWM 原理图示
  card(s, 0.5, 1.55, 6.5, 5.0);
  t(s, 0.5, 1.6, 6.5, 0.4, 'TIM2 CH3 PWM 原理', 15, C.primary, { bold: true, align: 'center' });

  // 时序示意：占空比示意
  t(s, 0.7, 2.0, 6.1, 0.35, 'PWM 周期与占空比', 13, C.secondary, { bold: true });
  // 三条 PWM 波形（低占空比）
  s.addShape('line', { x: 0.7, y: 2.6, x2: 6.6, y2: 2.6, line: { color: C.line, width: 1 } });
  // PWM 低占空比
  for (let i = 0; i < 6; i++) {
    s.addShape('rect', { x: 0.7 + i * 0.95, y: 2.5, w: 0.2, h: 0.3, fill: { color: C.primary } });
  }
  t(s, 0.7, 3.0, 6.1, 0.3, '低占空比（20%）→ 低速', 11, C.textLight, { align: 'center' });
  // 中占空比
  s.addShape('line', { x: 0.7, y: 3.8, x2: 6.6, y2: 3.8, line: { color: C.line, width: 1 } });
  for (let i = 0; i < 3; i++) {
    s.addShape('rect', { x: 0.7 + i * 1.9, y: 3.7, w: 0.95, h: 0.3, fill: { color: C.primary } });
  }
  t(s, 0.7, 4.1, 6.1, 0.3, '中占空比（50%）→ 中速', 11, C.textLight, { align: 'center' });
  // 高占空比
  s.addShape('line', { x: 0.7, y: 4.6, x2: 6.6, y2: 4.6, line: { color: C.line, width: 1 } });
  s.addShape('rect', { x: 0.7, y: 4.5, w: 5.9, h: 0.3, fill: { color: C.primary } });
  t(s, 0.7, 5.0, 6.1, 0.3, '高占空比（100%）→ 全速', 11, C.textLight, { align: 'center' });

  // 右侧：技术参数
  card(s, 7.5, 1.55, 5.33, 2.3);
  t(s, 7.5, 1.6, 5.33, 0.4, 'TIM2 PWM 技术参数', 14, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 9.15, y: 2.05, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  const params = [
    { k: '定时器', v: 'TIM2 · 通用定时器' },
    { k: '通道', v: 'CH3 · PA2 引脚' },
    { k: '时钟源', v: '内部时钟 72 MHz' },
    { k: '预分频', v: 'PSC = 35 → 2 MHz 计数' },
    { k: '自动重载', v: 'ARR = 99 → 20 kHz PWM' },
    { k: '分辨率', v: '100 级 (0-99)' }
  ];
  params.forEach((p, i) => {
    t(s, 7.7, 2.2 + i * 0.42, 2.0, 0.4, p.k, 12, C.secondary, { bold: true });
    t(s, 9.7, 2.2 + i * 0.42, 3.13, 0.4, p.v, 12, C.text);
  });

  // 右下：正反转
  card(s, 7.5, 4.2, 5.33, 2.35);
  t(s, 7.5, 4.3, 5.33, 0.4, '电机正反转控制', 14, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 9.15, y: 4.75, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  t(s, 7.7, 5.0, 5.0, 0.4, '正转：AIN1=1, AIN2=0 → PWM 驱动', 12, C.text);
  t(s, 7.7, 5.4, 5.0, 0.4, '反转：AIN1=0, AIN2=1 → PWM 驱动反向', 12, C.text);
  t(s, 7.7, 5.8, 5.0, 0.4, '停止：PWM=0 → 电机停机', 12, C.text);
  footer(s, 8);
}

// ===== P9 传感器数据采集 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '多传感器数据采集', 'DHT11 · 人体 · 光敏 · 热敏 · 转速反馈');

  // DHT11
  card(s, 0.5, 1.55, 3.95, 5.0);
  t(s, 0.5, 1.6, 3.95, 0.4, 'DHT11 温湿度', 15, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 1.95, y: 2.05, w: 1.0, h: 0.02, fill: { color: C.secondary } });
  t(s, 0.7, 2.3, 3.55, 0.4, '通信协议：单总线 (One-Wire', 12, C.text);
  t(s, 0.7, 2.7, 3.55, 0.4, '数据格式：40bit = 湿度整 + 湿度小 + 温度整 + 温度小 + 校验和', 12, C.text, { lineSpacingMultiple: 1.3 });
  t(s, 0.7, 3.5, 3.55, 0.4, '通信时序：起始 → 响应 → 数据读取', 12, C.text);
  t(s, 0.7, 4.1, 3.55, 0.4, '精度：±2°C / ±5% RH', 12, C.text);
  t(s, 0.7, 4.5, 3.55, 0.4, '采样周期：1 秒/次', 12, C.textLight);

  // 人体感应
  card(s, 4.65, 1.55, 3.95, 5.0);
  t(s, 4.65, 1.6, 3.95, 0.4, 'HC-SR505 人体红外', 15, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 6.15, y: 2.05, w: 1.0, h: 0.02, fill: { color: C.secondary } });
  t(s, 4.85, 2.3, 3.55, 0.4, '工作原理：被动红外 PIR', 12, C.text);
  t(s, 4.85, 2.7, 3.55, 0.4, '检测范围：≤ 3 米 · 120°', 12, C.text);
  t(s, 4.85, 3.1, 3.55, 0.4, '输出：数字信号 (0/1)', 12, C.text);
  t(s, 4.85, 3.5, 3.55, 0.4, '应用：有人 → 开启风扇', 12, C.text);
  t(s, 4.85, 3.9, 3.55, 0.4, '无人 → 停止节能', 12, C.textLight);
  t(s, 4.85, 4.3, 3.55, 0.4, '防误触发：延迟时间可调', 12, C.textLight);

  // ADC 光敏/热敏/测速
  card(s, 8.8, 1.55, 4.03, 5.0);
  t(s, 8.8, 1.6, 4.03, 0.4, 'ADC 多通道采集', 15, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 10.3, y: 2.05, w: 1.0, h: 0.02, fill: { color: C.secondary } });
  t(s, 9.0, 2.3, 3.63, 0.4, '光敏电阻：光照强度', 12, C.text);
  t(s, 9.0, 2.7, 3.63, 0.4, '热敏电阻：环境温度', 12, C.text);
  t(s, 9.0, 3.1, 3.63, 0.4, '转速反馈：实际 RPM', 12, C.text);
  t(s, 9.0, 3.5, 3.63, 0.4, 'ADC 分辨率：12 位 (0-4095', 12, C.textLight);
  t(s, 9.0, 3.9, 3.63, 0.4, '采样频率：1 Hz', 12, C.textLight);
  t(s, 9.0, 4.3, 3.63, 0.4, '数据刷新：OLED 实时显示', 12, C.textLight);
  t(s, 9.0, 4.7, 3.63, 0.4, '应用：传感器数据页显示', 12, C.textLight);
  footer(s, 9);
}

// ===== P10 定时器与中断系统 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '定时器与中断系统', '精准定时 · 编码器中断');

  // TIM3 定时卡
  card(s, 0.5, 1.55, 6.0, 5.0);
  t(s, 0.5, 1.6, 6.0, 0.4, 'TIM3 定时倒计时', 15, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 2.5, y: 2.05, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  t(s, 0.7, 2.3, 5.6, 0.4, '工作模式：TIM3 作为时基定时器', 13, C.secondary, { bold: true });
  t(s, 0.7, 2.8, 5.6, 0.4, 'PSC = 7200-1 → 10 kHz 计数', 12, C.text);
  t(s, 0.7, 3.2, 5.6, 0.4, 'ARR = 10000-1 → 1 Hz 中断', 12, C.text);
  t(s, 0.7, 3.6, 5.6, 0.4, '中断周期：1 秒/次', 12, C.text);
  t(s, 0.7, 4.0, 5.6, 0.4, '定时倒计时逻辑：', 13, C.secondary, { bold: true });
  t(s, 0.7, 4.4, 5.6, 0.4, 'Sec-- → 若 Sec<0 → Min-- → Sec=59', 12, C.text);
  t(s, 0.7, 4.8, 5.6, 0.4, '全部为 0 → 停止电机，转速=0', 12, C.text);

  // EXTI 编码器中断
  card(s, 7.0, 1.55, 5.83, 5.0);
  t(s, 7.0, 1.6, 5.83, 0.4, '旋转编码器 EXTI 中断', 15, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 9.0, y: 2.05, w: 2.0, h: 0.03, fill: { color: C.secondary } });
  t(s, 7.2, 2.3, 5.43, 0.4, '两相脉冲：A 相触发中断，B 相判向', 13, C.secondary, { bold: true });
  t(s, 7.2, 2.8, 5.43, 0.4, '正转：A 相下降沿 → B 相=1', 12, C.text);
  t(s, 7.2, 3.2, 5.43, 0.4, '反转：A 相下降沿 → B 相=0', 12, C.text);
  t(s, 7.2, 3.6, 5.43, 0.4, '分辨率：每格 ±1 转速单位', 12, C.text);
  t(s, 7.2, 4.0, 5.43, 0.4, '按键中断：编码器按键中断', 13, C.secondary, { bold: true });
  t(s, 7.2, 4.4, 5.43, 0.4, '按下锁定旋钮，防止误触', 12, C.text);
  footer(s, 10);
}

// ===== P11 软件工作流程 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '主程序工作流程', '开机初始化 → 循环调度 → 响应');

  const flow = [
    { t: '系统初始化', s: 'STM32 时钟 · GPIO · TIM2 · TIM3 · OLED · DHT11', hi: true },
    { t: '按键扫描', s: 'Key_GetNum() 获取按键键码' },
    { t: '菜单显示', s: '根据 Menu 变量显示对应页面' },
    { t: '指针反色', s: '当前选中项反色显示' },
    { t: '传感器更新', s: '1 秒/次 · 温湿度 · 光敏 · 热敏 · 转速' },
    { t: 'OLED 刷新', s: 'OLED_Update() 更新显存到屏幕' }
  ];
  flow.forEach((f, i) => {
    const y = 1.55 + i * 0.85;
    s.addShape('rect', { x: 0.5, y: y, w: 12.33, h: 0.75, fill: { color: f.hi ? C.secondary : 'F1F5F9' }, line: { color: C.line, width: 0.75 } });
    t(s, 0.7, y + 0.1, 2.5, 0.5, String(i + 1), 14, f.hi ? 'FFFFFF' : C.primary, { bold: true });
    t(s, 3.2, y + 0.1, 3.0, 0.5, f.t, 14, f.hi ? 'FFFFFF' : C.primary, { bold: true });
    t(s, 6.2, y + 0.1, 6.33, 0.5, f.s, 12, f.hi ? 'E8ECF4' : C.textLight);
  });
  t(s, 0.5, 7.0, 12.33, 0.3, '主循环每秒执行：传感器数据更新 → 菜单判断 → 输出决策 → OLED 刷新', 13, C.primary, { align: 'center', bold: true });
  footer(s, 11);
}

// ===== P12 关键代码架构 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '核心代码架构', '模块化 · 可读性强');

  // 代码模块
  const mods = [
    { f: 'main.c', c: '主程序入口 · 菜单调度 · 控制算法', d: 'Menu_Key() / Menu_Show() / Motor_SetSpeed()' },
    { f: 'DHT11.c', c: '温湿度驱动', d: 'DHT11_Init() · DHT11_Read() · 微秒级延时' },
    { f: 'OLED.c', c: '0.96寸 OLED 驱动 · 中文字库', d: 'OLED_ShowChinese() · OLED_Printf() · OLED_ReverseArea()' },
    { f: 'Key.c', c: '按键扫描 + 编码器中断处理', d: 'Key_GetNum() · Encoder_Get() · 消抖处理' },
    { f: 'tim.c', c: 'TIM2 PWM · TIM3 定时中断', d: 'HAL_TIM_PeriodElapsedCallback()' },
    { f: 'adc.c', c: 'ADC 多通道采样', d: '光敏 · 热敏 · 转速反馈' },
    { f: 'speed.c', c: '转速计算与反馈', d: 'Speed_Init() · Get_Speed_RPM()' },
    { f: 'gpio.c', c: 'GPIO 初始化配置', d: 'AIN1/AIN2 方向控制 · 感应输入' }
  ];
  mods.forEach((m, i) => {
    const x = 0.5 + (i % 2) * 6.15;
    const y = 1.55 + Math.floor(i / 2) * 1.35;
    card(s, x, y, 5.85, 1.15);
    t(s, x + 0.15, y + 0.15, 5.55, 0.4, m.f, 14, C.secondary, { bold: true });
    t(s, x + 0.15, y + 0.55, 5.55, 0.3, m.c, 12, C.primary, { bold: true });
    t(s, x + 0.15, y + 0.85, 5.55, 0.3, m.d, 11, C.textLight);
  });
  t(s, 0.5, 7.0, 12.33, 0.3, '模块化设计便于功能扩展与维护', 13, C.primary, { align: 'center', bold: true });
  footer(s, 12);
}

// ===== P13 功能测试与数据 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '功能测试与性能数据', '真实场景验证');

  const tests = [
    { t: '定时模式', data: [
      '设置 00:00:30 · 转速 50 → 运行 30 秒后自动停机',
      '倒计时精度：±1 秒/小时',
      'OLED 正确显示剩余时间与实时转速'
    ]},
    { t: '手动模式', data: [
      '编码器旋转平滑调速 0→100→0 无级调速',
      '旋钮锁定 / 解锁响应时间：<50 ms',
      '按键按下锁定后，编码器无效'
    ]},
    { t: '自动-温度控制', data: [
      '温度 25°C → 计算转速 = 63 档（实测相符）',
      '温度 15°C 以下 → 转速 = 0（温度过低保护',
      '无人时立即停机节能'
    ]},
    { t: '自动-湿度控制', data: [
      '湿度 60% RH → 计算转速 = 89 档（实测相符）',
      '湿度 20% 以下 → 转速 = 0（湿度低保护',
      '人体感应灵敏，无人停机'
    ]},
    { t: '传感器数据页', data: [
      '光照 / 热敏 / RPM 实时刷新',
      'OLED 中文显示清晰',
      '数据更新 1 秒/次'
    ]}
  ];
  tests.forEach((ts, i) => {
    const x = 0.5 + (i % 2) * 6.15;
    const y = 1.55 + Math.floor(i / 2) * 1.8;
    card(s, x, y, 5.85, 1.5);
    t(s, x + 0.15, y + 0.15, 5.55, 0.4, ts.t, 14, C.primary, { bold: true });
    s.addShape('rect', { x: x + 0.15, y: y + 0.55, w: 0.8, h: 0.02, fill: { color: C.secondary } });
    ts.data.forEach((d, j) => {
      t(s, x + 0.15, y + 0.65 + j * 0.3, 5.55, 0.3, '▸ ' + d, 11, C.textLight);
    });
  });
  footer(s, 13);
}

// ===== P14 项目特色与创新点 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgLight };
  titleBar(s, '项目特色与创新', '从传统风扇到智能系统的升级');

  const inno = [
    { n: '01', t: '四模式融合', d: '定时/手动/自动/测速四种工作模式，覆盖日常生活全场景，用户可灵活切换' },
    { n: '02', t: '滞回保护算法', d: '温度/湿度控制带滞回区间（启动/关闭阈值分离），防止临界点频繁启停，保护电机延长寿命' },
    { n: '03', t: 'OLED 中文菜单', d: '0.96 寸 I2C OLED，多级中文菜单，反色指针导航，操作直观友好' },
    { n: '04', t: '实时RPM测速反馈', d: '测速模式显示目标转速与实际RPM，旋钮锁定防止误触，可观测电机负载特性' },
    { n: '05', t: 'PWM 精准调速', d: 'TIM2 硬件 PWM，0-100 级精准调速，正反转双向控制，支持速度曲线可视化' },
    { n: '06', t: '人体感应节能', d: 'HC-SR505 人体感应，无人自动停机，有人恢复运转，节能环保' }
  ];
  inno.forEach((it, i) => {
    const x = 0.5 + (i % 3) * 4.15;
    const y = 1.55 + Math.floor(i / 3) * 2.7;
    card(s, x, y, 3.95, 2.5);
    t(s, x, y + 0.1, 3.95, 0.35, it.n, 16, C.secondary, { align: 'center', bold: true });
    t(s, x, y + 0.5, 3.95, 0.55, it.t, 18, C.primary, { align: 'center', bold: true });
    s.addShape('rect', { x: x + 1.65, y: y + 1.15, w: 0.65, h: 0.02, fill: { color: C.secondary } });
    t(s, x + 0.2, y + 1.35, 3.55, 1.0, it.d, 12, C.textLight, { align: 'center', lineSpacingMultiple: 1.4 });
  });
  footer(s, 14);
}

// ===== P15 总结与展望 =====
{
  const s = pptx.addSlide();
  s.background = { color: C.bgDark };
  t(s, 0.5, 1.5, 12.33, 1.0, '总结与未来展望', 44, 'FFFFFF', { align: 'center', bold: true });
  s.addShape('rect', { x: 5.7, y: 2.55, w: 2.0, h: 0.03, fill: { color: C.secondary } });

  // 总结
  card(s, 0.5, 3.0, 6.0, 3.5);
  t(s, 0.5, 3.1, 6.0, 0.4, '项目成果', 16, C.primary, { align: 'center', bold: true });
  s.addShape('rect', { x: 2.5, y: 3.5, w: 2.0, h: 0.02, fill: { color: C.secondary } });
  const sums = [
    '基于 STM32 的多模式智能风扇',
    'OLED 中文菜单，操作直观友好',
    '多传感器融合（DHT11 + 人体 + ADC）',
    'PWM 精准调速，0-100 级无级调速',
    '定时/手动/自动三大模式',
    '模块化代码，便于扩展维护'
  ];
  sums.forEach((s2, i) => {
    t(s, 0.7, 3.7 + i * 0.45, 5.6, 0.4, '▸ ' + s2, 12, C.text);
  });

  // 展望
  card(s, 7.0, 3.0, 5.83, 3.5);
  t(s, 7.0, 3.1, 5.83, 0.4, '未来扩展', 16, C.secondary, { align: 'center', bold: true });
  s.addShape('rect', { x: 9.0, y: 3.5, w: 2.0, h: 0.02, fill: { color: C.secondary } });
  const future = [
    'WiFi / 蓝牙远程控制（APP 互联',
    '语音控制（语音指令识别）',
    'LCD 彩屏升级，更丰富的 UI 交互',
    '多种风速曲线智能学习用户习惯',
    '历史数据记录与分析',
    '多机组网控制（全屋智能风道系统'
  ];
  future.forEach((f, i) => {
    t(s, 7.2, 3.7 + i * 0.45, 5.43, 0.4, '▸ ' + f, 12, C.text);
  });
  t(s, 0.5, 6.8, 12.33, 0.3, 'Smart_Fan v2.3：从一个风扇，到一个可以思考的智能伙伴', 14, '8E9AAF', { align: 'center', bold: true });
  footer(s, 15);
}

// ===== 生成文件 =====
pptx.writeFile({ fileName: 'Smart_Fan_v2.3_答辩.pptx' });
console.log('PPT 生成完成：Smart_Fan_v2.3_答辩.pptx');
