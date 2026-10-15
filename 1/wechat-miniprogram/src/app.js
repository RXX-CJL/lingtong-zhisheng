/**
 * 小程序入口文件
 */
App({
  globalData: {
    // 2026-10-03 由 DSH 修正三处（原值有 3 个错误）：
    //   ① 端口 8000 -> 8001（项目后端实际监听 8001）
    //   ② 前缀改为 /api/wx（后端小程序接口的真实前缀）
    //   ③ 补 baseUrl 字段 —— utils/api.js 读的是 globalData.baseUrl，
    //      而原 app.js 只有 apiBaseUrl；两者不一致会让 URL 变成
    //      "undefined/api/..."，所有请求必然失败（静态检查已证实）。
    //      两个字段都保留，兼容不同调用点。
    baseUrl: 'http://127.0.0.1:8001/api/wx',
    apiBaseUrl: 'http://127.0.0.1:8001/api/wx',
    userInfo: null,
    openid: null,
    token: null
  },

  onLaunch() {
    // 登录获取 openid
    this.login()
  },

  login() {
    wx.login({
      success: res => {
        if (res.code) {
          // 2026-10-03 由 DSH 修正：后端接口是 POST /api/wx/login
          // （原 /wechat/code2session 在后端不存在）
          this.request('/login', { code: res.code }, 'POST').then(result => {
            if (result && result.openid) {
              this.globalData.openid = result.openid
              wx.setStorageSync('openid', result.openid)
              if (result.dev_mode) {
                console.warn('[app] 后端处于开发模式（未配置 WX_APPID/WX_SECRET）')
              }
            }
          }).catch(() => { /* 登录失败不阻塞页面 */ })
        }
      }
    })
  },

  // 封装的请求方法
  request(url, data = {}, method = 'GET') {
    return new Promise((resolve, reject) => {
      // 优先用内存 openid，退化到本地缓存（避免冷启动竞态）
      const openid = this.globalData.openid || wx.getStorageSync('openid') || ''
      wx.request({
        url: this.globalData.baseUrl + url,
        data,
        method,
        header: {
          'content-type': 'application/json',
          // 2026-10-03 由 DSH 修正：后端 /api/wx/* 要求的鉴权头是 X-Openid
          // （原为 Authorization: Bearer <token>，后端不识别）
          'X-Openid': openid
        },
        success: res => {
          if (res.data && res.data.success) {
            resolve(res.data.data !== undefined ? res.data.data : res.data)
          } else {
            const msg = (res.data && res.data.message) || '请求失败'
            wx.showToast({ title: msg, icon: 'none' })
            reject(res.data || { message: msg })
          }
        },
        fail: err => {
          wx.showToast({ title: '网络请求失败', icon: 'none' })
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
