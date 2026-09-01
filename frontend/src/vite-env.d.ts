/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USE_MOCKS?: string
  readonly VITE_SUPABASE_URL?: string
  readonly VITE_SUPABASE_ANON_KEY?: string
  readonly VITE_API_BASE?: string
  readonly VITE_API_BASES?: string
  readonly VITE_API_FALLBACK_BASE?: string
  readonly VITE_DEGUSTACAO_PROVIDER?: string
  readonly VITE_TURNSTILE_SITEKEY?: string
  readonly VITE_CARTO_BUILDER_EMBED_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
