import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Image, ScrollView, Button } from '@tarojs/components'
import './index.scss'
import { getUserReports, ViolationRecord } from '../../api'

const VIOLATION_TYPES = {
  'red_light': '闯红灯',
  'parking': '违停',
  'speeding': '超速',
  'no_helmet': '未戴头盔',
  'phone': '接打电话',
  'other': '其他'
}

export default function Mine() {
  const [reports, setReports] = useState<ViolationRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchReports()
  }, [])

  const fetchReports = async () => {
    setLoading(true)
    try {
      const data = await getUserReports()
      setReports(data)
    } catch (error) {
      console.error('Fetch reports error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    fetchReports()
  }

  const handleItemClick = (item: ViolationRecord) => {
    Taro.showModal({
      title: '举报详情',
      content: `类型：${VIOLATION_TYPES[item.type] || item.type}\n描述：${item.description}\n状态：${item.status === 'pending' ? '待审核' : item.status === 'approved' ? '已采纳' : '已驳回'}`,
      showCancel: false
    })
  }

  const handleSettings = () => {
    Taro.showToast({ title: '设置功能开发中', icon: 'none' })
  }

  return (
    <ScrollView className="mine-page" scrollY>
      <View className="profile-section">
        <View className="profile-bg" />
        <View className="profile-content">
          <View className="avatar">
            <Text className="avatar-text">👤</Text>
          </View>
          <Text className="user-name">用户</Text>
          <Text className="user-id">ID: 888888</Text>
        </View>
      </View>

      <View className="stats-card">
        <View className="stat-item">
          <Text className="stat-value">{reports.length}</Text>
          <Text className="stat-label">累计举报</Text>
        </View>
        <View className="stat-divider" />
        <View className="stat-item">
          <Text className="stat-value">{reports.filter(r => r.status === 'approved').length}</Text>
          <Text className="stat-label">已采纳</Text>
        </View>
        <View className="stat-divider" />
        <View className="stat-item">
          <Text className="stat-value">{reports.filter(r => r.status === 'pending').length}</Text>
          <Text className="stat-label">待审核</Text>
        </View>
      </View>

      <View className="menu-card">
        <View className="menu-title">举报记录</View>
        <View className="report-list">
          {loading ? (
            <View className="loading">加载中...</View>
          ) : reports.length === 0 ? (
            <View className="empty-state">
              <Text className="empty-icon">📋</Text>
              <Text className="empty-text">暂无举报记录</Text>
            </View>
          ) : (
            reports.map((item) => (
              <View key={item.id} className="report-item" onClick={() => handleItemClick(item)}>
                <Image className="report-image" src={item.image_url} mode="aspectFill" />
                <View className="report-info">
                  <Text className="report-type">{VIOLATION_TYPES[item.type] || item.type}</Text>
                  <Text className="report-time">{item.timestamp}</Text>
                </View>
                <View className={`report-status ${item.status}`}>
                  {item.status === 'pending' ? '待审核' : item.status === 'approved' ? '已采纳' : '已驳回'}
                </View>
              </View>
            ))
          )}
        </View>
      </View>

      <View className="menu-card">
        <View className="menu-item" onClick={handleSettings}>
          <Text className="menu-icon">⚙️</Text>
          <Text className="menu-text">设置</Text>
          <Text className="menu-arrow">›</Text>
        </View>
        <View className="menu-item">
          <Text className="menu-icon">ℹ️</Text>
          <Text className="menu-text">关于我们</Text>
          <Text className="menu-arrow">›</Text>
        </View>
        <View className="menu-item">
          <Text className="menu-icon">📝</Text>
          <Text className="menu-text">使用帮助</Text>
          <Text className="menu-arrow">›</Text>
        </View>
      </View>

      <Button className="refresh-btn" onClick={handleRefresh}>
        <Text className="refresh-text">刷新数据</Text>
      </Button>
    </ScrollView>
  )
}