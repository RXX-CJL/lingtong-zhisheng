/**
 * 个人中心页
 */
const app = getApp()

Page({
  data: {
    userInfo: {
      nickname: '微信用户',
      avatar: '/assets/icons/avatar.png'
    },
    appealStats: {
      pending: 0,
      reviewing: 0,
      approved: 0,
      rejected: 0
    },
    menuItems: [
      // 2026-10-03 由 DSH 修正：原菜单指向 /pages/my/devices 与 /pages/my/settings，
      // 这两个页面**并不存在**（点击会报错）。改为指向真实存在的新页面。
      { id: 'vehicles', title: '车辆绑定', icon: '/assets/icons/device.png', path: '/pages/my/bind' },
      { id: 'notifications', title: '通知中心', icon: '/assets/icons/appeal.png', path: '/pages/notifications/index' },
      { id: 'appeals', title: '我的申诉', icon: '/assets/icons/appeal.png', path: '/pages/appeal/list' }
    ],
    vehicleCount: 0,
    unreadCount: 0
  },
  
  onLoad() {
    this.loadUserInfo()
    this.loadAppealStats()
    this.loadBindInfo()
  },
  
  onShow() {
    this.loadUserInfo()
    this.loadAppealStats()
    this.loadBindInfo()
  },
  
  // 加载绑定车辆数与未读通知数（2026-10-03 由 DSH 新增）
  loadBindInfo() {
    app.request('/bind/status').then(data => {
      this.setData({ vehicleCount: ((data && data.my_vehicles) || []).length })
    }).catch(() => {})
    app.request('/overview').then(data => {
      this.setData({ unreadCount: (data && data.unread) || 0 })
    }).catch(() => {})
  },
  
  // 加载用户信息
  loadUserInfo() {
    const openid = wx.getStorageSync('openid')
    if (openid) {
      // 可以调用API获取用户信息
    }
  },
  
  // 加载申诉统计
  loadAppealStats() {
    app.request('/appeals/statistics/summary').then(data => {
      this.setData({ appealStats: data })
    }).catch(() => {})
  },
  
  // 获取微信头像
  getUserProfile() {
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: res => {
        this.setData({
          'userInfo.nickname': res.userInfo.nickName,
          'userInfo.avatar': res.userInfo.avatarUrl
        })
      }
    })
  },
  
  // 菜单点击
  onMenuTap(e) {
    const path = e.currentTarget.dataset.path
    if (path) {
      wx.navigateTo({ url: path })
    }
  }
})
