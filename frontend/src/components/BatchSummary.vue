<!-- File: frontend/src/components/BatchSummary.vue -->
<script setup>
import { ref } from 'vue'
import { getStatusBadgeClass } from '../utils/helpers.js'

defineProps({
  summary: {
    type: Object,
    required: true
  }
})

defineEmits(['close'])

const activeLogsAccount = ref(null)

const showLogs = (accountDetail) => {
  activeLogsAccount.value = accountDetail
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-sm">
    <!-- Modal Box -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl">
      <!-- Modal Header -->
      <div class="p-5 border-b border-zinc-800 flex items-center justify-between shrink-0 bg-zinc-950/20">
        <h3 class="text-sm font-semibold uppercase tracking-wider text-purple-400 flex items-center gap-2">
          🏁 Kết quả chạy hàng loạt
        </h3>
        <button @click="$emit('close')" class="text-zinc-500 hover:text-zinc-300 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-6 flex-grow overflow-y-auto space-y-5 min-h-0 text-xs">
        
        <!-- Summary Stats Card -->
        <div class="grid grid-cols-3 gap-4 bg-zinc-950/40 p-4 rounded-xl border border-zinc-850">
          <div class="text-center">
            <p class="text-zinc-500 uppercase font-medium text-[9px] tracking-wider">Tổng cộng</p>
            <p class="text-lg font-bold text-zinc-350 mt-1">{{ summary.total }}</p>
          </div>
          <div class="text-center border-x border-zinc-800/80">
            <p class="text-zinc-500 uppercase font-medium text-[9px] tracking-wider text-green-500">Thành công</p>
            <p class="text-lg font-bold text-green-400 mt-1">{{ summary.success_count }}</p>
          </div>
          <div class="text-center">
            <p class="text-zinc-500 uppercase font-medium text-[9px] tracking-wider text-red-500">Thất bại / Lỗi</p>
            <p class="text-lg font-bold text-red-400 mt-1">{{ summary.error_count }}</p>
          </div>
        </div>

        <!-- Details Table -->
        <div class="border border-zinc-800 rounded-xl overflow-hidden bg-zinc-950/20">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-zinc-950/60 border-b border-zinc-800 text-zinc-400 font-semibold">
                <th class="p-3">Tài khoản</th>
                <th class="p-3">Nền tảng</th>
                <th class="p-3">Kết quả</th>
                <th class="p-3 text-right">Chi tiết</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-900">
              <tr v-for="(detail, aid) in summary.details" :key="aid" class="hover:bg-zinc-950/30 transition-colors">
                <td class="p-3 font-medium text-zinc-200 truncate max-w-[160px]">{{ detail.username }}</td>
                <td class="p-3 capitalize text-zinc-400">{{ detail.platform }}</td>
                <td class="p-3">
                  <span
                    :class="getStatusBadgeClass(detail.status)"
                    class="px-2 py-0.5 rounded text-[10px] font-semibold inline-block uppercase"
                  >
                    {{ detail.status }}
                  </span>
                </td>
                <td class="p-3 text-right">
                  <button
                    @click="showLogs(detail)"
                    class="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-purple-400 font-medium transition-colors"
                  >
                    Xem Log
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Inner log detail section if clicked -->
        <div v-if="activeLogsAccount" class="border border-zinc-850 rounded-xl p-4 bg-zinc-950 flex flex-col space-y-2.5">
          <div class="flex items-center justify-between text-zinc-400 font-semibold">
            <span>NHẬT KÝ CHI TIẾT: {{ activeLogsAccount.username }}</span>
            <button @click="activeLogsAccount = null" class="text-xs text-red-400 hover:text-red-300">Đóng</button>
          </div>
          <pre class="bg-black/40 border border-zinc-900 rounded-lg p-3 font-mono text-[10px] max-h-[160px] overflow-y-auto text-zinc-300 whitespace-pre-wrap select-text">{{ activeLogsAccount.logs }}</pre>
        </div>

      </div>

      <!-- Modal Footer -->
      <div class="p-5 border-t border-zinc-800 flex items-center justify-end shrink-0 bg-zinc-950/20">
        <button
          @click="$emit('close')"
          class="bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs px-5 py-2.5 rounded-xl transition-all duration-200"
        >
          Hoàn thành
        </button>
      </div>
    </div>
  </div>
</template>
