/**
 * Kits de Academia Tradicional — PP/P/M/G/GG.
 *
 * Curva típica:
 * - PP (~300m², Smart Fit Express): operação enxuta, sem spinning, sem premium
 * - P (~600m², Selfit P): cardio + musculação básica, sem aulas coletivas
 * - M (~1000m², Smart Fit Standard): kit completo padrão de mercado ★
 * - G (~2000m², Bodytech entry): adiciona Pilates room + premium plates
 * - GG (~4000m², Bodytech flagship): tudo + piscina-deck + multi-arena
 *
 * Fontes: Movement Catálogo 2024, ACAD Guia, Smart Fit SMFT3 releases.
 */
import type { KitEquipamentos } from './types'

export const ACADEMIA_PP: KitEquipamentos = {
  tipo_negocio: 'academia',
  tamanho_preset: 'pp',
  area_referencia_m2: 300,
  modelo_operacao: 'Smart Fit Express / Mini Studio (modelo express, sem spinning)',
  desconto_volume_pct: [0.10, 0.20],
  fontes: ['Movement Catálogo 2024', 'Smart Fit SMFT3 2024'],
  itens: [
    // Cardio compacto (10 unidades)
    { cat: 'cardio', nome: 'Esteira profissional', qtd: 4, ref: 'Movement RT200', preco_un: 9800, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Bike vertical (upright)', qtd: 3, ref: 'Movement BR200', preco_un: 5500, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Elíptico', qtd: 2, ref: 'Movement EL500', preco_un: 8200, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Remo ergômetro', qtd: 1, ref: 'Concept2 Model D', preco_un: 8400, fornecedor: 'Concept2' },

    // Musculação seletorizada — 6 estações essenciais
    { cat: 'musc_superior', nome: 'Crossover (polia dupla)', qtd: 1, ref: 'Movement CX200', preco_un: 18500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Puxador frontal', qtd: 1, ref: 'Movement LP100', preco_un: 11200, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Supino reto seletorizado', qtd: 1, ref: 'Movement BP100', preco_un: 12500, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Leg press 45°', qtd: 1, ref: 'Movement LP45', preco_un: 18500, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira extensora', qtd: 1, ref: 'Movement EX100', preco_un: 9200, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira flexora sentada', qtd: 1, ref: 'Movement FL100', preco_un: 9200, fornecedor: 'Movement' },

    // Plate-loaded mínimo
    { cat: 'livre', nome: 'Squat rack', qtd: 1, ref: 'Movement SR100', preco_un: 7200, fornecedor: 'Movement' },
    { cat: 'livre', nome: 'Banco supino ajustável', qtd: 2, ref: 'Movement BS300', preco_un: 2800, fornecedor: 'Movement' },

    // Pesos
    { cat: 'pesos', nome: 'Kit halteres 1-30kg (par)', qtd: 1, ref: 'RHS borracha', preco_un: 22000, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Kit anilhas (300kg variado)', qtd: 1, ref: 'RHS Olímpico', preco_un: 16000, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Barras olímpicas 20kg', qtd: 3, ref: 'RHS 1500mm', preco_un: 850, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Rack porta-anilhas', qtd: 1, ref: 'RHS RP200', preco_un: 1900, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Rack porta-halteres', qtd: 1, ref: 'RHS RH200', preco_un: 2800, fornecedor: 'RHS' },

    // Funcional + acessórios mínimo
    { cat: 'funcional', nome: 'Rig multi-grip 2 estações', qtd: 1, ref: 'Movement RG200', preco_un: 9500, fornecedor: 'Movement' },
    { cat: 'core', nome: 'Banco abdominal ajustável', qtd: 1, ref: 'Movement BA100', preco_un: 1800, fornecedor: 'Movement' },
  ],
}

export const ACADEMIA_P: KitEquipamentos = {
  tipo_negocio: 'academia',
  tamanho_preset: 'p',
  area_referencia_m2: 600,
  modelo_operacao: 'Selfit P / Just Fit (cardio + musculação básica)',
  desconto_volume_pct: [0.15, 0.25],
  fontes: ['Movement Catálogo 2024', 'ACAD Guia 2024'],
  itens: [
    // Cardio (18 unidades)
    { cat: 'cardio', nome: 'Esteira profissional', qtd: 6, ref: 'Movement RT300', preco_un: 12500, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Bike vertical', qtd: 4, ref: 'Movement BR300', preco_un: 6200, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Bike horizontal (recumbent)', qtd: 2, ref: 'Movement BR200', preco_un: 7500, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Elíptico', qtd: 3, ref: 'Movement EL700', preco_un: 10800, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Transport (escada)', qtd: 1, ref: 'Movement TP500', preco_un: 18900, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Remo ergômetro', qtd: 2, ref: 'Concept2 Model D', preco_un: 8400, fornecedor: 'Concept2' },

    // Musculação superior — 8 estações
    { cat: 'musc_superior', nome: 'Crossover (polia dupla)', qtd: 1, ref: 'Movement CX300', preco_un: 22500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Puxador frontal', qtd: 1, ref: 'Movement LP100', preco_un: 11200, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Remada sentada', qtd: 1, ref: 'Movement RS100', preco_un: 11500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Supino reto seletorizado', qtd: 1, ref: 'Movement BP100', preco_un: 12500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Supino inclinado', qtd: 1, ref: 'Movement BI100', preco_un: 12500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Peck deck (peitoral)', qtd: 1, ref: 'Movement PD100', preco_un: 11800, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Desenvolvimento ombros', qtd: 1, ref: 'Movement SP100', preco_un: 12100, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Rosca scott seletorizada', qtd: 1, ref: 'Movement BC100', preco_un: 9800, fornecedor: 'Movement' },

    // Musculação inferior — 7 estações
    { cat: 'musc_inferior', nome: 'Leg press 45°', qtd: 1, ref: 'Movement LP45', preco_un: 18500, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Hack squat', qtd: 1, ref: 'Movement HS100', preco_un: 16200, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira extensora', qtd: 1, ref: 'Movement EX100', preco_un: 9200, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira flexora sentada', qtd: 1, ref: 'Movement FL100', preco_un: 9200, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira adutora', qtd: 1, ref: 'Movement AD100', preco_un: 8500, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira abdutora', qtd: 1, ref: 'Movement AB100', preco_un: 8500, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Panturrilha em pé', qtd: 1, ref: 'Movement PE100', preco_un: 8900, fornecedor: 'Movement' },

    // Glúteo
    { cat: 'gluteo', nome: 'Glute drive (hip thrust)', qtd: 1, ref: 'Movement GD100', preco_un: 13500, fornecedor: 'Movement' },

    // Core
    { cat: 'core', nome: 'Cadeira abdominal', qtd: 1, ref: 'Movement CA100', preco_un: 8200, fornecedor: 'Movement' },
    { cat: 'core', nome: 'Banco abdominal ajustável', qtd: 2, ref: 'Movement BA100', preco_un: 1800, fornecedor: 'Movement' },

    // Livre
    { cat: 'livre', nome: 'Squat rack', qtd: 1, ref: 'Movement SR200', preco_un: 8500, fornecedor: 'Movement' },
    { cat: 'livre', nome: 'Smith machine', qtd: 1, ref: 'Movement SM300', preco_un: 14800, fornecedor: 'Movement' },
    { cat: 'livre', nome: 'Banco supino reto', qtd: 2, ref: 'Movement BS100', preco_un: 2200, fornecedor: 'Movement' },

    // Pesos
    { cat: 'pesos', nome: 'Kit halteres 1-40kg (par)', qtd: 1, ref: 'RHS borracha', preco_un: 28000, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Kit anilhas (450kg variado)', qtd: 1, ref: 'RHS Olímpico', preco_un: 22000, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Barras olímpicas 20kg', qtd: 4, ref: 'RHS 1500mm', preco_un: 850, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Rack porta-anilhas', qtd: 2, ref: 'RHS RP200', preco_un: 1900, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Rack porta-halteres', qtd: 1, ref: 'RHS RH200', preco_un: 2800, fornecedor: 'RHS' },

    // Funcional
    { cat: 'funcional', nome: 'Rig multi-grip 4 estações', qtd: 1, ref: 'Movement RG400', preco_un: 18500, fornecedor: 'Movement' },
    { cat: 'funcional', nome: 'Kettlebell kit 4-32kg (12 un)', qtd: 1, ref: 'RHS KB Set', preco_un: 4800, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Box jump', qtd: 2, ref: 'RHS BJ60', preco_un: 380, fornecedor: 'RHS' },
  ],
}

export const ACADEMIA_M: KitEquipamentos = {
  tipo_negocio: 'academia',
  tamanho_preset: 'm',
  area_referencia_m2: 1000,
  modelo_operacao: 'Smart Fit Standard / Bluefit (padrão de mercado mais comum)',
  desconto_volume_pct: [0.20, 0.30],
  fontes: ['Movement Catálogo 2024', 'ACAD Guia 2024', 'Smart Fit Standard release SMFT3'],
  itens: [
    // Cardio (28 unidades)
    { cat: 'cardio', nome: 'Esteira profissional', qtd: 10, ref: 'Movement RT300', preco_un: 12500, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Bike vertical', qtd: 6, ref: 'Movement BR300', preco_un: 6200, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Bike horizontal', qtd: 4, ref: 'Movement BR200', preco_un: 7500, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Elíptico', qtd: 4, ref: 'Movement EL700', preco_un: 10800, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Transport (escada)', qtd: 2, ref: 'Movement TP500', preco_un: 18900, fornecedor: 'Movement' },
    { cat: 'cardio', nome: 'Remo ergômetro', qtd: 2, ref: 'Concept2 Model D', preco_un: 8400, fornecedor: 'Concept2' },

    // Spinning (sala dedicada 50-80m²)
    { cat: 'spinning', nome: 'Bike spinning indoor', qtd: 15, ref: 'Schwinn AC Sport', preco_un: 4200, fornecedor: 'Schwinn' },

    // Musculação superior — 11 estações
    { cat: 'musc_superior', nome: 'Crossover (polia dupla)', qtd: 1, ref: 'Movement CX300', preco_un: 22500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Puxador frontal (lat pulldown)', qtd: 1, ref: 'Movement LP100', preco_un: 11200, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Remada sentada', qtd: 1, ref: 'Movement RS100', preco_un: 11500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Pullover', qtd: 1, ref: 'Movement PO100', preco_un: 11900, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Supino reto seletorizado', qtd: 1, ref: 'Movement BP100', preco_un: 12500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Supino inclinado', qtd: 1, ref: 'Movement BI100', preco_un: 12500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Peck deck (peitoral)', qtd: 1, ref: 'Movement PD100', preco_un: 11800, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Voador inverso (rear delt)', qtd: 1, ref: 'Movement RD100', preco_un: 11500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Desenvolvimento ombros', qtd: 1, ref: 'Movement SP100', preco_un: 12100, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Rosca scott seletorizada', qtd: 1, ref: 'Movement BC100', preco_un: 9800, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Tríceps polia', qtd: 1, ref: 'Movement TP200', preco_un: 9500, fornecedor: 'Movement' },

    // Musculação inferior — 9 estações
    { cat: 'musc_inferior', nome: 'Leg press 45°', qtd: 1, ref: 'Movement LP45', preco_un: 18500, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Hack squat', qtd: 1, ref: 'Movement HS100', preco_un: 16200, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira extensora', qtd: 1, ref: 'Movement EX100', preco_un: 9200, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira flexora sentada', qtd: 1, ref: 'Movement FL100', preco_un: 9200, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Mesa flexora deitada', qtd: 1, ref: 'Movement MF100', preco_un: 10100, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira adutora', qtd: 1, ref: 'Movement AD100', preco_un: 8500, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Cadeira abdutora', qtd: 1, ref: 'Movement AB100', preco_un: 8500, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Panturrilha em pé', qtd: 1, ref: 'Movement PE100', preco_un: 8900, fornecedor: 'Movement' },
    { cat: 'musc_inferior', nome: 'Panturrilha sentada', qtd: 1, ref: 'Movement PS100', preco_un: 7800, fornecedor: 'Movement' },

    // Glúteo (2 estações)
    { cat: 'gluteo', nome: 'Glute drive (hip thrust)', qtd: 1, ref: 'Movement GD100', preco_un: 13500, fornecedor: 'Movement' },
    { cat: 'gluteo', nome: 'Mesa glúteo (kickback)', qtd: 1, ref: 'Movement GK100', preco_un: 9800, fornecedor: 'Movement' },

    // Core (3 itens)
    { cat: 'core', nome: 'Cadeira abdominal', qtd: 1, ref: 'Movement CA100', preco_un: 8200, fornecedor: 'Movement' },
    { cat: 'core', nome: 'Banco abdominal ajustável', qtd: 2, ref: 'Movement BA100', preco_un: 1800, fornecedor: 'Movement' },
    { cat: 'core', nome: 'Cadeira rotação tronco', qtd: 1, ref: 'Movement RT100', preco_un: 9100, fornecedor: 'Movement' },

    // Livre / Plate-loaded
    { cat: 'livre', nome: 'Squat rack', qtd: 2, ref: 'Movement SR200', preco_un: 8500, fornecedor: 'Movement' },
    { cat: 'livre', nome: 'Smith machine', qtd: 1, ref: 'Movement SM300', preco_un: 14800, fornecedor: 'Movement' },
    { cat: 'livre', nome: 'Banco supino reto fixo', qtd: 2, ref: 'Movement BS100', preco_un: 2200, fornecedor: 'Movement' },
    { cat: 'livre', nome: 'Banco supino inclinado ajustável', qtd: 2, ref: 'Movement BI300', preco_un: 2800, fornecedor: 'Movement' },
    { cat: 'livre', nome: 'Banco scott livre', qtd: 1, ref: 'Movement BC300', preco_un: 2500, fornecedor: 'Movement' },

    // Pesos
    { cat: 'pesos', nome: 'Kit halteres 1-50kg (par)', qtd: 1, ref: 'RHS borracha', preco_un: 35000, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Kit anilhas (600kg variado)', qtd: 1, ref: 'RHS Olímpico', preco_un: 28000, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Barras olímpicas 20kg', qtd: 6, ref: 'RHS 1500mm', preco_un: 850, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Rack porta-anilhas', qtd: 2, ref: 'RHS RP200', preco_un: 1900, fornecedor: 'RHS' },
    { cat: 'pesos', nome: 'Rack porta-halteres', qtd: 2, ref: 'RHS RH200', preco_un: 2800, fornecedor: 'RHS' },

    // Funcional
    { cat: 'funcional', nome: 'Rig multi-grip 4 estações', qtd: 1, ref: 'Movement RG400', preco_un: 18500, fornecedor: 'Movement' },
    { cat: 'funcional', nome: 'Kettlebell kit 4-32kg (12 un)', qtd: 1, ref: 'RHS KB Set', preco_un: 4800, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Cordas naval 12m', qtd: 2, ref: 'RHS BR12', preco_un: 450, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Box jump', qtd: 3, ref: 'RHS BJ60', preco_un: 380, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Medicine ball kit 4-12kg (6 un)', qtd: 1, ref: 'RHS MB Set', preco_un: 1200, fornecedor: 'RHS' },

    // Acessórios
    { cat: 'acessorios', nome: 'Barras paralelas dip', qtd: 2, ref: 'Movement DP100', preco_un: 2400, fornecedor: 'Movement' },
    { cat: 'acessorios', nome: 'Graviton (assistência pull-up)', qtd: 1, ref: 'Movement GV100', preco_un: 14200, fornecedor: 'Movement' },
    { cat: 'acessorios', nome: 'Saco de boxe + stand', qtd: 1, ref: 'RHS SB100', preco_un: 1800, fornecedor: 'RHS' },
  ],
}

export const ACADEMIA_G: KitEquipamentos = {
  tipo_negocio: 'academia',
  tamanho_preset: 'g',
  area_referencia_m2: 2000,
  modelo_operacao: 'Bodytech / Cia Athletica entry (premium urbano com Pilates room)',
  desconto_volume_pct: [0.20, 0.35],
  fontes: ['Movement Catálogo 2024', 'Life Fitness BR', 'Bodytech IR 2024'],
  itens: [
    // Cardio (50 unidades) — algumas Life Fitness importadas
    { cat: 'cardio', nome: 'Esteira profissional', qtd: 18, ref: 'Life Fitness 95T Engage', preco_un: 28000, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Bike vertical', qtd: 10, ref: 'Life Fitness 95C', preco_un: 14500, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Bike horizontal', qtd: 6, ref: 'Life Fitness 95R', preco_un: 16200, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Elíptico', qtd: 8, ref: 'Life Fitness 95X', preco_un: 22000, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Transport (escada)', qtd: 4, ref: 'Life Fitness 95SE', preco_un: 32000, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Remo ergômetro', qtd: 4, ref: 'Concept2 Model D', preco_un: 8400, fornecedor: 'Concept2' },

    // Spinning sala dedicada (30 unidades)
    { cat: 'spinning', nome: 'Bike spinning indoor premium', qtd: 25, ref: 'Schwinn AC Performance', preco_un: 7500, fornecedor: 'Schwinn' },

    // Musculação superior — 18 estações (linhas Hammer Strength + Life Fitness)
    { cat: 'musc_superior', nome: 'Crossover dupla polia 4 pegadas', qtd: 2, ref: 'Life Fitness Signature Cable', preco_un: 38000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Puxador frontal Hammer', qtd: 1, ref: 'Hammer Strength Lat Pulldown', preco_un: 24000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Remada sentada Hammer', qtd: 1, ref: 'Hammer Strength Seated Row', preco_un: 24500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Remada articulada plate-loaded', qtd: 1, ref: 'Hammer Strength ISO-Lateral Row', preco_un: 22000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Pullover Hammer', qtd: 1, ref: 'Hammer Strength Pullover', preco_un: 22500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Supino reto Hammer', qtd: 1, ref: 'Hammer Strength Bench Press', preco_un: 26000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Supino inclinado Hammer', qtd: 1, ref: 'Hammer Strength Incline Press', preco_un: 26000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Supino declinado', qtd: 1, ref: 'Hammer Strength Decline Press', preco_un: 25000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Peck deck premium', qtd: 1, ref: 'Life Fitness Signature Pec Fly', preco_un: 19500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Voador inverso (rear delt)', qtd: 1, ref: 'Life Fitness Rear Delt', preco_un: 19500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Desenvolvimento ombros Hammer', qtd: 1, ref: 'Hammer Strength Shoulder Press', preco_un: 24000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Elevação lateral mecânica', qtd: 1, ref: 'Life Fitness Lateral Raise', preco_un: 18500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Rosca scott seletorizada', qtd: 2, ref: 'Movement BC100', preco_un: 9800, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Tríceps polia', qtd: 2, ref: 'Movement TP200', preco_un: 9500, fornecedor: 'Movement' },
    { cat: 'musc_superior', nome: 'Pulldown único', qtd: 1, ref: 'Movement PL100', preco_un: 10800, fornecedor: 'Movement' },

    // Musculação inferior — 13 estações
    { cat: 'musc_inferior', nome: 'Leg press 45° Hammer', qtd: 2, ref: 'Hammer Strength Linear Leg Press', preco_un: 32000, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Leg press horizontal', qtd: 1, ref: 'Life Fitness Horizontal Leg Press', preco_un: 28000, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Hack squat', qtd: 2, ref: 'Hammer Strength Hack Squat', preco_un: 25000, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Cadeira extensora', qtd: 2, ref: 'Life Fitness Leg Extension', preco_un: 16500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Cadeira flexora sentada', qtd: 2, ref: 'Life Fitness Leg Curl Seated', preco_un: 16500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Mesa flexora deitada', qtd: 1, ref: 'Life Fitness Leg Curl Prone', preco_un: 17500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Cadeira adutora', qtd: 1, ref: 'Life Fitness Hip Adduction', preco_un: 14500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Cadeira abdutora', qtd: 1, ref: 'Life Fitness Hip Abduction', preco_un: 14500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Panturrilha em pé', qtd: 1, ref: 'Life Fitness Standing Calf', preco_un: 14200, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Panturrilha sentada', qtd: 1, ref: 'Life Fitness Seated Calf', preco_un: 12500, fornecedor: 'Life Fitness' },

    // Glúteo
    { cat: 'gluteo', nome: 'Glute drive Hammer', qtd: 2, ref: 'Hammer Strength Glute Drive', preco_un: 19500, fornecedor: 'Life Fitness' },
    { cat: 'gluteo', nome: 'Mesa glúteo (kickback)', qtd: 1, ref: 'Movement GK100', preco_un: 9800, fornecedor: 'Movement' },
    { cat: 'gluteo', nome: 'GHD (Glute Ham Developer)', qtd: 2, ref: 'Rogue GHD 2.0', preco_un: 8500, fornecedor: 'Rogue' },

    // Core
    { cat: 'core', nome: 'Cadeira abdominal', qtd: 2, ref: 'Movement CA100', preco_un: 8200, fornecedor: 'Movement' },
    { cat: 'core', nome: 'Banco abdominal ajustável', qtd: 4, ref: 'Movement BA100', preco_un: 1800, fornecedor: 'Movement' },
    { cat: 'core', nome: 'Cadeira rotação tronco', qtd: 1, ref: 'Life Fitness Torso Rotation', preco_un: 16500, fornecedor: 'Life Fitness' },

    // Livre
    { cat: 'livre', nome: 'Squat rack premium', qtd: 4, ref: 'Rogue R-3', preco_un: 12500, fornecedor: 'Rogue' },
    { cat: 'livre', nome: 'Power rack 4 colunas', qtd: 1, ref: 'Rogue Monster Lite', preco_un: 18500, fornecedor: 'Rogue' },
    { cat: 'livre', nome: 'Smith machine', qtd: 2, ref: 'Life Fitness Smith', preco_un: 22000, fornecedor: 'Life Fitness' },
    { cat: 'livre', nome: 'Banco supino reto fixo', qtd: 4, ref: 'Rogue FB-3', preco_un: 3200, fornecedor: 'Rogue' },
    { cat: 'livre', nome: 'Banco supino ajustável', qtd: 4, ref: 'Rogue AB-3', preco_un: 4500, fornecedor: 'Rogue' },
    { cat: 'livre', nome: 'Banco scott livre', qtd: 2, ref: 'Movement BC300', preco_un: 2500, fornecedor: 'Movement' },

    // Pesos
    { cat: 'pesos', nome: 'Kit halteres 1-60kg (par)', qtd: 1, ref: 'Eleiko borracha', preco_un: 65000, fornecedor: 'Eleiko' },
    { cat: 'pesos', nome: 'Kit anilhas (1200kg variado)', qtd: 1, ref: 'Eleiko Sport', preco_un: 58000, fornecedor: 'Eleiko' },
    { cat: 'pesos', nome: 'Barras olímpicas premium 20kg', qtd: 10, ref: 'Eleiko Sport Training', preco_un: 2800, fornecedor: 'Eleiko' },
    { cat: 'pesos', nome: 'Rack porta-anilhas', qtd: 4, ref: 'Rogue PR-3', preco_un: 2800, fornecedor: 'Rogue' },
    { cat: 'pesos', nome: 'Rack porta-halteres premium', qtd: 3, ref: 'Rogue DR-3', preco_un: 4500, fornecedor: 'Rogue' },

    // Funcional + sala dedicada
    { cat: 'funcional', nome: 'Rig multi-grip 8 estações', qtd: 1, ref: 'Rogue Monster Lite 8', preco_un: 38000, fornecedor: 'Rogue' },
    { cat: 'funcional', nome: 'Kettlebell kit 4-48kg (16 un)', qtd: 1, ref: 'Rogue Kettlebells', preco_un: 9500, fornecedor: 'Rogue' },
    { cat: 'funcional', nome: 'Cordas naval 12m', qtd: 4, ref: 'RHS BR12', preco_un: 450, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Box jump pliométrico', qtd: 6, ref: 'Rogue Game Box', preco_un: 850, fornecedor: 'Rogue' },
    { cat: 'funcional', nome: 'Medicine ball kit 4-15kg (8 un)', qtd: 1, ref: 'RHS MB Set Pro', preco_un: 2200, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'TRX suspension', qtd: 8, ref: 'TRX Pro 4', preco_un: 1200, fornecedor: 'Generico' },

    // Acessórios
    { cat: 'acessorios', nome: 'Barras paralelas dip', qtd: 4, ref: 'Movement DP100', preco_un: 2400, fornecedor: 'Movement' },
    { cat: 'acessorios', nome: 'Graviton', qtd: 2, ref: 'Movement GV100', preco_un: 14200, fornecedor: 'Movement' },
    { cat: 'acessorios', nome: 'Saco de boxe + stand', qtd: 2, ref: 'RHS SB100', preco_un: 1800, fornecedor: 'RHS' },
  ],
}

export const ACADEMIA_GG: KitEquipamentos = {
  tipo_negocio: 'academia',
  tamanho_preset: 'gg',
  area_referencia_m2: 4000,
  modelo_operacao: 'Bodytech / Cia Athletica flagship (mega centro com piscina + lutas + spa)',
  desconto_volume_pct: [0.25, 0.40],
  fontes: ['Bodytech IR 2024', 'Cia Athletica catálogo unidades', 'IHRSA LatAm 2024'],
  itens: [
    // Cardio (90 unidades) — 2x do G
    { cat: 'cardio', nome: 'Esteira premium', qtd: 30, ref: 'Life Fitness 97T Discover SE3', preco_un: 38000, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Bike vertical premium', qtd: 18, ref: 'Life Fitness 97C', preco_un: 18500, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Bike horizontal premium', qtd: 12, ref: 'Life Fitness 97R', preco_un: 19500, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Elíptico premium', qtd: 14, ref: 'Life Fitness 97X', preco_un: 26500, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Transport premium', qtd: 8, ref: 'Life Fitness 97SE', preco_un: 38000, fornecedor: 'Life Fitness' },
    { cat: 'cardio', nome: 'Remo ergômetro', qtd: 6, ref: 'Concept2 Dynamic', preco_un: 14500, fornecedor: 'Concept2' },
    { cat: 'cardio', nome: 'Bike assault (sprint)', qtd: 4, ref: 'Assault AirBike Pro', preco_un: 8500, fornecedor: 'Rogue' },

    // Spinning (2 salas)
    { cat: 'spinning', nome: 'Bike spinning premium', qtd: 50, ref: 'Schwinn AC Performance Plus', preco_un: 9500, fornecedor: 'Schwinn' },

    // Musculação superior — Linha Hammer + Technogym (32 estações)
    { cat: 'musc_superior', nome: 'Crossover dupla 6 pegadas', qtd: 4, ref: 'Technogym Personal Cable', preco_un: 65000, fornecedor: 'Technogym' },
    { cat: 'musc_superior', nome: 'Puxador frontal Hammer', qtd: 2, ref: 'Hammer Strength Lat Pulldown', preco_un: 24000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Remada sentada Hammer', qtd: 2, ref: 'Hammer Strength Seated Row', preco_un: 24500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Remada articulada plate-loaded', qtd: 2, ref: 'Hammer Strength ISO-Lateral Row', preco_un: 22000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Pullover Hammer', qtd: 2, ref: 'Hammer Strength Pullover', preco_un: 22500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Supino reto Hammer', qtd: 2, ref: 'Hammer Strength Bench Press', preco_un: 26000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Supino inclinado Hammer', qtd: 2, ref: 'Hammer Strength Incline Press', preco_un: 26000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Supino declinado', qtd: 1, ref: 'Hammer Strength Decline Press', preco_un: 25000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Peck deck premium', qtd: 2, ref: 'Technogym Pec Fly', preco_un: 28000, fornecedor: 'Technogym' },
    { cat: 'musc_superior', nome: 'Voador inverso', qtd: 2, ref: 'Technogym Rear Delt', preco_un: 28000, fornecedor: 'Technogym' },
    { cat: 'musc_superior', nome: 'Desenvolvimento ombros Hammer', qtd: 2, ref: 'Hammer Strength Shoulder Press', preco_un: 24000, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Elevação lateral mecânica', qtd: 2, ref: 'Life Fitness Lateral Raise', preco_un: 18500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Rosca scott premium', qtd: 3, ref: 'Hammer Strength Preacher Curl', preco_un: 18500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Tríceps polia premium', qtd: 3, ref: 'Life Fitness Triceps Press', preco_un: 14500, fornecedor: 'Life Fitness' },
    { cat: 'musc_superior', nome: 'Pulldown único', qtd: 2, ref: 'Movement PL100', preco_un: 10800, fornecedor: 'Movement' },

    // Musculação inferior — 18 estações
    { cat: 'musc_inferior', nome: 'Leg press 45° Hammer', qtd: 3, ref: 'Hammer Strength Linear Leg Press', preco_un: 32000, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Leg press horizontal', qtd: 2, ref: 'Life Fitness Horizontal Leg Press', preco_un: 28000, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Hack squat', qtd: 3, ref: 'Hammer Strength Hack Squat', preco_un: 25000, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Cadeira extensora', qtd: 3, ref: 'Life Fitness Leg Extension', preco_un: 16500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Cadeira flexora sentada', qtd: 3, ref: 'Life Fitness Leg Curl Seated', preco_un: 16500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Mesa flexora deitada', qtd: 2, ref: 'Life Fitness Leg Curl Prone', preco_un: 17500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Cadeira adutora', qtd: 2, ref: 'Life Fitness Hip Adduction', preco_un: 14500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Cadeira abdutora', qtd: 2, ref: 'Life Fitness Hip Abduction', preco_un: 14500, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Panturrilha em pé', qtd: 2, ref: 'Life Fitness Standing Calf', preco_un: 14200, fornecedor: 'Life Fitness' },
    { cat: 'musc_inferior', nome: 'Panturrilha sentada', qtd: 2, ref: 'Life Fitness Seated Calf', preco_un: 12500, fornecedor: 'Life Fitness' },

    // Glúteo
    { cat: 'gluteo', nome: 'Glute drive Hammer', qtd: 3, ref: 'Hammer Strength Glute Drive', preco_un: 19500, fornecedor: 'Life Fitness' },
    { cat: 'gluteo', nome: 'Mesa glúteo (kickback)', qtd: 2, ref: 'Movement GK100', preco_un: 9800, fornecedor: 'Movement' },
    { cat: 'gluteo', nome: 'GHD', qtd: 4, ref: 'Rogue GHD 2.0', preco_un: 8500, fornecedor: 'Rogue' },

    // Core
    { cat: 'core', nome: 'Cadeira abdominal premium', qtd: 3, ref: 'Life Fitness Abdominal', preco_un: 14500, fornecedor: 'Life Fitness' },
    { cat: 'core', nome: 'Banco abdominal ajustável', qtd: 8, ref: 'Movement BA100', preco_un: 1800, fornecedor: 'Movement' },
    { cat: 'core', nome: 'Cadeira rotação tronco', qtd: 2, ref: 'Life Fitness Torso Rotation', preco_un: 16500, fornecedor: 'Life Fitness' },

    // Livre — sala dedicada powerlifting/strongman
    { cat: 'livre', nome: 'Squat rack premium', qtd: 8, ref: 'Rogue R-6', preco_un: 18500, fornecedor: 'Rogue' },
    { cat: 'livre', nome: 'Power rack 4 colunas', qtd: 4, ref: 'Rogue Monster Lite', preco_un: 18500, fornecedor: 'Rogue' },
    { cat: 'livre', nome: 'Smith machine premium', qtd: 3, ref: 'Life Fitness Smith', preco_un: 22000, fornecedor: 'Life Fitness' },
    { cat: 'livre', nome: 'Banco supino reto fixo', qtd: 8, ref: 'Rogue FB-3', preco_un: 3200, fornecedor: 'Rogue' },
    { cat: 'livre', nome: 'Banco supino ajustável', qtd: 8, ref: 'Rogue AB-3', preco_un: 4500, fornecedor: 'Rogue' },
    { cat: 'livre', nome: 'Banco scott livre', qtd: 3, ref: 'Movement BC300', preco_un: 2500, fornecedor: 'Movement' },
    { cat: 'livre', nome: 'Platform powerlifting', qtd: 2, ref: 'Rogue Comp Plat', preco_un: 12500, fornecedor: 'Rogue' },

    // Pesos premium
    { cat: 'pesos', nome: 'Kit halteres 1-70kg (par)', qtd: 1, ref: 'Eleiko Hex', preco_un: 95000, fornecedor: 'Eleiko' },
    { cat: 'pesos', nome: 'Kit bumpers (1500kg)', qtd: 1, ref: 'Eleiko XF 5', preco_un: 85000, fornecedor: 'Eleiko' },
    { cat: 'pesos', nome: 'Barras olímpicas premium 20kg', qtd: 18, ref: 'Eleiko IWF Comp', preco_un: 4500, fornecedor: 'Eleiko' },
    { cat: 'pesos', nome: 'Rack porta-anilhas premium', qtd: 8, ref: 'Rogue PR-3', preco_un: 2800, fornecedor: 'Rogue' },
    { cat: 'pesos', nome: 'Rack porta-halteres', qtd: 6, ref: 'Rogue DR-3', preco_un: 4500, fornecedor: 'Rogue' },

    // CrossFit (sala dedicada GG só)
    { cat: 'crossfit', nome: 'Rig CrossFit Monster 12 estações', qtd: 1, ref: 'Rogue Monster Lite 12', preco_un: 58000, fornecedor: 'Rogue' },
    { cat: 'crossfit', nome: 'Wall ball', qtd: 8, ref: 'Rogue Wall Ball', preco_un: 480, fornecedor: 'Rogue' },
    { cat: 'crossfit', nome: 'Slam ball', qtd: 8, ref: 'Rogue Slam Ball', preco_un: 380, fornecedor: 'Rogue' },

    // Funcional
    { cat: 'funcional', nome: 'Kettlebell kit 4-48kg (32 un)', qtd: 1, ref: 'Rogue Kettlebells Pro', preco_un: 18500, fornecedor: 'Rogue' },
    { cat: 'funcional', nome: 'Cordas naval 12m', qtd: 8, ref: 'RHS BR12', preco_un: 450, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Box jump pliométrico', qtd: 12, ref: 'Rogue Game Box', preco_un: 850, fornecedor: 'Rogue' },
    { cat: 'funcional', nome: 'Medicine ball kit', qtd: 2, ref: 'RHS MB Set Pro', preco_un: 2200, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'TRX suspension', qtd: 16, ref: 'TRX Pro 4', preco_un: 1200, fornecedor: 'Generico' },

    // Pilates (sala dedicada GG)
    { cat: 'pilates', nome: 'Reformer profissional', qtd: 6, ref: 'Stott V2 Max Plus', preco_un: 28000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Cadillac/Trapézio', qtd: 2, ref: 'Stott Cadillac', preco_un: 22000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Barrel (ladder)', qtd: 2, ref: 'Stott Ladder Barrel', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Chair (cadeira)', qtd: 2, ref: 'Stott Chair', preco_un: 9500, fornecedor: 'Stott' },

    // Acessórios
    { cat: 'acessorios', nome: 'Barras paralelas dip', qtd: 6, ref: 'Movement DP100', preco_un: 2400, fornecedor: 'Movement' },
    { cat: 'acessorios', nome: 'Graviton', qtd: 3, ref: 'Movement GV100', preco_un: 14200, fornecedor: 'Movement' },
    { cat: 'acessorios', nome: 'Saco de boxe + stand', qtd: 4, ref: 'RHS SB100', preco_un: 1800, fornecedor: 'RHS' },
  ],
}
