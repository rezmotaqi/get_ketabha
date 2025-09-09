import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Lazy load components for better performance
const DashboardLayout = () => import('@/views/DashboardLayout.vue')
const Login = () => import('@/views/Login.vue')
const Register = () => import('@/views/Register.vue')
const Dashboard = () => import('@/views/Dashboard.vue')
const Search = () => import('@/views/Search.vue')
const Bookmarks = () => import('@/views/Bookmarks.vue')
const Profile = () => import('@/views/Profile.vue')
const Settings = () => import('@/views/Settings.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/login',
      name: 'Login',
      component: Login,
      meta: { 
        requiresGuest: true,
        title: 'Login - LibGen Dashboard'
      }
    },
    {
      path: '/register',
      name: 'Register', 
      component: Register,
      meta: { 
        requiresGuest: true,
        title: 'Register - LibGen Dashboard'
      }
    },
    {
      path: '/app',
      component: DashboardLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/app/dashboard'
        },
        {
          path: '/dashboard',
          name: 'Dashboard',
          component: Dashboard,
          alias: '/app/dashboard',
          meta: { 
            title: 'Dashboard - LibGen',
            icon: 'home'
          }
        },
        {
          path: '/search',
          name: 'Search',
          component: Search,
          alias: '/app/search',
          meta: { 
            title: 'Search Books - LibGen',
            icon: 'search'
          }
        },
        {
          path: '/bookmarks',
          name: 'Bookmarks',
          component: Bookmarks,
          alias: '/app/bookmarks',
          meta: { 
            title: 'My Bookmarks - LibGen',
            icon: 'bookmark'
          }
        },
        {
          path: '/profile',
          name: 'Profile',
          component: Profile,
          alias: '/app/profile',
          meta: { 
            title: 'Profile - LibGen',
            icon: 'user'
          }
        },
        {
          path: '/settings',
          name: 'Settings',
          component: Settings,
          alias: '/app/settings',
          meta: { 
            title: 'Settings - LibGen',
            icon: 'cog'
          }
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFound.vue'),
      meta: {
        title: 'Page Not Found - LibGen Dashboard'
      }
    }
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // Wait for auth initialization
  if (!authStore.isInitialized) {
    await authStore.checkAuth()
  }

  // Set page title
  if (to.meta.title) {
    document.title = to.meta.title as string
  }

  // Check authentication requirements
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if not authenticated
    next({ 
      name: 'Login', 
      query: { redirect: to.fullPath }
    })
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    // Redirect to dashboard if already authenticated
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

// Global after hook for loading states
router.afterEach((to, from) => {
  // Could add analytics tracking here
  console.log(`Navigated to ${to.path}`)
})

export default router
