/**
 * URL do proxy Places (FastAPI em prod/dev; Vite middleware só se API_BASE vazio).
 */
import { API_BASE } from '@/lib/supabase'

export const PLACES_AUTOCOMPLETE_URL = `${API_BASE.replace(/\/$/, '')}/api/places-autocomplete`
