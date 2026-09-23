App({
  onLaunch(options) {
    // 初始化全局数据
    // 优先级：本地配置 > 环境变量
    const localConfig = wx.getStorageSync('serverConfig') || {};
    
    this.globalData = {
      openid: localConfig.openid || "TEST_OPENID_001",
      // 支持自定义服务器地址，真机调试时使用局域网IP
      baseUrl: localConfig.baseUrl || "http://127.0.0.1:8001"
    };

    // 检测运行环境
    const isDev = !wx.getAccountInfoSync().miniProgram;
    if (!isDev || wx.getStorageSync('isProduction')) {
      wx.showModal({
        title: '配置提示',
        content: '真机调试时，请在「我的」页面设置服务器地址为电脑的局域网IP（如 http://192.168.x.x:8000）',
        showCancel: false
      });
    }

    console.log('智瞳灵声小程序启动', options);
  },

  globalData: {
    openid: "TEST_OPENID_001",
    baseUrl: "http://127.0.0.1:8001"
  }
});