<script setup>
import { getStatusBadgeClass, getPlatformColor } from '../utils/helpers.js'

defineProps({
  history: {
    type: Array,
    required: true
  },
  accounts: {
    type: Array,
    required: true
  }
})

defineEmits(['view-logs', 'refresh', 'clear'])
</script>

<template>
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
          <button @click="$emit('refresh')" class="text-xs bg-zinc-950 border border-zinc-800 hover:border-zinc-700 px-3 py-1.5 rounded-lg transition-colors font-medium">Làm mới</button>
          <button @click="$emit('clear')" class="text-xs bg-red-950/20 text-red-400 border border-red-900/20 hover:bg-red-900/20 px-3 py-1.5 rounded-lg transition-colors font-medium">Xóa lịch sử</button>
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
                  @click="$emit('view-logs', item)"
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
</template>
