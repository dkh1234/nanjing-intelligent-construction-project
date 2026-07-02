import axios from 'axios'

const BASE_URL = '/api/dify'

const request = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('请求超时，请稍后重试'))
    }
    // 透传完整 response 以便调试
    const enriched = new Error(error.response?.data?.message || error.message || '网络异常')
    enriched.response = error.response
    enriched.data = error.response?.data
    return Promise.reject(enriched)
  }
)

export default request
