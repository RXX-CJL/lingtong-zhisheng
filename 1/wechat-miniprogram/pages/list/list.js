// pages/list/list.js
const app = getApp();
const api = require('../../utils/api.js');
const { getTypeList, getStatusList, formatDate, formatPercent, getTypeName, getStatusName } = require('../../utils/format.js');

Page({
  data: {
    items: [],
    page: 1,
    pageSize: 10,
    hasMore: true,
    loading: false,
    filterType: '',
    filterStatus: '',
    typeOptions: [
      { value: '', label: '全部类型' },
      ...getTypeList()
    ],
    statusOptions: [
      { value: '', label: '全部状态' },
      ...getStatusList()
    ],
    typeIndex: 0,
    statusIndex: 0,
    baseUrl: ''
  },

  onLoad(options) {
    this.setData({ baseUrl: app.globalData.baseUrl });
  },

  onShow() {
    // 每次显示时刷新列表
    this.refreshList();
  },

  onPullDownRefresh() {
    this.refreshList();
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadMore();
    }
  },

  /**
   * 刷新列表
   */
  refreshList() {
    this.setData({
      page: 1,
      hasMore: true,
      items: []
    });
    this.loadList();
  },

  /**
   * 加载列表数据
   */
  loadList() {
    if (this.data.loading) return;

    this.setData({ loading: true });

    const openid = app.globalData.openid;
    api.getMyList(
      openid,
      this.data.page,
      this.data.pageSize,
      this.data.filterType,
      this.data.filterStatus
    ).then(res => {
      // 处理返回数据，添加中文名称
      const items = (res.items || res.data || []).map(item => ({
        ...item,
        violation_type_name: getTypeName(item.violation_type),
        status_name: getStatusName(item.status),
        created_at: formatDate(item.created_at),
        confidence: formatPercent(item.confidence)
      }));

      this.setData({
        items: items,
        hasMore: res.has_more || res.hasMore || false,
        loading: false
      });

      wx.stopPullDownRefresh();
    }).catch(err => {
      console.error('获取列表失败', err);
      this.setData({ loading: false });
      wx.stopPullDownRefresh();
      wx.showToast({
        title: '获取记录失败',
        icon: 'none'
      });
    });
  },

  /**
   * 加载更多
   */
  loadMore() {
    if (!this.data.hasMore) return;

    this.setData({ page: this.data.page + 1, loading: true });

    const openid = app.globalData.openid;
    api.getMyList(
      openid,
      this.data.page,
      this.data.pageSize,
      this.data.filterType,
      this.data.filterStatus
    ).then(res => {
      const newItems = (res.items || res.data || []).map(item => ({
        ...item,
        violation_type_name: getTypeName(item.violation_type),
        status_name: getStatusName(item.status),
        created_at: formatDate(item.created_at),
        confidence: formatPercent(item.confidence)
      }));

      this.setData({
        items: [...this.data.items, ...newItems],
        hasMore: res.has_more || res.hasMore || false,
        loading: false
      });
    }).catch(err => {
      console.error('加载更多失败', err);
      this.setData({
        page: this.data.page - 1,
        loading: false
      });
    });
  },

  /**
   * 违规类型筛选变化
   */
  onTypeChange(e) {
    const index = e.detail.value;
    const typeOptions = this.data.typeOptions;
    this.setData({
      typeIndex: index,
      filterType: typeOptions[index].value
    });
    this.refreshList();
  },

  /**
   * 状态筛选变化
   */
  onStatusChange(e) {
    const index = e.detail.value;
    const statusOptions = this.data.statusOptions;
    this.setData({
      statusIndex: index,
      filterStatus: statusOptions[index].value
    });
    this.refreshList();
  },

  /**
   * 跳转详情页
   */
  goToDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}`
    });
  },

  /**
   * 跳转提交页
   */
  goToSubmit() {
    wx.navigateTo({
      url: '/pages/submit/submit'
    });
  },

  /**
   * 图片加载失败
   */
  onImageError(e) {
    const index = e.currentTarget.dataset.index;
    const items = [...this.data.items];
    items[index].image_path = '';
    this.setData({ items });
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