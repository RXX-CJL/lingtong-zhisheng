import { useState, useEffect } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { View, Text, Image, ScrollView, Button } from '@tarojs/components'
import './index.scss'
import { getViolationStats, getViolationList, ViolationRecord, ViolationStats } from '../../api'

const VIOLATION_TYPES = {
  'red_light': '闯红灯',
  'parking': '违停',
  'speeding': '超速',
  'no_helmet': '未戴头盔',
  'phone': '接打电话'
}

export default function Home() {
  const [stats, setStats] = useState<ViolationStats | null>(null)
  const [violations, setViolations] = useState<ViolationRecord[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsRes, violationsRes] = await Promise.all([
        getViolationStats(),
        getViolationList(1, 5)
      ])
      setStats(statsRes)
      setViolations(violationsRes)
    } catch (error) {
      console.error('Fetch data error:', error)
    } finally {
      setLoading(false)
    }
  }

  useDidShow(() => {
    fetchData()
  })

  useEffect(() => {
    fetchData()
  }, [])

  const goToReport = () => {
    Taro.switchTab({ url: '/pages/report/index' })
  }

  return (
    <ScrollView className="home-page" scrollY>
      <View className="header-section">
        <View className="header-bg" />
        <View className="header-content">
          <Text className="header-title">交通违规举报</Text>
          <Text className="header-subtitle">共建文明交通环境</Text>
          <Button className="report-btn" onClick={goToReport}>
            <Text className="report-btn-icon">📸</Text>
            <Text className="report-btn-text">立即举报</Text>
          </Button>
        </View>
      </View>

      {loading ? (
        <View className="loading">加载中...</View>
      ) : (
        <>
          <View className="stats-section">
            <View className="section-title">统计概览</View>
            <View className="stats-grid">
              <View className="stat-item">
                <Text className="stat-value">{stats?.today_count || 0}</Text>
                <Text className="stat-label">今日举报</Text>
              </View>
              <View className="stat-item">
                <Text className="stat-value">{stats?.week_count || 0}</Text>
                <Text className="stat-label">本周举报</Text>
              </View>
              <View className="stat-item">
                <Text className="stat-value">{stats?.month_count || 0}</Text>
                <Text className="stat-label">本月举报</Text>
              </View>
            </View>
          </View>

          <View className="top-types-section">
            <View className="section-title">高发违规类型</View>
            <ScrollView className="types-scroll" scrollX>
              <View className="types-list">
                {(stats?.top_types || []).map((item, index) => (
                  <View key={index} className="type-item">
                    <View className="type-rank">{index + 1}</View>
                    <Text className="type-name">{VIOLATION_TYPES[item.type] || item.type}</Text>
                    <Text className="type-count">{item.count}起</Text>
                  </View>
                ))}
              </View>
            </ScrollView>
          </View>

          <View className="recent-section">
            <View className="section-header">
              <Text className="section-title">最近举报</Text>
              <Text className="section-more">查看全部</Text>
            </View>
            <View className="recent-list">
              {violations.map((item) => (
                <View key={item.id} className="recent-item">
                  <Image className="recent-image" src={item.image_url} mode="aspectFill" />
                  <View className="recent-info">
                    <Text className="recent-type">{VIOLATION_TYPES[item.type] || item.type}</Text>
                    <Text className="recent-desc">{item.description}</Text>
                    <View className="recent-footer">
                      <Text className="recent-location">{item.location}</Text>
                      <Text className="recent-time">{item.timestamp}</Text>
                    </View>
                  </View>
                  <View className={`recent-status ${item.status}`}>
                    {item.status === 'pending' ? '待审核' : item.status === 'approved' ? '已采纳' : '已驳回'}
                  </View>
                </View>
              ))}
            </View>
          </View>
        </>
      )}
    </ScrollView>
  )
}