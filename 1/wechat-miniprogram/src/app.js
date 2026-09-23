/**
 * 小程序入口文件
 */
App({
  globalData: {
    apiBaseUrl: 'http://localhost:8000/api',  // API地址
    userInfo: null,
    openid: null,
    token: null
  },
  
  onLaunch() {
    // 登录获取openid
    this.login()
  },
  
  login() {
    wx.login({
      success: res => {
        if (res.code) {
          // 发送code到后端获取openid
          this.request('/wechat/code2session', {
            code: res.code
          }, 'POST').then(result => {
            if (result.openid) {
              this.globalData.openid = result.openid
              wx.setStorageSync('openid', result.openid)
            }
          })
        }
      }
    })
  },
  
  // 封装的请求方法
  request(url, data = {}, method = 'GET') {
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBaseUrl + url,
        data,
        method,
        header: {
          'content-type': 'application/json',
          'Authorization': this.globalData.token ? `Bearer ${this.globalData.token}` : ''
        },
        success: res => {
          if (res.data.success) {
            resolve(res.data.data || res.data)
          } else {
            wx.showToast({
              title: res.data.message || '请求失败',
              icon: 'none'
            })
            reject(res.data)
          }
        },
        fail: err => {
          wx.showToast({
            title: '网络请求失败',
            icon: 'none'
          })
          reject(err)
        }
      })
    })
  },
  
  // 显示加载中
  showLoading(title = '加载中') {
    wx.showLoading({ title, mask: true })
  },
  
  // 隐藏加载
  hideLoading() {
    wx.hideLoading()
  }
})
