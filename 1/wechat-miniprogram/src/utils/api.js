/**
 * API 请求封装
 * 统一处理 baseURL、错误处理、loading 等
 */

const app = getApp();

/**
 * 基础请求方法
 * @param {Object} options 请求配置
 * @returns {Promise} 请求结果
 */
function request(options) {
  return new Promise((resolve, reject) => {
    const { baseUrl = app.globalData.baseUrl } = app.globalData;
    const url = options.url.startsWith('http') ? options.url : baseUrl + options.url;

    wx.showLoading({
      title: options.loading !== false ? '加载中...' : '',
      mask: true
    });

    wx.request({
      url: url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...options.header
      },
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          // 处理业务错误
          const errorMsg = res.data?.message || `请求失败 (${res.statusCode})`;
          wx.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 2000
          });
          reject(new Error(errorMsg));
        }
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({
          title: '网络连接失败',
          icon: 'none',
          duration: 2000
        });
        reject(err);
      }
    });
  });
}

/**
 * 提交违规记录
 * @param {string} openid 用户openid
 * @param {Object} violationData 违规数据
 * @param {Array} imagesBase64 图片base64数组
 * @returns {Promise}
 */
function submitViolation(openid, violationData, imagesBase64) {
  const now = new Date();
  const pad = (n) => (n < 10 ? '0' + n : '' + n);
  const timestamp =
    now.getFullYear() +
    '-' + pad(now.getMonth() + 1) +
    '-' + pad(now.getDate()) +
    'T' + pad(now.getHours()) +
    ':' + pad(now.getMinutes()) +
    ':' + pad(now.getSeconds());

  // imagesBase64 可能是数组也可能是单张，这里取第一张作为主图
  let imageData = '';
  if (Array.isArray(imagesBase64) && imagesBase64.length > 0) {
    imageData = imagesBase64[0];
  } else if (typeof imagesBase64 === 'string') {
    imageData = imagesBase64;
  }

  return request({
    url: '/api/wechat/violation/submit',
    method: 'POST',
    data: {
      openid: openid,
      violation_data: {
        violation_type: violationData.violation_type || 'lane_departure',
        track_id: violationData.track_id || Date.now() % 10000,
        confidence: violationData.confidence || 0.95,
        position: violationData.position || { x: 0, y: 0, width: 100, height: 100 },
        timestamp: violationData.timestamp || timestamp,
        image_data: imageData,
        additional_info: {
          remark: violationData.remark || '',
          source: 'wechat_miniprogram'
        }
      },
      device_info: {
        platform: 'wechat',
        version: '1.0.0'
      }
    }
  });
}

/**
 * 获取我的违规记录列表
 * @param {string} openid 用户openid
 * @param {number} page 页码
 * @param {number} pageSize 每页数量
 * @param {string} violationType 违规类型筛选
 * @param {string} status 状态筛选
 * @returns {Promise}
 */
function getMyList(openid, page = 1, pageSize = 10, violationType = '', status = '') {
  let url = `/api/wechat/violation/list?openid=${openid}&page=${page}&page_size=${pageSize}`;
  if (violationType) {
    url += `&violation_type=${violationType}`;
  }
  if (status) {
    url += `&status=${status}`;
  }
  return request({
    url: url,
    method: 'GET',
    loading: false
  });
}

/**
 * 获取我的违规记录详情
 * @param {string} openid 用户openid
 * @param {number} id 记录ID
 * @returns {Promise}
 */
function getMyDetail(openid, id) {
  return request({
    url: `/api/wechat/violation/${id}?openid=${openid}`,
    method: 'GET',
    loading: false
  });
}

/**
 * 获取我的统计信息
 * @param {string} openid 用户openid
 * @returns {Promise}
 */
function getMyStats(openid) {
  return request({
    url: `/api/wechat/statistics/my?openid=${openid}`,
    method: 'GET',
    loading: false
  });
}

/**
 * 获取全局统计信息
 * @returns {Promise}
 */
function getGlobalStats() {
  return request({
    url: '/api/violations/statistics/summary',
    method: 'GET',
    loading: false
  });
}

/**
 * 获取完整的图片URL
 * @param {string} imagePath 服务器返回的图片路径
 * @returns {string} 完整的图片URL
 */
function getImageUrl(imagePath) {
  if (!imagePath) return '';
  if (imagePath.startsWith('http')) return imagePath;
  const { baseUrl } = app.globalData;
  // uploads/xxx.jpg -> baseUrl + '/' + uploads/xxx.jpg
  return baseUrl + '/' + imagePath;
}

module.exports = {
  request,
  submitViolation,
  getMyList,
  getMyDetail,
  getMyStats,
  getGlobalStats,
  getImageUrl
};