import { createContext, useContext } from 'react'
import './explorar-chrome.css'

/** Fundo da rota mapa — carvão GymSite (app e site). */
export const EXPLORAR_PAGE = 'explorar-page'

/** Painéis sobre o mapa = paleta site (GYMSITE_PALETTE). */
export const EXPLORAR_CHROME = 'explorar-chrome'

/** Degustação chat canônica: https://www.gymsite.com.br/degustacao */
export const SITE_ORIGIN = 'https://www.gymsite.com.br'

export const ExplorarSiteContext = createContext(false)

export function useExplorarSite(): boolean {
  return useContext(ExplorarSiteContext)
}

/** Chrome sempre carvão+lime — o site (/degustacao) não é tema claro. */
export function explorarChrome(_site = false): string {
  return 'explorar-chrome'
}
