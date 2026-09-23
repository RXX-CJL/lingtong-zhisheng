import { request, uploadFile } from '../utils/request'

export interface ViolationRecord {
  id: number
  type: string
  description: string
  image_url: string
  location: string
  timestamp: string
  status: string
  violation_type: string
}

export interface ViolationStats {
  today_count: number
  week_count: number
  month_count: number
  top_types: { type: string; count: number }[]
}

export interface NotificationRecord {
  id: number
  title: string
  content: string
  type: string
  violation_id: number
  read: boolean
  timestamp: string
}

export interface AppealRecord {
  appeal_id: number
  violation_id: number
  reason: string
  status: string
  evidence_urls: string[]
  result: string | null
  created_at: string
  processed_at: string | null
}

export async function getViolationStats(): Promise<ViolationStats> {
  const res = await request({ url: '/violation/stats' })
  return res.data
}

export async function getViolationList(
  page: number = 1,
  limit: number = 10
): Promise<ViolationRecord[]> {
  const res = await request({ url: `/violation/list?page=${page}&limit=${limit}` })
  return res.data
}

export async function submitViolation(data: {
  type: string
  description: string
  location: string
  image: string
}): Promise<any> {
  return uploadFile(data.image, '/violation/submit', {
    type: data.type,
    description: data.description,
    location: data.location
  })
}

export async function getUserReports(): Promise<ViolationRecord[]> {
  const res = await request({ url: '/violation/my-reports' })
  return res.data
}

export async function getViolationDetail(id: number): Promise<ViolationRecord> {
  const res = await request({ url: `/violation/detail/${id}` })
  return res.data
}

export async function getNotificationList(): Promise<NotificationRecord[]> {
  const res = await request({ url: '/notifications/list' })
  return res.data
}

export async function getNotificationDetail(id: number): Promise<NotificationRecord> {
  const res = await request({ url: `/notifications/${id}` })
  return res.data
}

export async function markNotificationRead(id: number): Promise<any> {
  const res = await request({ url: `/notifications/${id}/read`, method: 'PUT' })
  return res.data
}

export async function submitAppeal(data: {
  violation_id: number
  reason: string
  contact?: string
  evidence?: string
}): Promise<any> {
  if (data.evidence) {
    return uploadFile(data.evidence, '/appeals/submit-with-image', {
      violation_id: data.violation_id.toString(),
      reason: data.reason,
      contact: data.contact || ''
    })
  }
  const res = await request({
    url: '/appeals/submit',
    method: 'POST',
    data: {
      violation_id: data.violation_id,
      reason: data.reason,
      contact: data.contact
    }
  })
  return res.data
}

export async function getAppealByViolation(violation_id: number): Promise<AppealRecord | null> {
  try {
    const res = await request({ url: `/appeals/${violation_id}` })
    return res.data
  } catch {
    return null
  }
}