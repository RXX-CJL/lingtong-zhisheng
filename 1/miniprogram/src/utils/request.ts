import Taro from '@tarojs/taro'

const BASE_URL = 'http://127.0.0.1:8001/api'

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export async function request<T = any>(
  options: {
    url: string
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
    data?: any
    header?: any
  }
): Promise<ApiResponse<T>> {
  const { url, method = 'GET', data = {}, header = {} } = options

  return new Promise((resolve, reject) => {
    Taro.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...header
      },
      success: (res) => {
        resolve(res.data as ApiResponse<T>)
      },
      fail: (error) => {
        reject(error)
      }
    })
  })
}

export async function uploadFile(
  filePath: string,
  url: string,
  formData?: any
): Promise<any> {
  return new Promise((resolve, reject) => {
    Taro.uploadFile({
      url: `${BASE_URL}${url}`,
      filePath,
      name: 'image',
      formData,
      success: (res) => {
        resolve(JSON.parse(res.data))
      },
      fail: (error) => {
        reject(error)
      }
    })
  })
}