/**
 * Rastreia relatórios com pipeline em andamento (sessionStorage).
 * Sobrevive a navegação entre páginas e refresh — o monitor global continua polling.
 */
const STORAGE_KEY = 'gymsite_pipeline_watch'

export interface TrackedPipeline {
  id: string
  startedAt: number
  label?: string
}

function readAll(): TrackedPipeline[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as TrackedPipeline[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAll(items: TrackedPipeline[]) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export function getTrackedPipelines(): TrackedPipeline[] {
  return readAll()
}

export function trackPipeline(id: string, label?: string) {
  const items = readAll()
  if (items.some((x) => x.id === id)) return
  items.push({ id, startedAt: Date.now(), label })
  writeAll(items)
  window.dispatchEvent(new CustomEvent('gymsite:pipeline-watch-changed'))
}

export function untrackPipeline(id: string) {
  const next = readAll().filter((x) => x.id !== id)
  writeAll(next)
  window.dispatchEvent(new CustomEvent('gymsite:pipeline-watch-changed'))
}

export function subscribePipelineWatch(cb: () => void) {
  const handler = () => cb()
  window.addEventListener('gymsite:pipeline-watch-changed', handler)
  window.addEventListener('storage', handler)
  return () => {
    window.removeEventListener('gymsite:pipeline-watch-changed', handler)
    window.removeEventListener('storage', handler)
  }
}
