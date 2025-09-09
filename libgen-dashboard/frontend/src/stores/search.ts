import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useToast } from 'vue-toastification'
import apiService from '@/services/api'
import type { 
  Book, 
  BookSearchRequest, 
  DownloadLinksResponse,
  SearchHistory,
  BookFilters,
  SortOptions 
} from '@/types'

export const useSearchStore = defineStore('search', () => {
  // State
  const query = ref('')
  const results = ref<Book[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const totalResults = ref(0)
  const currentPage = ref(1)
  const resultsPerPage = ref(20)
  const searchHistory = ref<SearchHistory[]>([])
  const downloadLinks = ref<Record<string, DownloadLinksResponse>>({})
  const loadingLinks = ref<Set<string>>(new Set())
  
  // Filters and sorting
  const filters = ref<BookFilters>({})
  const sortOptions = ref<SortOptions>({
    field: 'relevance',
    direction: 'desc'
  })

  // Getters
  const totalPages = computed(() => 
    Math.ceil(totalResults.value / resultsPerPage.value)
  )

  const paginatedResults = computed(() => {
    const start = (currentPage.value - 1) * resultsPerPage.value
    const end = start + resultsPerPage.value
    return filteredAndSortedResults.value.slice(start, end)
  })

  const filteredAndSortedResults = computed(() => {
    let filtered = [...results.value]

    // Apply filters
    if (filters.value.extension?.length) {
      filtered = filtered.filter(book => 
        book.extension && filters.value.extension!.includes(book.extension)
      )
    }

    if (filters.value.language?.length) {
      filtered = filtered.filter(book => 
        book.language && filters.value.language!.includes(book.language)
      )
    }

    if (filters.value.yearRange) {
      const [minYear, maxYear] = filters.value.yearRange
      filtered = filtered.filter(book => {
        const year = parseInt(book.year || '0')
        return year >= minYear && year <= maxYear
      })
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const { field, direction } = sortOptions.value
      let aValue: any = a[field as keyof Book] || ''
      let bValue: any = b[field as keyof Book] || ''

      // Handle different field types
      if (field === 'year') {
        aValue = parseInt(aValue) || 0
        bValue = parseInt(bValue) || 0
      }

      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase()
        bValue = bValue.toLowerCase()
      }

      const comparison = aValue < bValue ? -1 : aValue > bValue ? 1 : 0
      return direction === 'asc' ? comparison : -comparison
    })

    return filtered
  })

  const hasFilters = computed(() => {
    return !!(
      filters.value.extension?.length ||
      filters.value.language?.length ||
      filters.value.yearRange
    )
  })

  const toast = useToast()

  // Actions
  async function searchBooks(searchRequest: BookSearchRequest) {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await apiService.searchBooks(searchRequest)
      
      query.value = searchRequest.query
      results.value = response.books
      totalResults.value = response.total_results
      currentPage.value = 1
      
      // Add to search history
      await loadSearchHistory()
      
      if (results.value.length === 0) {
        toast.warning('No books found for your search')
      } else {
        toast.success(`Found ${totalResults.value} books`)
      }
      
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Search failed'
      toast.error(error.value)
      results.value = []
      totalResults.value = 0
    } finally {
      isLoading.value = false
    }
  }

  async function getDownloadLinks(md5Hash: string, bookTitle: string = '') {
    if (downloadLinks.value[md5Hash]) {
      return downloadLinks.value[md5Hash]
    }

    loadingLinks.value.add(md5Hash)
    
    try {
      const response = await apiService.getDownloadLinks(md5Hash)
      downloadLinks.value[md5Hash] = response
      
      if (response.download_links.length === 0) {
        toast.warning(`No download links found for "${bookTitle}"`)
      }
      
      return response
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to get download links'
      toast.error(message)
      throw err
    } finally {
      loadingLinks.value.delete(md5Hash)
    }
  }

  async function loadSearchHistory(limit: number = 20) {
    try {
      searchHistory.value = await apiService.getSearchHistory(limit)
    } catch (err) {
      console.error('Failed to load search history:', err)
    }
  }

  async function clearSearchHistory() {
    try {
      // Clear all search history items
      for (const item of searchHistory.value) {
        await apiService.deleteSearchHistory(item.id)
      }
      searchHistory.value = []
      toast.success('Search history cleared')
    } catch (err) {
      toast.error('Failed to clear search history')
    }
  }

  function setPage(page: number) {
    if (page >= 1 && page <= totalPages.value) {
      currentPage.value = page
    }
  }

  function setResultsPerPage(count: number) {
    resultsPerPage.value = count
    currentPage.value = 1
  }

  function updateFilters(newFilters: Partial<BookFilters>) {
    filters.value = { ...filters.value, ...newFilters }
    currentPage.value = 1
  }

  function clearFilters() {
    filters.value = {}
    currentPage.value = 1
  }

  function updateSort(newSort: Partial<SortOptions>) {
    sortOptions.value = { ...sortOptions.value, ...newSort }
    currentPage.value = 1
  }

  function clearSearch() {
    query.value = ''
    results.value = []
    error.value = null
    totalResults.value = 0
    currentPage.value = 1
    downloadLinks.value = {}
    loadingLinks.value.clear()
  }

  // Get unique values for filter options
  const getUniqueExtensions = computed(() => {
    return [...new Set(results.value
      .map(book => book.extension)
      .filter(Boolean)
    )].sort()
  })

  const getUniqueLanguages = computed(() => {
    return [...new Set(results.value
      .map(book => book.language)
      .filter(Boolean)
    )].sort()
  })

  const getYearRange = computed(() => {
    const years = results.value
      .map(book => parseInt(book.year || '0'))
      .filter(year => year > 0)
    
    if (years.length === 0) return [1900, new Date().getFullYear()]
    
    return [Math.min(...years), Math.max(...years)]
  })

  // Reset store state
  function $reset() {
    query.value = ''
    results.value = []
    isLoading.value = false
    error.value = null
    totalResults.value = 0
    currentPage.value = 1
    resultsPerPage.value = 20
    searchHistory.value = []
    downloadLinks.value = {}
    loadingLinks.value.clear()
    filters.value = {}
    sortOptions.value = { field: 'relevance', direction: 'desc' }
  }

  return {
    // State
    query,
    results,
    isLoading,
    error,
    totalResults,
    currentPage,
    resultsPerPage,
    searchHistory,
    downloadLinks,
    loadingLinks,
    filters,
    sortOptions,
    
    // Getters
    totalPages,
    paginatedResults,
    filteredAndSortedResults,
    hasFilters,
    getUniqueExtensions,
    getUniqueLanguages,
    getYearRange,
    
    // Actions
    searchBooks,
    getDownloadLinks,
    loadSearchHistory,
    clearSearchHistory,
    setPage,
    setResultsPerPage,
    updateFilters,
    clearFilters,
    updateSort,
    clearSearch,
    $reset
  }
})
