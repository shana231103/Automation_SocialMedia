<script setup>
defineProps({
  item: {
    type: Object,
    default: null
  }
})

defineEmits(['close'])
</script>

<template>
  <div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
      <!-- Modal Header -->
      <div class="border-b border-zinc-800 px-6 py-4 flex items-center justify-between bg-zinc-950/40">
        <div class="flex items-center gap-2">
          <span class="text-lg">📄</span>
          <div>
            <h3 class="font-bold text-zinc-200">Chi tiết nhật ký chạy (Logs)</h3>
            <p class="text-[10px] text-zinc-500" v-if="item">
              {{ new Date(item.created_at).toLocaleString() }} - Mạng xã hội: {{ item.platform.toUpperCase() }}
            </p>
          </div>
        </div>
        <button @click="$emit('close')" class="text-zinc-400 hover:text-white text-lg font-bold p-1">&times;</button>
      </div>
      
      <!-- Modal Body -->
      <div class="p-6 overflow-y-auto flex-grow bg-black font-mono text-[11px] leading-relaxed text-zinc-300 whitespace-pre-wrap max-h-[50vh]">
        {{ item?.run_logs || 'Không có bản ghi log nào.' }}
      </div>

      <!-- Modal Footer -->
      <div class="border-t border-zinc-800 px-6 py-4 flex items-center justify-end bg-zinc-950/40">
        <button
          @click="$emit('close')"
          class="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold px-4 py-2 rounded-xl text-xs transition-colors"
        >
          Đóng cửa sổ
        </button>
      </div>
    </div>
  </div>
</template>
