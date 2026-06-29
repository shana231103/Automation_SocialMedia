<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  liveLogs: {
    type: Array,
    required: true
  },
  isRunning: {
    type: Boolean,
    required: true
  }
})

const consoleScrollContainer = ref(null)

// Automatically scroll to bottom when new logs are added
watch(() => props.liveLogs, () => {
  nextTick(() => {
    if (consoleScrollContainer.value) {
      consoleScrollContainer.value.scrollTop = consoleScrollContainer.value.scrollHeight
    }
  })
}, { deep: true })
</script>

<template>
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
</template>
