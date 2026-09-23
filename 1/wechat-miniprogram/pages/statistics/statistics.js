// pages/statistics/statistics.js
const app = getApp();
const api = require('../../utils/api.js');
const { getTypeName, getStatusName } = require('../../utils/format.js');

Page({
  data: {
    stats: {},
    typeStats: [],
    myRank: null,
    loading: true
  },

  onLoad(options) {
    console.log('统计页加载');
  },

  onShow() {
    this.loadGlobalStats();
  },

  onPullDownRefresh() {
    this.loadGlobalStats();
  },

  /**
   * 加载全局统计数据
   */
  loadGlobalStats() {
    this.setData({ loading: true });

    api.getGlobalStats()
      .then(res => {
        console.log('全局统计', res);

        // 处理统计数据
        const stats = {
          total: res.total || 0,
          today: res.today || 0,
          week: res.week || 0,
          month: res.month || 0,
          pending: res.pending || 0,
          confirmed: res.confirmed || 0,
          rejected: res.rejected || 0
        };

        // 处理类型统计数据
        const typeList = (res.by_type || []).map(item => ({
          ...item,
          violation_type_name: getTypeName(item.violation_type),
          percent: res.total > 0 ? Math.round((item.count / res.total) * 100) : 0
        }));

        this.setData({
          stats,
          typeStats: typeList,
          myRank: res.my_rank || null,
          loading: false
        });

        wx.stopPullDownRefresh();
      })
      .catch(err => {
        console.error('获取全局统计失败', err);
        this.setData({
          stats: {},
          typeStats: [],
          loading: false
        });
        wx.stopPullDownRefresh();
        wx.showToast({
          title: '获取统计失败',
          icon: 'none'
        });
      });
  },

  /**
   * 页面错误处理
   */
  onError(err) {
    console.error('页面错误', err);
    wx.showToast({
      title: '页面加载异常',
      icon: 'none'
    });
  }
});