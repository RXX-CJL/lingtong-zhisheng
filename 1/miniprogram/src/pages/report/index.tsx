import { useState } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Image, Button, Textarea, ScrollView, Radio } from '@tarojs/components'
import './index.scss'
import { submitViolation } from '../../api'

const VIOLATION_OPTIONS = [
  { value: 'red_light', label: '闯红灯', icon: '🚦' },
  { value: 'parking', label: '违停', icon: '🚗' },
  { value: 'speeding', label: '超速', icon: '⚡' },
  { value: 'no_helmet', label: '未戴头盔', icon: '🛵' },
  { value: 'phone', label: '接打电话', icon: '📱' },
  { value: 'other', label: '其他', icon: '⚠️' }
]

export default function Report() {
  const [selectedType, setSelectedType] = useState('')
  const [description, setDescription] = useState('')
  const [location, setLocation] = useState('')
  const [imagePath, setImagePath] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChooseImage = () => {
    Taro.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        setImagePath(res.tempFilePaths[0])
      }
    })
  }

  const handleSubmit = async () => {
    if (!selectedType) {
      Taro.showToast({ title: '请选择违规类型', icon: 'none' })
      return
    }
    if (!imagePath) {
      Taro.showToast({ title: '请上传证据图片', icon: 'none' })
      return
    }
    if (!description) {
      Taro.showToast({ title: '请填写违规描述', icon: 'none' })
      return
    }

    setIsSubmitting(true)
    try {
      await submitViolation({
        type: selectedType,
        description,
        location: location || '未填写',
        image: imagePath
      })
      Taro.showToast({ title: '举报提交成功', icon: 'success' })
      setSelectedType('')
      setDescription('')
      setLocation('')
      setImagePath('')
    } catch (error) {
      Taro.showToast({ title: '提交失败，请重试', icon: 'none' })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <ScrollView className="report-page" scrollY>
      <View className="report-card">
        <View className="card-section">
          <Text className="section-title">违规类型</Text>
          <View className="type-grid">
            {VIOLATION_OPTIONS.map((item) => (
              <Radio
                key={item.value}
                className="type-radio"
                checked={selectedType === item.value}
                value={item.value}
                onChange={() => setSelectedType(item.value)}
              >
                <View className={`type-option ${selectedType === item.value ? 'selected' : ''}`}>
                  <Text className="type-icon">{item.icon}</Text>
                  <Text className="type-label">{item.label}</Text>
                </View>
              </Radio>
            ))}
          </View>
        </View>

        <View className="card-section">
          <Text className="section-title">证据图片</Text>
          <View className={`image-upload ${imagePath ? 'has-image' : ''}`} onClick={handleChooseImage}>
            {imagePath ? (
              <Image className="uploaded-image" src={imagePath} mode="aspectFill" />
            ) : (
              <View className="upload-placeholder">
                <Text className="upload-icon">📷</Text>
                <Text className="upload-text">点击拍照或上传</Text>
              </View>
            )}
          </View>
        </View>

        <View className="card-section">
          <Text className="section-title">违规描述</Text>
          <Textarea
            className="description-input"
            placeholder="请详细描述违规行为..."
            value={description}
            onChange={(e) => setDescription(e.detail.value)}
            maxlength={500}
          />
          <Text className="input-count">{description.length}/500</Text>
        </View>

        <View className="card-section">
          <Text className="section-title">违规地点</Text>
          <View className="location-input-wrap">
            <Text className="location-icon">📍</Text>
            <Textarea
              className="location-input"
              placeholder="请输入违规地点（选填）"
              value={location}
              onChange={(e) => setLocation(e.detail.value)}
              maxlength={100}
            />
          </View>
        </View>

        <Button className="submit-btn" onClick={handleSubmit} loading={isSubmitting}>
          <Text className="submit-text">提交举报</Text>
        </Button>
      </View>

      <View className="tips-section">
        <Text className="tips-title">💡 举报须知</Text>
        <Text className="tips-item">• 请确保图片清晰，能清晰辨认违规行为</Text>
        <Text className="tips-item">• 请如实填写违规信息，虚假举报将被追责</Text>
        <Text className="tips-item">• 举报信息将匿名提交，保护您的隐私</Text>
      </View>
    </ScrollView>
  )
}