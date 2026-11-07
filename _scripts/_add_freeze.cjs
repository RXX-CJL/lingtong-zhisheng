const fs = require('fs');
const P = 'C:/Users/ROG/.dsh/task-board/ledger-v2.json';
const d = JSON.parse(fs.readFileSync(P,'utf8'));
const t = d.tasks.find(x => x.title.includes('违停'));
if (!t) { console.log('未找到违停卡'); process.exit(1); }
t.freeze = {
  goal: '产出「违停」交通违法仿真视频，存到 E:\\output\\1\\carla\\仿真输出\\违停.mp4',
  progress: '尚未开始。',
  next: '①读 E:\\output\\_carla_workshop_batch4_env_verdict.md 了解工坊能力；②参考 E:\\output\\recipes\\闯红灯演示.json 写剧本；③跑 --selftest 再 --recipe 出片；④用 cv2 断言时长误差<1秒'
};
t.handover = {
  references: [
    'E:\\output\\recipes\\闯红灯演示.json',
    'E:\\output\\1\\carla\\CARLA_0.9.16\\PythonAPI\\examples\\carla_creator_workshop.py',
    'E:\\output\\_carla_workshop_ai_verdict.md'
  ],
  bundledAt: Date.now()
};
d.revision = (d.revision||0) + 1;
fs.writeFileSync(P, JSON.stringify(d, null, 2), 'utf8');
console.log('已写入 freeze + handover，revision ->', d.revision);
console.log(JSON.stringify({freeze: t.freeze, handover: t.handover}, null, 1).slice(0,600));