export const getStatusBadgeClass = (status) => {
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

export const getPlatformColor = (plat) => {
  switch (plat) {
    case 'facebook': return 'text-blue-400 border-blue-500/20 bg-blue-500/5'
    case 'youtube': return 'text-red-400 border-red-500/20 bg-red-500/5'
    case 'tiktok': return 'text-cyan-400 border-cyan-500/20 bg-cyan-500/5'
    case 'twitter': return 'text-zinc-200 border-zinc-500/20 bg-zinc-500/5'
    default: return 'text-zinc-400 border-zinc-700'
  }
}
