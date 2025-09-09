// User types
export interface User {
  id: number
  email: string
  username: string
  first_name?: string
  last_name?: string
  avatar_url?: string
  is_active: boolean
  created_at: string
  last_login?: string
}

export interface UserCreate {
  email: string
  username: string
  password: string
  first_name?: string
  last_name?: string
}

export interface UserLogin {
  email: string
  password: string
}

// Authentication types
export interface AuthTokens {
  access_token: string
  token_type: string
  expires_in: number
}

export interface AuthState {
  user: User | null
  tokens: AuthTokens | null
  isAuthenticated: boolean
  isLoading: boolean
}

// Book types
export interface Book {
  title: string
  author?: string
  year?: string
  pages?: string
  language?: string
  size?: string
  extension?: string
  md5?: string
  publisher?: string
  isbn?: string
  description?: string
  cover_url?: string
}

export interface BookSearchRequest {
  query: string
  max_results?: number
  search_type?: string
}

export interface BookSearchResponse {
  query: string
  total_results: number
  books: Book[]
  user_id: number
  search_timestamp: string
}

export interface DownloadLink {
  url: string
  type: string
  mirror?: string
  quality?: string
}

export interface DownloadLinksResponse {
  md5: string
  download_links: DownloadLink[]
  user_id: number
  generated_at: string
}

// Search history types
export interface SearchHistory {
  id: number
  query: string
  results_count: number
  search_timestamp: string
}

// Bookmark types
export interface Bookmark {
  id: number
  book_md5: string
  book_title: string
  book_author?: string
  book_extension?: string
  book_size?: string
  book_year?: string
  bookmarked_at: string
}

export interface BookmarkCreate {
  book_md5: string
  book_title: string
  book_author?: string
  book_extension?: string
  book_size?: string
  book_year?: string
}

// Dashboard stats
export interface DashboardStats {
  total_searches: number
  total_bookmarks: number
  recent_searches: SearchHistory[]
  popular_books: Bookmark[]
  user_stats: Record<string, any>
}

// API response types
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
  timestamp: string
}

export interface ApiError {
  success: boolean
  error: string
  detail?: string
  timestamp: string
}

// UI state types
export interface SearchState {
  query: string
  results: Book[]
  isLoading: boolean
  error: string | null
  totalResults: number
  currentPage: number
  resultsPerPage: number
}

export interface UiState {
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  notifications: Notification[]
}

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
  read: boolean
}

// Form types
export interface LoginForm {
  email: string
  password: string
  rememberMe: boolean
}

export interface RegisterForm {
  email: string
  username: string
  password: string
  confirmPassword: string
  firstName?: string
  lastName?: string
}

export interface SearchForm {
  query: string
  searchType: 'title' | 'author' | 'isbn' | 'all'
  maxResults: number
}

// Filter and sort types
export interface BookFilters {
  extension?: string[]
  language?: string[]
  yearRange?: [number, number]
  sizeRange?: [number, number]
}

export interface SortOptions {
  field: 'title' | 'author' | 'year' | 'size' | 'relevance'
  direction: 'asc' | 'desc'
}

// Navigation types
export interface NavItem {
  name: string
  href: string
  icon?: string
  current: boolean
  children?: NavItem[]
}

// Statistics types
export interface UserStats {
  totalSearches: number
  totalBookmarks: number
  favoriteGenres: string[]
  searchActivity: Array<{
    date: string
    count: number
  }>
}
