<script setup>
import { ref, onMounted, nextTick } from 'vue'

// API endpoints (proxied via Vite)
const ACCOUNTS_API = '/api/accounts'
const HISTORY_API = '/api/history'

// Form state
const username = ref('')
const password = ref('')
const platform = ref('facebook')
const showPassword = ref(false)

// UI state
const accounts = ref([])
const history = ref([])
const isRunning = ref(false)
const activeAccountRunning = ref(null)
const liveLogs = ref([])
const consoleScrollContainer = ref(null)
const selectedHistoryLogs = ref(null) // For the log detail modal
const showLogsModal = ref(false)

// Fetch all accounts
const fetchAccounts = async () => {
  try {
    const res = await fetch(ACCOUNTS_API)
    if (res.ok) {
      accounts.value = await res.json()
    }
  } catch (error) {
    console.error('Error fetching accounts:', error)
  }
}

// Fetch execution history
const fetchHistory = async () => {
  try {
    const res = await fetch(HISTORY_API)
    if (res.ok) {
      history.value = await res.json()
    }
  } catch (error) {
    console.error('Error fetching history:', error)
  }
}

// Save account
const saveAccount = async () => {
  if (!username.value || !password.value) return
  
  try {
    const res = await fetch(ACCOUNTS_API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value,
        platform: platform.value
      })
    })
    
    if (res.ok) {
      // Clear form
      username.value = ''
      password.value = ''
      // Refresh list
      await fetchAccounts()
    } else {
      const err = await res.json()
      alert(`Lỗi: ${err.detail || 'Không thể lưu tài khoản'}`)
    }
  } catch (error) {
    console.error('Error saving account:', error)
    alert('Không thể kết nối đến server backend.')
  }
}

// Delete account
const deleteAccount = async (id) => {
  if (!confirm('Bạn có chắc chắn muốn xóa tài khoản này?')) return
  try {
    const res = await fetch(`${ACCOUNTS_API}/${id}`, {
      method: 'DELETE'
    })
    if (res.ok) {
      await fetchAccounts()
    }
  } catch (error) {
    console.error('Error deleting account:', error)
  }
}

// Run login automation (SSE stream)
const runLogin = (account) => {
  if (isRunning.value) return
  
  isRunning.value = true
  activeAccountRunning.value = account
  liveLogs.value = []
  liveLogs.value.push(`[HỆ THỐNG] Đang thiết lập phiên chạy cho ${account.platform}...`)
  
  const eventSource = new EventSource(`/api/run-login/${account.id}`)
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'log') {
        liveLogs.value.push(`[INFO] ${data.message}`)
      } else if (data.type === 'result') {
        liveLogs.value.push(`[KẾT QUẢ] Trạng thái đăng nhập được xác định: ${data.status.toUpperCase()}`)
      } else if (data.type === 'error') {
        liveLogs.value.push(`[LỖI] ${data.message}`)
        eventSource.close()
        isRunning.value = false
        activeAccountRunning.value = null
        fetchAccounts()
        fetchHistory()
      } else if (data.type === 'done') {
        liveLogs.value.push(`[HỆ THỐNG] Tiến trình tự động hóa hoàn tất. Đóng kết nối.`)
        eventSource.close()
        isRunning.value = false
        activeAccountRunning.value = null
        fetchAccounts()
        fetchHistory()
      }
      
      // Auto-scroll console to bottom
      nextTick(() => {
        if (consoleScrollContainer.value) {
          consoleScrollContainer.value.scrollTop = consoleScrollContainer.value.scrollHeight
        }
      })
    } catch (e) {
      console.error('Error parsing SSE event:', e)
    }
  }
  
  eventSource.onerror = (err) => {
    liveLogs.value.push(`[LỖI] Lỗi kết nối luồng dữ liệu thời gian thực (SSE).`)
    eventSource.close()
    isRunning.value = false
    activeAccountRunning.value = null
    fetchAccounts()
    fetchHistory()
  }
}

// Clear history log
const clearHistory = async () => {
  if (!confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử chạy?')) return
  try {
    const res = await fetch(`${HISTORY_API}/clear`, {
      method: 'POST'
    })
    if (res.ok) {
      await fetchHistory()
    }
  } catch (error) {
    console.error('Error clearing history:', error)
  }
}

// View details logs
const viewHistoryLogs = (item) => {
  selectedHistoryLogs.value = item
  showLogsModal.value = true
}

// Color badges for platform & status
const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'đã đăng nhập':
      return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
    case 'chưa đăng nhập':
      return 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
    case 'checkpoint':
      return 'bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-[0_0_8px_rgba(245,158,11,0.15)]'
    case 'dead':
      return 'bg-zinc-800 text-zinc-400 border border-zinc-700'
    default:
      return 'bg-zinc-800 text-zinc-400 border border-zinc-700'
  }
}

const getPlatformColor = (plat) => {
  switch (plat) {
    case 'facebook': return 'text-blue-400 border-blue-500/20 bg-blue-500/5'
    case 'youtube': return 'text-red-400 border-red-500/20 bg-red-500/5'
    case 'tiktok': return 'text-cyan-400 border-cyan-500/20 bg-cyan-500/5'
    case 'twitter': return 'text-zinc-200 border-zinc-500/20 bg-zinc-500/5'
    default: return 'text-zinc-400 border-zinc-700'
  }
}

onMounted(() => {
  fetchAccounts()
  fetchHistory()
})
</script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-purple-600 selection:text-white">
    <!-- Header -->
    <header class="border-b border-zinc-900 bg-zinc-900/40 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <!-- Automation Robot Icon -->
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-6 h-6 text-white animate-pulse">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" />
          </svg>
        </div>
        <div>
          <h1 class="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-indigo-400 tracking-wide">
            Social Media Login Automation
          </h1>
          <p class="text-xs text-zinc-400">Hệ thống kiểm tra & lưu trữ trạng thái đăng nhập mạng xã hội tự động</p>
        </div>
      </div>
      
      <!-- System status -->
      <div class="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-full px-3 py-1.5 text-xs text-zinc-300">
        <span class="relative flex h-2.5 w-2.5">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" :class="isRunning ? 'bg-amber-400' : 'bg-emerald-400'"></span>
          <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="isRunning ? 'bg-amber-500' : 'bg-emerald-500'"></span>
        </span>
        <span>{{ isRunning ? 'Đang chạy tự động hóa...' : 'Hệ thống sẵn sàng' }}</span>
      </div>
    </header>

    <!-- Main Grid -->
    <main class="flex-grow p-6 max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Left Column: Setup and Accounts -->
      <div class="lg:col-span-5 flex flex-col gap-6">
        
        <!-- Add Account Card -->
        <section class="bg-zinc-900/60 border border-zinc-900 rounded-2xl p-5 shadow-xl relative overflow-hidden backdrop-blur-sm">
          <div class="absolute -top-12 -right-12 w-24 h-24 bg-purple-500/5 rounded-full blur-2xl"></div>
          
          <h2 class="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-4 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-4 h-4 text-purple-400">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-9-4.5a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0ZM7.5 12a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 18.75a8.25 8.25 0 0 1-16.5 0V18a3.75 3.75 0 0 1 3.75-3.75h9a3.75 3.75 0 0 1 3.75 3.75v.75Z" />
            </svg>
            Cấu hình tài khoản mới
          </h2>

          <form @submit.prevent="saveAccount" class="space-y-4">
            <!-- Platform Selector -->
            <div>
              <label class="block text-xs text-zinc-400 mb-1.5 font-medium">Mạng xã hội</label>
              <div class="grid grid-cols-4 gap-2">
                <button
                  type="button"
                  @click="platform = 'facebook'"
                  :class="platform === 'facebook' ? 'border-blue-500 bg-blue-500/10 text-blue-400' : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700'"
                  class="flex flex-col items-center justify-center py-2.5 rounded-xl border text-xs font-semibold transition-all duration-200"
                >
                  <span class="text-lg mb-1">📘</span>
                  Facebook
                </button>
                <button
                  type="button"
                  @click="platform = 'youtube'"
                  :class="platform === 'youtube' ? 'border-red-500 bg-red-500/10 text-red-400' : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700'"
                  class="flex flex-col items-center justify-center py-2.5 rounded-xl border text-xs font-semibold transition-all duration-200"
                >
                  <span class="text-lg mb-1">📺</span>
                  YouTube
                </button>
                <button
                  type="button"
                  @click="platform = 'tiktok'"
                  :class="platform === 'tiktok' ? 'border-cyan-500 bg-cyan-500/10 text-cyan-400' : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700'"
                  class="flex flex-col items-center justify-center py-2.5 rounded-xl border text-xs font-semibold transition-all duration-200"
                >
                  <span class="text-lg mb-1">🎵</span>
                  TikTok
                </button>
                <button
                  type="button"
                  @click="platform = 'twitter'"
                  :class="platform === 'twitter' ? 'border-zinc-200 bg-white/10 text-zinc-100' : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700'"
                  class="flex flex-col items-center justify-center py-2.5 rounded-xl border text-xs font-semibold transition-all duration-200"
                >
                  <span class="text-lg mb-1">🐦</span>
                  Twitter / X
                </button>
              </div>
            </div>

            <!-- Username Input -->
            <div>
              <label class="block text-xs text-zinc-400 mb-1.5 font-medium">Tài khoản (Email / SĐT / Username)</label>
              <div class="relative">
                <input
                  v-model="username"
                  type="text"
                  required
                  placeholder="Nhập tên đăng nhập..."
                  class="w-full bg-zinc-950 border border-zinc-800 focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 rounded-xl px-3.5 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none transition-all"
                />
              </div>
            </div>

            <!-- Password Input -->
            <div>
              <label class="block text-xs text-zinc-400 mb-1.5 font-medium">Mật khẩu</label>
              <div class="relative">
                <input
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  placeholder="Nhập mật khẩu..."
                  class="w-full bg-zinc-950 border border-zinc-800 focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 rounded-xl pl-3.5 pr-10 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none transition-all"
                />
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  class="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  <span v-if="showPassword" class="text-xs">👁️</span>
                  <span v-else class="text-xs">👁️‍🗨️</span>
                </button>
              </div>
            </div>

            <button
              type="submit"
              class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium py-2 rounded-xl text-sm transition-all duration-300 shadow-lg shadow-purple-900/30 active:scale-[0.98]"
            >
              Lưu cấu hình tài khoản
            </button>
          </form>
        </section>

        <!-- Account List Card -->
        <section class="bg-zinc-900/60 border border-zinc-900 rounded-2xl p-5 shadow-xl flex-grow flex flex-col overflow-hidden backdrop-blur-sm">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-4 flex items-center justify-between">
            <span class="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-4 h-4 text-indigo-400">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.109A2.25 2.25 0 0 1 12.75 21.5h-1.5a2.25 2.25 0 0 1-2.25-2.263V19.13m4.786-3.07a9.348 9.348 0 0 0-2.286-1.161M14.214 16.06a9.338 9.338 0 0 0-4.12-.952 4.125 4.125 0 0 0-7.533 2.493M14.214 16.06a9.386 9.386 0 0 1-.786-3.07M10.82 12.24a4.21 4.21 0 1 1-2.25-3.816M13.25 10a4.25 4.25 0 1 1-8.5 0 4.25 4.25 0 0 1 8.5 0Z" />
              </svg>
              Danh sách tài khoản ({{ accounts.length }})
            </span>
            <button @click="fetchAccounts" class="text-xs text-purple-400 hover:text-purple-300 font-medium">Làm mới</button>
          </h2>

          <!-- Account Items Container -->
          <div class="space-y-2.5 overflow-y-auto flex-grow max-h-[320px] pr-1.5">
            <div v-if="accounts.length === 0" class="text-center py-8 text-zinc-600 text-xs">
              Chưa có tài khoản nào được lưu cấu hình.
            </div>
            
            <div
              v-for="acc in accounts"
              :key="acc.id"
              class="flex items-center justify-between p-3 rounded-xl bg-zinc-950/40 border border-zinc-900/60 hover:border-zinc-800/80 transition-all duration-200"
            >
              <div class="flex items-center gap-3 min-w-0">
                <!-- Platform Indicator -->
                <span class="text-lg px-2 py-1 bg-zinc-900 rounded-lg">{{ acc.platform === 'facebook' ? '📘' : acc.platform === 'youtube' ? '📺' : acc.platform === 'tiktok' ? '🎵' : '🐦' }}</span>
                <div class="min-w-0">
                  <p class="text-sm font-semibold truncate text-zinc-200">{{ acc.username }}</p>
                  <div class="flex items-center gap-2 mt-1">
                    <span :class="getStatusBadgeClass(acc.status)" class="px-2 py-0.5 rounded text-[10px] font-medium tracking-wide">
                      {{ acc.status }}
                    </span>
                    <span v-if="acc.last_checked_at" class="text-[10px] text-zinc-500">
                      {{ new Date(acc.last_checked_at).toLocaleTimeString() }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Action button for running / deleting -->
              <div class="flex items-center gap-1.5 shrink-0">
                <button
                  @click="runLogin(acc)"
                  :disabled="isRunning"
                  :class="isRunning ? 'bg-zinc-800 text-zinc-600 cursor-not-allowed' : 'bg-purple-600/10 hover:bg-purple-600 text-purple-400 hover:text-white border border-purple-500/20'"
                  class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200"
                >
                  <svg v-if="isRunning && activeAccountRunning?.id === acc.id" class="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-3.5 h-3.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                  </svg>
                  <span>Chạy</span>
                </button>
                <button
                  @click="deleteAccount(acc.id)"
                  :disabled="isRunning"
                  class="p-2 rounded-lg bg-zinc-950 hover:bg-red-500/10 text-zinc-500 hover:text-red-400 border border-zinc-900 transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-3.5 h-3.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </section>

      </div>

      <!-- Right Column: Live Logs Console -->
      <div class="lg:col-span-7 flex flex-col bg-zinc-900/60 border border-zinc-900 rounded-2xl p-5 shadow-xl backdrop-blur-sm overflow-hidden min-h-[450px] lg:min-h-0">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-4 flex items-center justify-between">
          <span class="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-4 h-4 text-emerald-400">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
            </svg>
            Bảng điều khiển trực tiếp (Real-time Console)
          </span>
          <span v-if="isRunning" class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
          </span>
        </h2>

        <!-- Terminal Output -->
        <div
          ref="consoleScrollContainer"
          class="flex-grow bg-black border border-zinc-900 rounded-xl p-4 font-mono text-[11px] leading-relaxed text-zinc-300 overflow-y-auto space-y-1.5 shadow-inner"
        >
          <div v-if="liveLogs.length === 0" class="text-zinc-600 italic">
            Chưa có tiến trình nào đang chạy. Hãy click nút "Chạy" ở một tài khoản bất kỳ để bắt đầu tự động đăng nhập.
          </div>
          
          <div v-for="(log, idx) in liveLogs" :key="idx" class="whitespace-pre-wrap">
            <span v-if="log.startsWith('[INFO]')" class="text-blue-400 font-semibold">{{ log.substring(0, 6) }}</span>
            <span v-else-if="log.startsWith('[KẾT QUẢ]')" class="text-emerald-400 font-bold">{{ log.substring(0, 9) }}</span>
            <span v-else-if="log.startsWith('[LỖI]')" class="text-red-400 font-bold">{{ log.substring(0, 5) }}</span>
            <span v-else-if="log.startsWith('[HỆ THỐNG]')" class="text-purple-400 font-bold">{{ log.substring(0, 10) }}</span>
            
            <span v-if="log.startsWith('[INFO]')" class="text-zinc-300">{{ log.substring(6) }}</span>
            <span v-else-if="log.startsWith('[KẾT QUẢ]')" class="text-zinc-100">{{ log.substring(9) }}</span>
            <span v-else-if="log.startsWith('[LỖI]')" class="text-red-300">{{ log.substring(5) }}</span>
            <span v-else-if="log.startsWith('[HỆ THỐNG]')" class="text-purple-200">{{ log.substring(10) }}</span>
            <span v-else class="text-zinc-400">{{ log }}</span>
          </div>
        </div>

        <div class="mt-4 p-3 bg-zinc-950 rounded-xl border border-zinc-900 text-[11px] text-zinc-400 flex flex-col gap-1.5">
          <p class="font-bold text-zinc-300">💡 Hướng dẫn vận hành:</p>
          <ul class="list-disc list-inside space-y-0.5">
            <li>Nút "Chạy" sẽ khởi chạy luồng tự động hóa mở Chrome kiểm tra.</li>
            <li>Nếu phát hiện CAPTCHA (đặc biệt là TikTok), hãy giải tay trực tiếp trên trình duyệt Chrome vừa mở.</li>
            <li>Trình duyệt sẽ hiển thị trên màn hình của bạn và tự động đóng sau khi hoàn tất.</li>
          </ul>
        </div>
      </div>

    </main>

    <!-- Bottom History Section -->
    <section class="p-6 max-w-7xl w-full mx-auto">
      <div class="bg-zinc-900/60 border border-zinc-900 rounded-2xl p-5 shadow-xl backdrop-blur-sm">
        <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-4 h-4 text-pink-400">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            Lịch sử tự động đăng nhập (Đã lưu database)
          </h2>
          <div class="flex items-center gap-2">
            <button @click="fetchHistory" class="text-xs bg-zinc-950 border border-zinc-800 hover:border-zinc-700 px-3 py-1.5 rounded-lg transition-colors font-medium">Làm mới</button>
            <button @click="clearHistory" class="text-xs bg-red-950/20 text-red-400 border border-red-900/20 hover:bg-red-900/20 px-3 py-1.5 rounded-lg transition-colors font-medium">Xóa lịch sử</button>
          </div>
        </div>

        <!-- History Table -->
        <div class="overflow-x-auto border border-zinc-900/80 rounded-xl">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="bg-zinc-950/80 border-b border-zinc-900 text-zinc-400 uppercase tracking-wider font-semibold">
                <th class="p-3">Tài khoản</th>
                <th class="p-3">Mạng xã hội</th>
                <th class="p-3">Thời gian chạy</th>
                <th class="p-3">Kết quả</th>
                <th class="p-3 text-right">Chi tiết</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-900/40 bg-zinc-950/20">
              <tr v-if="history.length === 0">
                <td colspan="5" class="p-8 text-center text-zinc-600">Lịch sử chạy trống.</td>
              </tr>
              <tr v-for="item in history" :key="item.id" class="hover:bg-zinc-900/10 transition-colors">
                <td class="p-3 font-medium text-zinc-300">{{ item.account_id ? accounts.find(a => a.id === item.account_id)?.username || 'Tài khoản đã xóa' : 'Tài khoản đã xóa' }}</td>
                <td class="p-3">
                  <span :class="getPlatformColor(item.platform)" class="px-2 py-0.5 border rounded font-medium text-[10px] uppercase">
                    {{ item.platform }}
                  </span>
                </td>
                <td class="p-3 text-zinc-400">{{ new Date(item.created_at).toLocaleString() }}</td>
                <td class="p-3">
                  <span :class="getStatusBadgeClass(item.status)" class="px-2 py-0.5 rounded font-semibold text-[10px]">
                    {{ item.status }}
                  </span>
                </td>
                <td class="p-3 text-right">
                  <button
                    @click="viewHistoryLogs(item)"
                    class="text-xs text-purple-400 hover:text-purple-300 font-semibold underline px-2 py-1"
                  >
                    Xem Log
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Modal: View Detailed Logs -->
    <div v-if="showLogsModal" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        <!-- Modal Header -->
        <div class="border-b border-zinc-800 px-6 py-4 flex items-center justify-between bg-zinc-950/40">
          <div class="flex items-center gap-2">
            <span class="text-lg">📄</span>
            <div>
              <h3 class="font-bold text-zinc-200">Chi tiết nhật ký chạy (Logs)</h3>
              <p class="text-[10px] text-zinc-500">{{ new Date(selectedHistoryLogs?.created_at).toLocaleString() }} - Mạng xã hội: {{ selectedHistoryLogs?.platform.toUpperCase() }}</p>
            </div>
          </div>
          <button @click="showLogsModal = false" class="text-zinc-400 hover:text-white text-lg font-bold p-1">&times;</button>
        </div>
        
        <!-- Modal Body -->
        <div class="p-6 overflow-y-auto flex-grow bg-black font-mono text-[11px] leading-relaxed text-zinc-300 whitespace-pre-wrap max-h-[50vh]">
          {{ selectedHistoryLogs?.run_logs || 'Không có bản ghi log nào.' }}
        </div>

        <!-- Modal Footer -->
        <div class="border-t border-zinc-800 px-6 py-4 flex items-center justify-end bg-zinc-950/40">
          <button
            @click="showLogsModal = false"
            class="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold px-4 py-2 rounded-xl text-xs transition-colors"
          >
            Đóng cửa sổ
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* Custom styled scrollbars for a premium dark terminal look */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #27272a;
  border-radius: 9999px;
}
::-webkit-scrollbar-thumb:hover {
  background: #3f3f46;
}
</style>
