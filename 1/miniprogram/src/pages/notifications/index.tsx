import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, ScrollView, Image } from '@tarojs/components'
import './index.scss'
import { getNotificationList, markNotificationRead, NotificationRecord } from '../../api'

const VIOLATION_TYPES = {
  'red_light': '闯红灯',
  'parking': '违停',
  'speeding': '超速',
  'no_helmet': '未戴头盔',
  'phone': '接打电话',
  'other': '其他'
}

export default function Notifications() {
  const [notifications, setNotifications] = useState<NotificationRecord[]>([])
  const [loading, setLoading] = useState(true)

  const fetchNotifications = async () => {
    setLoading(true)
    try {
      const data = await getNotificationList()
      setNotifications(data)
    } catch (error) {
      console.error('Fetch notifications error:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNotifications()
  }, [])

  const handleItemClick = async (item: NotificationRecord) => {
    if (!item.read) {
      await markNotificationRead(item.id)
    }
    Taro.navigateTo({
      url: `/pages/appeal/index?violation_id=${item.violation_id}&notification_id=${item.id}`
    })
  }

  const handleRefresh = () => {
    fetchNotifications()
  }

  return (
    <ScrollView className="notifications-page" scrollY>
      <View className="page-header">
        <Text className="page-title">违规通知</Text>
        <Text className="refresh-btn" onClick={handleRefresh}>刷新</Text>
      </View>

      {loading ? (
        <View className="loading">加载中...</View>
      ) : notifications.length === 0 ? (
        <View className="empty-state">
          <Text className="empty-icon">🔔</Text>
          <Text className="empty-text">暂无违规通知</Text>
          <Text className="empty-hint">当您的车辆被检测到违规时，会在这里通知您</Text>
        </View>
      ) : (
        <View className="notification-list">
          {notifications.map((item) => (
            <View
              key={item.id}
              className={`notification-item ${item.read ? 'read' : 'unread'}`}
              onClick={() => handleItemClick(item)}
            >
              <View className={`notification-icon ${item.type === 'violation' ? 'violation' : 'appeal'}`}>
                {item.type === 'violation' ? '⚠️' : '📝'}
              </View>
              <View className="notification-content">
                <Text className="notification-title">{item.title}</Text>
                <Text className="notification-desc">{item.content}</Text>
                <Text className="notification-time">{item.timestamp}</Text>
              </View>
              {!item.read && <View className="unread-dot" />}
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  )
}
