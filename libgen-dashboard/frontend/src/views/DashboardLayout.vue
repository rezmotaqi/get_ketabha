<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Sidebar -->
    <Sidebar :open="sidebarOpen" @close="sidebarOpen = false" />
    
    <!-- Main content -->
    <div class="lg:pl-64 flex flex-col flex-1">
      <!-- Top navigation -->
      <div class="sticky top-0 z-10 lg:hidden pl-1 pt-1 sm:pl-3 sm:pt-3 bg-gray-50">
        <button
          type="button"
          class="-ml-0.5 -mt-0.5 h-12 w-12 inline-flex items-center justify-center rounded-md text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
          @click="sidebarOpen = true"
        >
          <span class="sr-only">Open sidebar</span>
          <Bars3Icon class="h-6 w-6" />
        </button>
      </div>
      
      <!-- Page header -->
      <header class="bg-white shadow-sm lg:static lg:overflow-y-visible">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div class="relative flex justify-between xl:grid xl:grid-cols-12 lg:gap-8">
            <div class="flex md:absolute md:left-0 md:inset-y-0 lg:static xl:col-span-2">
              <div class="flex-shrink-0 flex items-center">
                <h1 class="text-xl font-semibold text-gray-900">
                  {{ currentPageTitle }}
                </h1>
              </div>
            </div>
            
            <!-- Search bar (if on search page) -->
            <div class="min-w-0 flex-1 md:px-8 lg:px-0 xl:col-span-6" v-if="$route.name === 'Search'">
              <QuickSearch />
            </div>
            
            <!-- User menu -->
            <div class="flex items-center md:absolute md:right-0 md:inset-y-0 lg:static xl:col-span-4">
              <UserMenu />
            </div>
          </div>
        </div>
      </header>
      
      <!-- Main content area -->
      <main class="flex-1 overflow-y-auto">
        <div class="py-6">
          <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <router-view />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Bars3Icon } from '@heroicons/vue/24/outline'

// Import components (we'll create these)
import Sidebar from '@/components/layout/Sidebar.vue'
import UserMenu from '@/components/layout/UserMenu.vue'
import QuickSearch from '@/components/search/QuickSearch.vue'

const route = useRoute()
const sidebarOpen = ref(false)

const currentPageTitle = computed(() => {
  return route.meta.title?.toString().split(' - ')[0] || 'Dashboard'
})
</script>
