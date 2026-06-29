<script setup>
import { ref } from 'vue'

const emit = defineEmits(['save'])

const username = ref('')
const password = ref('')
const platform = ref('facebook')
const showPassword = ref(false)

const submitForm = () => {
  if (!username.value || !password.value) return
  emit('save', {
    username: username.value,
    password: password.value,
    platform: platform.value
  })
  // Clear sensitive fields after save event emission
  username.value = ''
  password.value = ''
}
</script>

<template>
  <section class="bg-zinc-900/60 border border-zinc-900 rounded-2xl p-5 shadow-xl relative overflow-hidden backdrop-blur-sm">
    <div class="absolute -top-12 -right-12 w-24 h-24 bg-purple-500/5 rounded-full blur-2xl"></div>
    
    <h2 class="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-4 flex items-center gap-2">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-4 h-4 text-purple-400">
        <path stroke-linecap="round" stroke-linejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-9-4.5a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0ZM7.5 12a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 18.75a8.25 8.25 0 0 1-16.5 0V18a3.75 3.75 0 0 1 3.75-3.75h9a3.75 3.75 0 0 1 3.75 3.75v.75Z" />
      </svg>
      Cấu hình tài khoản mới
    </h2>

    <form @submit.prevent="submitForm" class="space-y-4">
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
</template>
