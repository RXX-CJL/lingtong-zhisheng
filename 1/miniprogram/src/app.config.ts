export default defineAppConfig({
  pages: [
    'pages/home/index',
    'pages/report/index',
    'pages/notifications/index',
    'pages/mine/index',
    'pages/appeal/index'
  ],
  window: {
    backgroundTextStyle: 'dark',
    navigationBarBackgroundColor: '#1890ff',
    navigationBarTitleText: '交通违规举报',
    navigationBarTextStyle: 'white',
    backgroundColor: '#f0f2f5'
  },
  tabBar: {
    color: '#999999',
    selectedColor: '#1890ff',
    backgroundColor: '#ffffff',
    borderStyle: 'white',
    list: [
      {
        pagePath: 'pages/home/index',
        text: '首页',
        iconPath: 'assets/tabbar/home.svg',
        selectedIconPath: 'assets/tabbar/home-selected.svg'
      },
      {
        pagePath: 'pages/report/index',
        text: '举报',
        iconPath: 'assets/tabbar/report.svg',
        selectedIconPath: 'assets/tabbar/report-selected.svg'
      },
      {
        pagePath: 'pages/notifications/index',
        text: '通知',
        iconPath: 'assets/tabbar/notification.svg',
        selectedIconPath: 'assets/tabbar/notification-selected.svg'
      },
      {
        pagePath: 'pages/mine/index',
        text: '我的',
        iconPath: 'assets/tabbar/mine.svg',
        selectedIconPath: 'assets/tabbar/mine-selected.svg'
      }
    ]
  }
})