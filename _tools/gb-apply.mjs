import fs from 'node:fs';
const D = 'C:/Users/ROG/AppData/Local/GlassBoard';
const P = D + '/layout.json';
const j = JSON.parse(fs.readFileSync(P, 'utf8'));

// 桌面 38 个快捷方式 → 分组映射（按用途）
const PLAN = {
  'AI/开发': ['CC Switch','ChatGPT','Claude','DeepSeek Harness','Qoder CN IDE','Qoder CN','Trae CN','Visual Studio Code','WebCodex Desktop','GitHub Desktop','GitHub','Cloudflare','draw.io','Notion','Ollama'],
  '工程/单片机': ['CanMV IDE K230','Proteus 8 Professional','Configure Virtual Serial Port Driver'],
  '游戏': ['和平精英模拟器','崩坏：星穹铁道','米哈游启动器','雷电模拟器9','雷电多开器','STOVE','Plain Craft Launcher 2','无畏契约WeGame版'],
  '影音/社交': ['抖音','Mineradio','迅雷','百度网盘'],
  '系统工具': ['电源-平衡模式','电源-高性能模式','Radmin.exe','DroidCamApp'],
  '办公': ['WPS Office','Microsoft Edge'],
};

const groupOf = {};
for (const [g, names] of Object.entries(PLAN)) for (const n of names) groupOf[n] = g;

// 新增的 10 个（GlassBoard 扫描开始菜单时漏掉的桌面项）
const NEW = [
  {Name:'CC Switch', Path:'C:\\Users\\ROG\\Desktop\\CC Switch.lnk', LaunchTarget:'F:\\AI\\CC-Switch\\cc-switch.exe', LaunchArguments:''},
  {Name:'ChatGPT', Path:'C:\\Users\\ROG\\Desktop\\ChatGPT.lnk', LaunchTarget:'C:\\Windows\\explorer.exe', LaunchArguments:'shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App'},
  {Name:'Cloudflare', Path:'C:\\Users\\ROG\\Desktop\\Cloudflare.lnk', LaunchTarget:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge_proxy.exe', LaunchArguments:' --profile-directory=Default --app-id=kbdhpemeclgiggljbfcmlnmibnmolaih --app-url=https://dash.cloudflare.com/ --app-launch-source=4'},
  {Name:'draw.io', Path:'C:\\Users\\ROG\\Desktop\\draw.io.lnk', LaunchTarget:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge_proxy.exe', LaunchArguments:' --profile-directory=Default --app-id=ilmgmogedobmcfegdjcibiiaodmdenpf --app-url=https://app.diagrams.net/index.html --app-launch-source=4'},
  {Name:'DroidCamApp', Path:'C:\\Users\\ROG\\Desktop\\DroidCamApp.lnk', LaunchTarget:'C:\\Program Files (x86)\\DroidCam\\DroidCamApp.exe', LaunchArguments:''},
  {Name:'Plain Craft Launcher 2', Path:'C:\\Users\\ROG\\Desktop\\Plain Craft Launcher 2.lnk', LaunchTarget:'F:\\MC\\PCL 下载\\Plain Craft Launcher 2.exe', LaunchArguments:''},
  {Name:'Radmin.exe', Path:'C:\\Users\\ROG\\Desktop\\Radmin.exe.lnk', LaunchTarget:'D:\\Radmin.exe', LaunchArguments:''},
  {Name:'无畏契约WeGame版', Path:'C:\\Users\\ROG\\Desktop\\无畏契约WeGame版.lnk', LaunchTarget:'E:\\WeGameApps\\rail_apps\\无畏契约(2001715)\\WeGameLauncher\\launcher.exe', LaunchArguments:''},
  {Name:'电源-平衡模式', Path:'C:\\Users\\ROG\\Desktop\\电源-平衡模式.lnk', LaunchTarget:'C:\\Windows\\system32\\powercfg.exe', LaunchArguments:'/setactive 381b4222-f694-41f0-9685-ff5bb260df2e'},
  {Name:'电源-高性能模式', Path:'C:\\Users\\ROG\\Desktop\\电源-高性能模式.lnk', LaunchTarget:'C:\\Windows\\system32\\powercfg.exe', LaunchArguments:'/setactive 6fecc5ae-f350-48a5-b669-b472cb895ccf'},
];

let added = 0, regrouped = 0;
for (const n of NEW) {
  if (!j.Apps.some(a => (a.Name||'') === n.Name)) {
    j.Apps.push({ Group: groupOf[n.Name] || '', LaunchArguments: n.LaunchArguments, LaunchTarget: n.LaunchTarget, Name: n.Name, Path: n.Path, Pinned: true, ProductInfo: '' });
    added++;
  }
}

// 让 38 个桌面项全部归组 + 固定
const deskSet = new Set(Object.keys(groupOf));
for (const a of j.Apps) {
  const nm = a.Name || '';
  if (deskSet.has(nm)) {
    if (a.Group !== groupOf[nm]) regrouped++;
    a.Group = groupOf[nm];
    a.Pinned = true;
  }
}

// 补全新分组名
const needGroups = Object.keys(PLAN);
for (const g of needGroups) if (!j.Groups.includes(g)) j.Groups.push(g);

// Dock：桌面 38 项按组顺序排在最前
const byName = {};
for (const a of j.Apps) byName[a.Name] = a;
const dockOrder = [];
for (const g of needGroups) for (const n of PLAN[g]) { if (byName[n]) dockOrder.push(byName[n].Path); }
// 保留原有 Dock 项（去重）
for (const p of (j.DockOrder || [])) if (!dockOrder.includes(p)) dockOrder.push(p);
j.DockOrder = dockOrder.slice(0, 60);

j.SaveRevision = (j.SaveRevision || 0) + 1;
fs.writeFileSync(P, JSON.stringify(j, null, 1), 'utf8');

console.log('新增 Apps: ' + added);
console.log('重新归组: ' + regrouped);
console.log('Groups 现在: ' + JSON.stringify(j.Groups));
console.log('DockOrder 长度: ' + j.DockOrder.length);
console.log('Apps 总数: ' + j.Apps.length);
const c = {}; for (const a of j.Apps) { const g = a.Group || '(未分组)'; c[g]=(c[g]||0)+1; }
console.log('分组分布: ' + Object.entries(c).sort((a,b)=>b[1]-a[1]).map(([k,v])=>k+'='+v).join('  '));