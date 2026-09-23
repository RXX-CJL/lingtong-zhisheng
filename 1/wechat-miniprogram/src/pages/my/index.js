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
      { id: 'appeals', title: '我的申诉', icon: '/assets/icons/appeal.png', path: '/pages/appeal/list' },
      { id: 'devices', title: '设备绑定', icon: '/assets/icons/device.png', path: '/pages/my/devices' },
      { id: 'settings', title: '设置', icon: '/assets/icons/settings.png', path: '/pages/my/settings' }
    ]
  },
  
  onLoad() {
    this.loadUserInfo()
    this.loadAppealStats()
  },
  
  onShow() {
    this.loadUserInfo()
    this.loadAppealStats()
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
