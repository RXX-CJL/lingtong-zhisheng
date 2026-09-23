// pages/detail/detail.js
const app = getApp();
const api = require('../../utils/api.js');
const { formatDate, formatPercent, getTypeName, getStatusName } = require('../../utils/format.js');

Page({
  data: {
    id: null,
    detail: null,
    imageUrl: '',
    loading: true,
    baseUrl: ''
  },

  onLoad(options) {
    this.setData({ baseUrl: app.globalData.baseUrl });

    if (options.id) {
      this.setData({ id: options.id });
      this.loadDetail();
    } else {
      wx.showToast({
        title: '参数错误',
        icon: 'none'
      });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    }
  },

  /**
   * 加载详情数据
   */
  loadDetail() {
    this.setData({ loading: true });

    const openid = app.globalData.openid;
    const id = this.data.id;

    api.getMyDetail(openid, id)
      .then(res => {
        // 处理返回数据
        const detail = {
          ...res,
          violation_type_name: getTypeName(res.violation_type),
          status_name: getStatusName(res.status),
          created_at: formatDate(res.created_at),
          confidence: formatPercent(res.confidence),
          cloud_validated_at: formatDate(res.cloud_validated_at),
          reviewed_at: formatDate(res.reviewed_at)
        };

        // 处理图片URL
        const imageUrl = res.image_path
          ? this.data.baseUrl + '/' + res.image_path
          : '';

        this.setData({
          detail,
          imageUrl,
          loading: false
        });
      })
      .catch(err => {
        console.error('获取详情失败', err);
        this.setData({ loading: false });
        wx.showToast({
          title: '获取详情失败',
          icon: 'none'
        });
      });
  },

  /**
   * 预览图片
   */
  previewImage() {
    if (!this.data.imageUrl) return;

    wx.previewImage({
      current: this.data.imageUrl,
      urls: [this.data.imageUrl]
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