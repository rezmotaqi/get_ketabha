import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useToast } from 'vue-toastification'
import apiService from '@/services/api'
import type { User, UserLogin, UserCreate, AuthTokens } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const tokens = ref<AuthTokens | null>(null)
  const isLoading = ref(false)
  const isInitialized = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!user.value && !!tokens.value)
  const userName = computed(() => {
    if (!user.value) return ''
    return user.value.first_name 
      ? `${user.value.first_name} ${user.value.last_name || ''}`.trim()
      : user.value.username
  })

  const toast = useToast()

  // Actions
  async function login(credentials: UserLogin) {
    isLoading.value = true
    try {
      // Authenticate user
      const authTokens = await apiService.login(credentials)
      tokens.value = authTokens

      // Get user info
      const userData = await apiService.getCurrentUser()
      user.value = userData

      toast.success(`Welcome back, ${userName.value}!`)
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Login failed'
      toast.error(message)
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function register(userData: UserCreate) {
    isLoading.value = true
    try {
      // Register user
      await apiService.register(userData)
      
      // Auto-login after registration
      const loginSuccess = await login({
        email: userData.email,
        password: userData.password
      })

      if (loginSuccess) {
        toast.success('Account created successfully!')
      }
      
      return loginSuccess
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Registration failed'
      toast.error(message)
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    isLoading.value = true
    try {
      await apiService.logout()
      user.value = null
      tokens.value = null
      toast.success('Logged out successfully')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function checkAuth() {
    if (isInitialized.value) return

    isLoading.value = true
    try {
      const token = localStorage.getItem('access_token')
      const storedUser = localStorage.getItem('user')

      if (token && storedUser) {
        tokens.value = {
          access_token: token,
          token_type: localStorage.getItem('token_type') || 'bearer',
          expires_in: 0
        }

        // Verify token is still valid by fetching current user
        const userData = await apiService.getCurrentUser()
        user.value = userData
      }
    } catch (error) {
      // Token is invalid, clear stored data
      await logout()
    } finally {
      isLoading.value = false
      isInitialized.value = true
    }
  }

  async function refreshUser() {
    if (!isAuthenticated.value) return

    try {
      const userData = await apiService.getCurrentUser()
      user.value = userData
    } catch (error) {
      console.error('Failed to refresh user data:', error)
      await logout()
    }
  }

  function updateUser(userData: Partial<User>) {
    if (user.value) {
      user.value = { ...user.value, ...userData }
      localStorage.setItem('user', JSON.stringify(user.value))
    }
  }

  // Reset store state
  function $reset() {
    user.value = null
    tokens.value = null
    isLoading.value = false
    isInitialized.value = false
  }

  return {
    // State
    user,
    tokens,
    isLoading,
    isInitialized,
    
    // Getters
    isAuthenticated,
    userName,
    
    // Actions
    login,
    register,
    logout,
    checkAuth,
    refreshUser,
    updateUser,
    $reset
  }
})
