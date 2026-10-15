// 核实候选开源项目的真实性与活跃度（git ls-remote，不 clone）
const { execFileSync } = require('child_process');

const REPOS = [
  ['beita6969/-', '智能车牌识别管理系统（YOLOv8x+YOLOv11+HyperLPR3+EasyOCR）'],
  ['maruthisaiteja/smart-traffic-violation-detection-using-YOLOv8', 'YOLOv8 违规检测（未戴头盔/闯红灯）'],
  ['szad670401/HyperLPR', 'HyperLPR 中文车牌识别框架'],
  ['sirius-ai/LPRNet_Pytorch', 'LPRNet 轻量车牌识别（PyTorch）'],
  ['we0091234/Chinese_license_plate_detection_recognition', '中文车牌检测识别（YOLO 系列）'],
  ['ultralytics/ultralytics', 'YOLO 官方（对照基线）'],
];

for (const [repo, desc] of REPOS) {
  let head = null, err = '';
  try {
    head = execFileSync('git', ['ls-remote', `https://github.com/${repo}.git`, 'HEAD'],
      { encoding: 'utf8', timeout: 30000 }).split(/\s+/)[0];
  } catch (e) { err = String(e.message).slice(0, 60); }
  console.log(`\n=== ${repo}`);
  console.log(`    用途: ${desc}`);
  console.log(`    HEAD: ${head || '(不可达 / 不存在)'} ${err ? '  err=' + err : ''}`);
}
