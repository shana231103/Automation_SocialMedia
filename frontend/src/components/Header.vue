<script setup>
defineProps({
  isRunning: {
    type: Boolean,
    required: true
  }
})
</script>

<template>
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
</template>
