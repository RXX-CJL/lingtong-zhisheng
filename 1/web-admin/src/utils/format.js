// 违规类型中文名 —— 全站唯一来源（2026-10-23 由 DSH 补全 6 -> 11 类）
// 依据：api/behavior_engine.py:50-59 BEHAVIOR_TYPE_CN(8)
//     + api/rule_engine/plugins/traffic_plugin.py:41-52 TRAFFIC_TYPE_CN(9, 独有 no_helmet)
//     + urban_management_plugin.py:289 street_stall / public_security_plugin.py:284 crowd_gathering
// 任何新增违规类型必须先登记到这里，否则界面会落到「未知类型」兜底
export const TYPE_MAP = {
  red_light: '闯红灯',
  wrong_way: '逆行',
  illegal_parking: '违规停车',
  lane_departure: '压线行驶',
  speeding: '超速',
  running_yellow: '抢黄灯',
  illegal_turn: '违规掉头',
  pedestrian_crossing: '未礼让行人',
  no_helmet: '未戴头盔',
  street_stall: '疑似占道经营',
  crowd_gathering: '人员聚集',
  // 历史别名：EventDetail 旧补丁用的是少个 "er" 的拼写，EventDetail.vue:612 已删。
  // 保留别名只为兼容可能存在的历史记录，新增代码一律用 illegal_parking。
  illegal_park: '违规停车'
}

export const STATUS_MAP = {
  pending: '待审核',
  confirmed: '已确认',
  rejected: '已驳回'
}

// 违规类型语义色（2026-10-23 由 DSH 统一）
// 结构逻辑：暖色 = 动态危险驾驶，冷色 = 静态/轻微违法 —— 颜色本身即严重度线索
// base: _ui_optimization_verdict.md §2.4（7 类，经三模型评审）
export const TYPE_COLORS = {
  red_light: '#D14343',            // 信号红，全站唯一正红
  speeding: '#ED7D31',             // 警示橙，动态高危
  running_yellow: '#F2C14E',       // 黄灯语义
  wrong_way: '#9B5DE5',            // 紫，严重但与暖色区分
  no_helmet: '#2E9E8F',            // 青绿（慎用正绿，避免"合规"误读）
  illegal_parking: '#5B8DB8',      // 蓝灰，静态低紧急
  lane_departure: '#98A2B3',       // 中性灰，轻微违法
  // ↓ 以下 4 类为 §2.4 未覆盖、按同一逻辑补齐的扩展色
  illegal_turn: '#C2600A',         // 深琥珀：动态危险，明度与超速橙拉开
  pedestrian_crossing: '#B5477E',  // 品红：对人风险，全站唯一品红
  street_stall: '#7A8CA3',         // 深蓝灰：静态
  crowd_gathering: '#4C7A9E',      // 蓝青：群体但非直接违法
  illegal_park: '#5B8DB8'          // 历史别名，与 illegal_parking 同色
}

// 未登记类型专用兜底灰（真实类目禁用此色）
export const TYPE_FALLBACK_COLOR = '#C0C4CC'
export const TYPE_FALLBACK_NAME = '未知类型'

export const STATUS_COLORS = {
  pending: 'warning',
  confirmed: 'success',
  rejected: 'info'
}

export function formatDate(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

export function formatPercent(value) {
  if (value === null || value === undefined) return '-'
  return Math.round(value * 100) + '%'
}

// 违规类型 → 中文名。未登记一律「未知类型」+ 告警，绝不把英文 key 透给界面
export function getTypeName(type) {
  if (!type) return '-'
  const name = TYPE_MAP[type]
  if (name) return name
  console.warn('[format] 未登记的违规类型，已用兜底文案：', type)
  return TYPE_FALLBACK_NAME
}

export function getStatusName(status) {
  return STATUS_MAP[status] || status
}

// 违规类型 → 语义色。未登记用兜底灰（不发告警，避免与 getTypeName 重复刷屏）
export function getTypeColor(type) {
  return TYPE_COLORS[type] || TYPE_FALLBACK_COLOR
}

export function getStatusColor(status) {
  return STATUS_COLORS[status] || 'info'
}