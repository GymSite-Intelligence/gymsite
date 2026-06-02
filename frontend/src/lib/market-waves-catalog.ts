/**
 * Catálogo de ondas — espelha data/market_waves.csv para UI offline.
 */
import type { MarketWave } from '@/types/domain'

export interface MarketWaveScenario {
  id: string
  wave: MarketWave
  tier_qwen: string
  cidade: string
  uf: string
  bairro: string
  golden_anchor?: string
  hypothesis: string
}

export const MARKET_WAVES_CATALOG: MarketWaveScenario[] = [
  {
    id: 'fortaleza_parangaba_red_w1',
    wave: 'red',
    tier_qwen: 'capital_bairro',
    cidade: 'Fortaleza',
    uf: 'CE',
    bairro: 'Parangaba',
    golden_anchor: 'fortaleza_parangaba_20260528',
    hypothesis: 'Saturação alta; ressalvas low-cost',
  },
  {
    id: 'fortaleza_meireles_red_w1',
    wave: 'red',
    tier_qwen: 'ultra_premium',
    cidade: 'Fortaleza',
    uf: 'CE',
    bairro: 'Meireles',
    golden_anchor: 'fortaleza_meireles_20260528',
    hypothesis: 'Mercado maduro litoral; ticket alto',
  },
  {
    id: 'fortaleza_aldeota_red_w1',
    wave: 'red',
    tier_qwen: 'premium_capital',
    cidade: 'Fortaleza',
    uf: 'CE',
    bairro: 'Aldeota',
    golden_anchor: 'fortaleza_aldeota_20260601',
    hypothesis: 'Premium saturado; redes fortes',
  },
  {
    id: 'curitiba_batel_red_w1',
    wave: 'red',
    tier_qwen: 'premium_capital',
    cidade: 'Curitiba',
    uf: 'PR',
    bairro: 'Batel',
    golden_anchor: 'curitiba_batel_20260512',
    hypothesis: 'Borda score; guerra preço',
  },
  {
    id: 'niteroi_camboinhas_red_w1',
    wave: 'red',
    tier_qwen: 'investigar',
    cidade: 'Niterói',
    uf: 'RJ',
    bairro: 'Camboinhas',
    golden_anchor: 'niteroi_camboinhas_20260513',
    hypothesis: 'Veredito negativo; tensão narrativa',
  },
  {
    id: 'fortaleza_cidade_red_w1',
    wave: 'red',
    tier_qwen: 'proxy_negativo',
    cidade: 'Fortaleza',
    uf: 'CE',
    bairro: 'Fortaleza',
    golden_anchor: 'fortaleza_cidade_inteira_20260527',
    hypothesis: 'Proxy investigar mais',
  },
  {
    id: 'fortaleza_eusebio_trans_w1',
    wave: 'transition',
    tier_qwen: 'primeiro_movimento',
    cidade: 'Fortaleza',
    uf: 'CE',
    bairro: 'Eusébio',
    golden_anchor: 'fortaleza_eusebio_20260529',
    hypothesis: 'RM expansão; oceano azul relativo',
  },
  {
    id: 'brasilia_aguas_claras_blue_w1',
    wave: 'blue',
    tier_qwen: 'low_cost_interior',
    cidade: 'Brasília',
    uf: 'DF',
    bairro: 'Águas Claras',
    golden_anchor: 'brasilia_ade_aguas_claras_setor_habitacional_arniqueira_20260512',
    hypothesis: 'Baixa saturação capital',
  },
  {
    id: 'anapolis_anapolis_city_blue_w1',
    wave: 'blue',
    tier_qwen: 'interior_capital',
    cidade: 'Anápolis',
    uf: 'GO',
    bairro: 'Anápolis City',
    golden_anchor: 'anapolis_anapolis_city_20260529',
    hypothesis: 'Low cost interior; ressalvas',
  },
  {
    id: 'altamira_altamira_blue_w1',
    wave: 'blue',
    tier_qwen: 'polo_regional',
    cidade: 'Altamira',
    uf: 'PA',
    bairro: 'Altamira',
    golden_anchor: 'altamira_altamira_20260529',
    hypothesis: 'Interior PA; potencial',
  },
]

export const WAVE_LABELS: Record<MarketWave, string> = {
  red: 'Oceano vermelho',
  transition: 'Transição',
  blue: 'Oceano azul',
}
