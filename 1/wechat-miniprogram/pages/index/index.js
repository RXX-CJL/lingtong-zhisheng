// pages/index/index.js
const app = getApp();
const api = require('../../utils/api.js');
const { getMyStats } = require('../../utils/format.js');

Page({
  data: {
    stats: null,
    loading: false
  },

  onLoad(options) {
    console.log('首页加载');
  },

  onShow() {
    // 每次显示页面时刷新统计数据
    this.loadMyStats();
  },

  onPullDownRefresh() {
    this.loadMyStats();
  },

  /**
   * 加载我的统计数据
   */
  loadMyStats() {
    const openid = app.globalData.openid;
    api.getMyStats(openid).then(res => {
      this.setData({ stats: res });
    }).catch(err => {
      console.error('获取统计失败', err);
      // 兜底显示空数据
      this.setData({
        stats: { total: 0, confirmed: 0, pending: 0 }
      });
    });
  },

  /**
   * 跳转至提交页面
   */
  goToSubmit() {
    wx.navigateTo({
      url: '/pages/submit/submit'
    });
  },

  /**
   * 跳转至我的记录列表
   */
  goToList() {
    wx.switchTab({
      url: '/pages/list/list'
    });
  },

  /**
   * 跳转至全局统计页面
   */
  goToStatistics() {
    wx.switchTab({
      url: '/pages/statistics/statistics'
    });
  }
});