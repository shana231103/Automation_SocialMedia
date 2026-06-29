<script setup>
import { ref, onMounted } from 'vue'
import Header from './components/Header.vue'
import AccountForm from './components/AccountForm.vue'
import AccountList from './components/AccountList.vue'
import ConsoleTerminal from './components/ConsoleTerminal.vue'
import HistoryTable from './components/HistoryTable.vue'
import LogsModal from './components/LogsModal.vue'

// API endpoints (proxied via Vite)
const ACCOUNTS_API = '/api/accounts'
const HISTORY_API = '/api/history'

// UI state
const accounts = ref([])
const history = ref([])
const isRunning = ref(false)
const activeAccountRunning = ref(null)
const liveLogs = ref([])
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
const saveAccount = async ({ username, password, platform }) => {
  try {
    const res = await fetch(ACCOUNTS_API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        password,
        platform
      })
    })
    
    if (res.ok) {
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

onMounted(() => {
  fetchAccounts()
  fetchHistory()
})
</script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-purple-600 selection:text-white">
    <!-- Header -->
    <Header :is-running="isRunning" />

    <!-- Main Grid -->
    <main class="flex-grow p-6 max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Left Column: Setup and Accounts -->
      <div class="lg:col-span-5 flex flex-col gap-6">
        <!-- Add Account Card -->
        <AccountForm @save="saveAccount" />

        <!-- Account List Card -->
        <AccountList
          :accounts="accounts"
          :is-running="isRunning"
          :active-account-running="activeAccountRunning"
          @run="runLogin"
          @delete="deleteAccount"
          @refresh="fetchAccounts"
        />
      </div>

      <!-- Right Column: Live Logs Console -->
      <ConsoleTerminal
        :live-logs="liveLogs"
        :is-running="isRunning"
      />

    </main>

    <!-- Bottom History Section -->
    <HistoryTable
      :history="history"
      :accounts="accounts"
      @view-logs="viewHistoryLogs"
      @refresh="fetchHistory"
      @clear="clearHistory"
    />

    <!-- Modal: View Detailed Logs -->
    <LogsModal
      v-if="showLogsModal"
      :item="selectedHistoryLogs"
      @close="showLogsModal = false"
    />
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
