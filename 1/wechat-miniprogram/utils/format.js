/**
 * 格式化工具函数
 */

// 违规类型映射
const TYPE_MAP = {
  red_light: '闯红灯',
  no_helmet: '未戴头盔',
  wrong_way: '逆行',
  illegal_parking: '违规停车',
  lane_departure: '压线行驶',
  speeding: '超速'
};

// 状态映射
const STATUS_MAP = {
  pending: '待审核',
  confirmed: '已确认',
  rejected: '已驳回'
};

/**
 * 格式化日期
 * @param {string} isoString ISO格式日期字符串
 * @returns {string} 格式化后的日期 "YYYY-MM-DD HH:mm"
 */
function formatDate(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

/**
 * 格式化置信度
 * @param {number} confidence 置信度 (0-1)
 * @returns {string} 百分比字符串 "85%"
 */
function formatPercent(confidence) {
  if (confidence === null || confidence === undefined) return '';
  return Math.round(confidence * 100) + '%';
}

/**
 * 获取违规类型中文名称
 * @param {string} type 违规类型英文标识
 * @returns {string} 中文名称
 */
function getTypeName(type) {
  return TYPE_MAP[type] || type;
}

/**
 * 获取状态中文名称
 * @param {string} status 状态英文标识
 * @returns {string} 中文名称
 */
function getStatusName(status) {
  return STATUS_MAP[status] || status;
}

/**
 * 获取违规类型列表
 * @returns {Array} 违规类型数组
 */
function getTypeList() {
  return Object.entries(TYPE_MAP).map(([value, label]) => ({
    value,
    label
  }));
}

/**
 * 获取状态列表
 * @returns {Array} 状态数组
 */
function getStatusList() {
  return Object.entries(STATUS_MAP).map(([value, label]) => ({
    value,
    label
  }));
}

module.exports = {
  TYPE_MAP,
  STATUS_MAP,
  formatDate,
  formatPercent,
  getTypeName,
  getStatusName,
  getTypeList,
  getStatusList
};