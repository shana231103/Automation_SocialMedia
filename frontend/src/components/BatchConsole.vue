<!-- File: frontend/src/components/BatchConsole.vue -->
<script setup>
import { ref, computed, onUpdated, nextTick } from 'vue'
import { getStatusBadgeClass } from '../utils/helpers.js'

const props = defineProps({
  batchAccounts: {
    type: Array,
    required: true
  },
  batchLogs: {
    type: Object,
    required: true
  },
  batchStatuses: {
    type: Object,
    required: true
  },
  batchProfiles: {
    type: Object,
    required: true
  },
  isBatchRunning: {
    type: Boolean,
    required: true
  }
})

// Track active tab: 'overview' or account ID
const activeTab = ref('overview')

// Calculate progress percentage
const progressStats = computed(() => {
  const total = props.batchAccounts.length
  if (total === 0) return { percent: 0, success: 0, error: 0, running: 0, queued: 0 }
  
  let success = 0
  let error = 0
  let running = 0
  let queued = 0
  
  props.batchAccounts.forEach(acc => {
    const status = props.batchStatuses[acc.id]
    if (status === 'success' || status === 'đã đăng nhập') success++
    else if (status === 'error' || status === 'dead' || status === 'checkpoint' || status === 'chưa đăng nhập') error++
    else if (status === 'running') running++
    else queued++
  })

  const completed = success + error
  const percent = Math.round((completed / total) * 100)
  
  return { percent, success, error, running, queued, total }
})

// Auto scroll logic for active terminal logs
const terminalLogsContainer = ref(null)
const scrollToBottom = () => {
  if (terminalLogsContainer.value) {
    terminalLogsContainer.value.scrollTop = terminalLogsContainer.value.scrollHeight
  }
}

onUpdated(() => {
  nextTick(() => {
    scrollToBottom()
  })
})
</script>

<template>
  <div class="lg:col-span-7 bg-zinc-900/60 border border-zinc-900 rounded-2xl p-5 shadow-xl flex flex-col h-[520px] backdrop-blur-sm">
    <!-- Tabs Header -->
    <div class="flex items-center gap-1.5 border-b border-zinc-800 pb-3 overflow-x-auto shrink-0 mb-4 pr-1">
      <button
        @click="activeTab = 'overview'"
        :class="activeTab === 'overview' ? 'bg-purple-600/15 border-purple-500/30 text-purple-400 font-semibold' : 'bg-transparent border-transparent text-zinc-400 hover:text-zinc-200'"
        class="px-3.5 py-1.5 rounded-lg border text-xs tracking-wide transition-all select-none shrink-0"
      >
        📊 Tổng quan
      </button>
      
      <button
        v-for="acc in batchAccounts"
        :key="acc.id"
        @click="activeTab = acc.id"
        :class="activeTab === acc.id ? 'bg-zinc-800 border-zinc-700 text-purple-400 font-semibold' : 'bg-transparent border-transparent text-zinc-400 hover:text-zinc-200'"
        class="px-3 py-1.5 rounded-lg border text-xs tracking-wide transition-all flex items-center gap-1.5 select-none shrink-0"
      >
        <span>{{ acc.platform === 'facebook' ? '📘' : acc.platform === 'youtube' ? '📺' : acc.platform === 'tiktok' ? '🎵' : '🐦' }}</span>
        <span class="truncate max-w-[80px]">{{ acc.username }}</span>
        
        <!-- Status indicator dot -->
        <span
          :class="{
            'bg-yellow-500 animate-pulse': batchStatuses[acc.id] === 'queued',
            'bg-blue-500 animate-pulse': batchStatuses[acc.id] === 'running',
            'bg-green-500': batchStatuses[acc.id] === 'success' || batchStatuses[acc.id] === 'đã đăng nhập',
            'bg-red-500': batchStatuses[acc.id] === 'error' || batchStatuses[acc.id] === 'dead' || batchStatuses[acc.id] === 'checkpoint'
          }"
          class="w-1.5 h-1.5 rounded-full inline-block"
        ></span>
      </button>
    </div>

    <!-- Active Tab Content -->
    <div class="flex-grow flex flex-col overflow-hidden min-h-0">
      
      <!-- Overview Tab -->
      <div v-if="activeTab === 'overview'" class="flex-grow flex flex-col overflow-y-auto space-y-4">
        <!-- Progress section -->
        <div class="bg-zinc-950/40 border border-zinc-900/60 p-4 rounded-xl">
          <div class="flex justify-between items-center text-xs font-semibold mb-2">
            <span class="text-zinc-400">TIẾN TRÌNH CHẠY HÀNG LOẠT</span>
            <span class="text-purple-400">{{ progressStats.percent }}%</span>
          </div>
          <!-- Progress bar -->
          <div class="w-full bg-zinc-900 rounded-full h-2 overflow-hidden mb-4">
            <div
              :style="{ width: progressStats.percent + '%' }"
              class="bg-gradient-to-r from-indigo-500 to-purple-500 h-full rounded-full transition-all duration-300"
            ></div>
          </div>
          
          <!-- Stat cards -->
          <div class="grid grid-cols-4 gap-2 text-center">
            <div class="p-2 bg-zinc-950 rounded-lg border border-zinc-900">
              <p class="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">Chờ</p>
              <p class="text-base font-bold mt-0.5 text-yellow-500">{{ progressStats.queued }}</p>
            </div>
            <div class="p-2 bg-zinc-950 rounded-lg border border-zinc-900">
              <p class="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">Chạy</p>
              <p class="text-base font-bold mt-0.5 text-blue-400">{{ progressStats.running }}</p>
            </div>
            <div class="p-2 bg-zinc-950 rounded-lg border border-zinc-900">
              <p class="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">Xong</p>
              <p class="text-base font-bold mt-0.5 text-green-500">{{ progressStats.success }}</p>
            </div>
            <div class="p-2 bg-zinc-950 rounded-lg border border-zinc-900">
              <p class="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">Lỗi</p>
              <p class="text-base font-bold mt-0.5 text-red-500">{{ progressStats.error }}</p>
            </div>
          </div>
        </div>

        <!-- Accounts Queue Table -->
        <div class="flex-grow overflow-x-auto min-h-0 bg-zinc-950/20 border border-zinc-900/60 rounded-xl">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="bg-zinc-950/60 border-b border-zinc-900 text-zinc-400 font-semibold">
                <th class="p-3">Tài khoản</th>
                <th class="p-3">Platform</th>
                <th class="p-3">Profile</th>
                <th class="p-3 text-right">Trạng thái</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-900/60">
              <tr v-for="acc in batchAccounts" :key="acc.id" class="hover:bg-zinc-950/30 transition-colors">
                <td class="p-3 font-medium text-zinc-200 truncate max-w-[150px]">{{ acc.username }}</td>
                <td class="p-3 capitalize text-zinc-400">{{ acc.platform }}</td>
                <td class="p-3 text-zinc-500 italic">{{ batchProfiles[acc.id] || 'Mặc định' }}</td>
                <td class="p-3 text-right">
                  <span
                    :class="getStatusBadgeClass(batchStatuses[acc.id] || 'queued')"
                    class="px-2 py-0.5 rounded text-[10px] font-semibold inline-block uppercase tracking-wider"
                  >
                    {{ batchStatuses[acc.id] || 'queued' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Account Logs Tab -->
      <div v-else class="flex-grow flex flex-col overflow-hidden min-h-0">
        <!-- Terminal Logs Container -->
        <div
          ref="terminalLogsContainer"
          class="flex-grow overflow-y-auto bg-zinc-950 rounded-xl border border-zinc-900/60 p-4 font-mono text-xs text-zinc-300 space-y-1.5 scroll-smooth"
        >
          <div v-if="!batchLogs[activeTab] || batchLogs[activeTab].length === 0" class="text-zinc-600 italic">
            Chưa có log sự kiện nào...
          </div>
          <div
            v-for="(log, idx) in batchLogs[activeTab] || []"
            :key="idx"
            :class="{
              'text-red-400': log.includes('[LỖI]') || log.includes('[ERROR]') || log.includes('Error') || log.includes('System Error'),
              'text-green-400 font-semibold': log.includes('[KẾT QUẢ]') || log.includes('[SUCCESS]'),
              'text-purple-400 font-semibold': log.includes('[HỆ THỐNG]')
            }"
            class="leading-relaxed break-words whitespace-pre-wrap"
          >
            {{ log }}
          </div>
        </div>
        
        <!-- Tab status indicator footer -->
        <div class="mt-2 flex items-center justify-between text-[11px] text-zinc-500 shrink-0">
          <span>Profile: {{ batchProfiles[activeTab] || 'Mặc định' }}</span>
          <span class="flex items-center gap-1.5 uppercase font-semibold">
            Trạng thái: 
            <span
              :class="getStatusBadgeClass(batchStatuses[activeTab] || 'queued')"
              class="px-1.5 py-0.2 rounded font-bold"
            >
              {{ batchStatuses[activeTab] || 'queued' }}
            </span>
          </span>
        </div>
      </div>

    </div>
  </div>
</template>
