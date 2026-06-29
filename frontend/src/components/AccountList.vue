<script setup>
import { getStatusBadgeClass } from '../utils/helpers.js'

defineProps({
  accounts: {
    type: Array,
    required: true
  },
  isRunning: {
    type: Boolean,
    required: true
  },
  activeAccountRunning: {
    type: Object,
    default: null
  }
})

defineEmits(['run', 'delete', 'refresh'])
</script>

<template>
  <section class="bg-zinc-900/60 border border-zinc-900 rounded-2xl p-5 shadow-xl flex-grow flex flex-col overflow-hidden backdrop-blur-sm">
    <h2 class="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-4 flex items-center justify-between">
      <span class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-4 h-4 text-indigo-400">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.109A2.25 2.25 0 0 1 12.75 21.5h-1.5a2.25 2.25 0 0 1-2.25-2.263V19.13m4.786-3.07a9.348 9.348 0 0 0-2.286-1.161M14.214 16.06a9.338 9.338 0 0 0-4.12-.952 4.125 4.125 0 0 0-7.533 2.493M14.214 16.06a9.386 9.386 0 0 1-.786-3.07M10.82 12.24a4.21 4.21 0 1 1-2.25-3.816M13.25 10a4.25 4.25 0 1 1-8.5 0 4.25 4.25 0 0 1 8.5 0Z" />
        </svg>
        Danh sách tài khoản ({{ accounts.length }})
      </span>
      <button @click="$emit('refresh')" class="text-xs text-purple-400 hover:text-purple-300 font-medium">Làm mới</button>
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
            @click="$emit('run', acc)"
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
            @click="$emit('delete', acc.id)"
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
</template>
