import { useQuery } from '@tanstack/react-query'
import {
  fetchMapsJsConfig,
  mapsMapIdFromEnv,
  type MapsJsConfig,
} from '@/lib/maps-js-api'

export function useMapsJsConfig() {
  return useQuery({
    queryKey: ['maps-js-config'],
    queryFn: async (): Promise<MapsJsConfig & { mapId: string }> => {
      const cfg = await fetchMapsJsConfig()
      const envMapId = mapsMapIdFromEnv()
      return {
        ...cfg,
        mapId: envMapId || cfg.map_id,
      }
    },
    staleTime: 5 * 60_000,
    retry: 1,
    meta: { silent: true },
  })
}
