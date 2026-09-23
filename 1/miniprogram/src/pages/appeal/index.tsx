import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, ScrollView, Textarea, Image, Button } from '@tarojs/components'
import './index.scss'
import { submitAppeal, getViolationDetail, AppealRecord, ViolationRecord } from '../../api'

const VIOLATION_TYPES = {
  'red_light': '闯红灯',
  'parking': '违停',
  'speeding': '超速',
  'no_helmet': '未戴头盔',
  'phone': '接打电话',
  'other': '其他'
}

export default function Appeal() {
  const [violationId, setViolationId] = useState<number>(0)
  const [violation, setViolation] = useState<ViolationRecord | null>(null)
  const [appeal, setAppeal] = useState<AppealRecord | null>(null)
  const [reason, setReason] = useState('')
  const [contact, setContact] = useState('')
  const [evidencePath, setEvidencePath] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    const options = Taro.getCurrentInstance()?.router?.params
    if (options?.violation_id) {
      const id = parseInt(options.violation_id)
      setViolationId(id)
      fetchViolation(id)
    }
  }, [])

  const fetchViolation = async (id: number) => {
    try {
      const data = await getViolationDetail(id)
      setViolation(data)
    } catch (error) {
      console.error('Fetch violation error:', error)
    }
  }

  const handleChooseImage = () => {
    Taro.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        setEvidencePath(res.tempFilePaths[0])
      }
    })
  }

  const handleSubmit = async () => {
    if (!reason.trim()) {
      Taro.showToast({ title: '请填写申诉理由', icon: 'none' })
      return
    }

    setIsSubmitting(true)
    try {
      await submitAppeal({
        violation_id: violationId,
        reason: reason.trim(),
        contact: contact.trim() || undefined,
        evidence: evidencePath || undefined
      })
      Taro.showToast({ title: '申诉提交成功', icon: 'success' })
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    } catch (error) {
      Taro.showToast({ title: '提交失败，请重试', icon: 'none' })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!violation) {
    return <View className="loading">加载中...</View>
  }

  return (
    <ScrollView className="appeal-page" scrollY>
      <View className="page-header">
        <Text className="page-title">申诉提交</Text>
      </View>

      <View className="appeal-card">
        <View className="card-section">
          <Text className="section-title">违规信息</Text>
          <View className="violation-info">
            <View className="violation-type-badge">{VIOLATION_TYPES[violation.type] || violation.type}</View>
            <Text className="violation-desc">{violation.description}</Text>
            <Text className="violation-time">检测时间：{violation.timestamp}</Text>
            <Text className="violation-location">检测地点：{violation.location}</Text>
            <View className="violation-image-wrap">
              <Image className="violation-image" src={violation.image_url} mode="aspectFit" />
              <Text className="image-label">违规证据</Text>
            </View>
          </View>
        </View>

        <View className="card-section">
          <Text className="section-title">申诉理由</Text>
          <Textarea
            className="reason-input"
            placeholder="请详细说明您的申诉理由，如：您认为该检测存在误判，请提供相关证据..."
            value={reason}
            onChange={(e) => setReason(e.detail.value)}
            maxlength={500}
            autoHeight
          />
          <Text className="input-count">{reason.length}/500</Text>
        </View>

        <View className="card-section">
          <Text className="section-title">联系方式（选填）</Text>
          <Textarea
            className="contact-input"
            placeholder="请输入您的联系方式，以便我们与您联系"
            value={contact}
            onChange={(e) => setContact(e.detail.value)}
            maxlength={50}
          />
        </View>

        <View className="card-section">
          <Text className="section-title">申诉证据（选填）</Text>
          <View className={`image-upload ${evidencePath ? 'has-image' : ''}`} onClick={handleChooseImage}>
            {evidencePath ? (
              <Image className="uploaded-image" src={evidencePath} mode="aspectFill" />
            ) : (
              <View className="upload-placeholder">
                <Text className="upload-icon">📷</Text>
                <Text className="upload-text">点击拍照或上传证据</Text>
              </View>
            )}
          </View>
          <Text className="upload-hint">您可以上传照片作为申诉证据</Text>
        </View>

        <Button className="submit-btn" onClick={handleSubmit} loading={isSubmitting}>
          <Text className="submit-text">提交申诉</Text>
        </Button>
      </View>

      <View className="tips-section">
        <Text className="tips-title">💡 申诉须知</Text>
        <Text className="tips-item">• 请如实填写申诉理由，虚假申诉将被追责</Text>
        <Text className="tips-item">• 申诉提交后，管理员将在3个工作日内处理</Text>
        <Text className="tips-item">• 申诉结果将通过通知告知您</Text>
      </View>
    </ScrollView>
  )
}
