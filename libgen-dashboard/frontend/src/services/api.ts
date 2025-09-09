import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { useToast } from 'vue-toastification'
import type {
  User,
  UserCreate,
  UserLogin,
  AuthTokens,
  BookSearchRequest,
  BookSearchResponse,
  DownloadLinksResponse,
  SearchHistory,
  Bookmark,
  BookmarkCreate,
  DashboardStats
} from '@/types'

class ApiService {
  private api: AxiosInstance
  private toast = useToast()

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          this.clearAuth()
          window.location.href = '/login'
        } else if (error.response?.status >= 500) {
          this.toast.error('Server error. Please try again later.')
        } else if (error.response?.data?.detail) {
          this.toast.error(error.response.data.detail)
        }
        return Promise.reject(error)
      }
    )
  }

  private clearAuth() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('token_type')
    localStorage.removeItem('user')
  }

  // Health check
  async healthCheck(): Promise<any> {
    const response = await this.api.get('/')
    return response.data
  }

  // Authentication methods
  async register(userData: UserCreate): Promise<User> {
    const response = await this.api.post('/auth/register', userData)
    return response.data
  }

  async login(credentials: UserLogin): Promise<AuthTokens> {
    const response = await this.api.post('/auth/login', credentials)
    const tokens = response.data
    
    // Store tokens in localStorage
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('token_type', tokens.token_type)
    
    return tokens
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.api.get('/auth/me')
    const user = response.data
    
    // Store user in localStorage
    localStorage.setItem('user', JSON.stringify(user))
    
    return user
  }

  async logout(): Promise<void> {
    // Clear local storage
    this.clearAuth()
    
    // In a real app, you might also want to call a logout endpoint
    // to invalidate the token on the server side
  }

  // Book search methods
  async searchBooks(searchRequest: BookSearchRequest): Promise<BookSearchResponse> {
    const response = await this.api.post('/search', searchRequest)
    return response.data
  }

  async getDownloadLinks(md5Hash: string): Promise<DownloadLinksResponse> {
    const response = await this.api.get(`/book/${md5Hash}/download-links`)
    return response.data
  }

  // Search history methods
  async getSearchHistory(limit?: number): Promise<SearchHistory[]> {
    const params = limit ? { limit } : {}
    const response = await this.api.get('/search-history', { params })
    return response.data
  }

  async deleteSearchHistory(historyId: number): Promise<void> {
    await this.api.delete(`/search-history/${historyId}`)
  }

  // Bookmark methods
  async getBookmarks(limit?: number): Promise<Bookmark[]> {
    const params = limit ? { limit } : {}
    const response = await this.api.get('/bookmarks', { params })
    return response.data
  }

  async createBookmark(bookmarkData: BookmarkCreate): Promise<Bookmark> {
    const response = await this.api.post('/bookmarks', bookmarkData)
    return response.data
  }

  async deleteBookmark(bookmarkId: number): Promise<void> {
    await this.api.delete(`/bookmarks/${bookmarkId}`)
  }

  async isBookmarked(md5Hash: string): Promise<boolean> {
    try {
      const response = await this.api.get(`/bookmarks/check/${md5Hash}`)
      return response.data.bookmarked
    } catch (error) {
      return false
    }
  }

  // Dashboard stats
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await this.api.get('/stats')
    return response.data
  }

  // Mirror status
  async getMirrorStatus(): Promise<Record<string, boolean>> {
    const response = await this.api.get('/mirrors/status')
    return response.data
  }

  // Search suggestions
  async getSearchSuggestions(query: string): Promise<string[]> {
    const response = await this.api.get('/search/suggestions', {
      params: { q: query }
    })
    return response.data
  }

  // Popular books
  async getPopularBooks(limit: number = 10): Promise<any[]> {
    const response = await this.api.get('/books/popular', {
      params: { limit }
    })
    return response.data
  }

  // Generic request method for custom endpoints
  async request<T = any>(config: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.request(config)
    return response.data
  }
}

// Create and export a singleton instance
export const apiService = new ApiService()
export default apiService
