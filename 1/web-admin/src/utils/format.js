export const TYPE_MAP = {
  red_light: '闯红灯',
  no_helmet: '未戴头盔',
  wrong_way: '逆行',
  illegal_parking: '违规停车',
  lane_departure: '压线行驶',
  speeding: '超速'
}

export const STATUS_MAP = {
  pending: '待审核',
  confirmed: '已确认',
  rejected: '已驳回'
}

export const TYPE_COLORS = {
  red_light: '#ff4d4f',
  no_helmet: '#fa8c16',
  wrong_way: '#722ed1',
  illegal_parking: '#eb2f96',
  lane_departure: '#13c2c2',
  speeding: '#f5222d'
}

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

export function getTypeName(type) {
  return TYPE_MAP[type] || type
}

export function getStatusName(status) {
  return STATUS_MAP[status] || status
}

export function getTypeColor(type) {
  return TYPE_COLORS[type] || '#999'
}

export function getStatusColor(status) {
  return STATUS_COLORS[status] || 'info'
}