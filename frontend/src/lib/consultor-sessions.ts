import type { ChatMessageData } from '@/components/chat/ChatMessage'
import type { ConsultorProjeto } from '@/hooks/useConsultorChat'

const STORAGE_KEY = 'consultor-sessions-v1'

export interface ConsultorSessionItem {
  id: string
  title: string
  updatedAt: string
  status?: string
}

export interface ConsultorSessionCacheEntry {
  title: string
  updatedAt: string
  messagesSnapshot: ChatMessageData[]
  projetoSnapshot: ConsultorProjeto | null
}

export interface ConsultorSessionsStore {
  activeProjetoId: string | null
  cache: Record<string, ConsultorSessionCacheEntry>
}

function readStore(): ConsultorSessionsStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { activeProjetoId: null, cache: {} }
    const parsed = JSON.parse(raw) as ConsultorSessionsStore
    return {
      activeProjetoId: parsed.activeProjetoId ?? null,
      cache: parsed.cache ?? {},
    }
  } catch {
    return { activeProjetoId: null, cache: {} }
  }
}

function writeStore(store: ConsultorSessionsStore): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  } catch {
    /* quota / private mode */
  }
}

export function sessionTitleFromProjeto(projeto: ConsultorProjeto | null): string {
  if (!projeto?.localizacao) return 'Nova conversa'
  const { bairro, cidade, uf } = projeto.localizacao
  const parts = [bairro, cidade, uf].filter(Boolean)
  return parts.length ? parts.join(', ') : 'Nova conversa'
}

export function getActiveProjetoId(): string | null {
  return readStore().activeProjetoId
}

export function setActiveProjetoId(projetoId: string | null): void {
  const store = readStore()
  store.activeProjetoId = projetoId
  writeStore(store)
}

export function cacheSession(
  projetoId: string,
  messages: ChatMessageData[],
  projeto: ConsultorProjeto | null,
): void {
  const store = readStore()
  const title = sessionTitleFromProjeto(projeto)
  store.cache[projetoId] = {
    title,
    updatedAt: new Date().toISOString(),
    messagesSnapshot: messages,
    projetoSnapshot: projeto,
  }
  store.activeProjetoId = projetoId
  writeStore(store)
}

export function loadCachedSession(projetoId: string): ConsultorSessionCacheEntry | null {
  return readStore().cache[projetoId] ?? null
}

export function mergeServerSessions(
  serverItems: ConsultorSessionItem[],
): ConsultorSessionItem[] {
  const store = readStore()
  const byId = new Map<string, ConsultorSessionItem>()
  for (const item of serverItems) {
    byId.set(item.id, item)
  }
  for (const [id, entry] of Object.entries(store.cache)) {
    if (!byId.has(id)) {
      byId.set(id, {
        id,
        title: entry.title,
        updatedAt: entry.updatedAt,
        status: entry.projetoSnapshot?.status,
      })
    }
  }
  return [...byId.values()].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  )
}

export function downloadSessionJson(payload: {
  projeto: ConsultorProjeto | null
  projetoId: string | null
  messages: ChatMessageData[]
}): void {
  const stamp = new Date().toISOString().slice(0, 10)
  const idPart = payload.projetoId ?? 'draft'
  const blob = new Blob(
    [
      JSON.stringify(
        {
          exportedAt: new Date().toISOString(),
          projetoId: payload.projetoId,
          projeto: payload.projeto,
          messages: payload.messages,
        },
        null,
        2,
      ),
    ],
    { type: 'application/json' },
  )
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `gymsite-consultor-${idPart}-${stamp}.json`
  a.click()
  URL.revokeObjectURL(url)
}
