/**
 * Kits Studio Pilates — PP/P/M/G/GG.
 * Equipamento principal: Reformer, Cadillac, Barrel, Chair (clássicos Pilates).
 * Fornecedores premium: Stott, Balanced Body. Nacional: Arktus, Cia Pilates.
 */
import type { KitEquipamentos } from './types'

export const PILATES_PP: KitEquipamentos = {
  tipo_negocio: 'studio_pilates',
  tamanho_preset: 'pp',
  area_referencia_m2: 60,
  modelo_operacao: 'Studio solo (1 instrutor + 2 alunos por vez)',
  desconto_volume_pct: [0.05, 0.15],
  fontes: ['Stott Pilates BR', 'ABFPilates 2024'],
  itens: [
    { cat: 'pilates', nome: 'Reformer profissional', qtd: 2, ref: 'Stott V2 Max', preco_un: 22000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Chair (cadeira combo)', qtd: 1, ref: 'Stott Stability Chair', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Barrel pequeno (arc)', qtd: 1, ref: 'Stott Arc Barrel', preco_un: 1800, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Bolas suíças', qtd: 4, ref: 'RHS Stability Ball', preco_un: 180, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Bolas pequenas (soft)', qtd: 6, ref: 'Pilates Mini Ball', preco_un: 80, fornecedor: 'Generico' },
    { cat: 'funcional', nome: 'Elásticos resistência (kit)', qtd: 2, ref: 'Stott Bands', preco_un: 350, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Bastão wand', qtd: 4, ref: 'Pilates Wand', preco_un: 95, fornecedor: 'Generico' },
    { cat: 'acessorios', nome: 'Tatames + mats', qtd: 6, ref: 'Pilates Mat Pro', preco_un: 220, fornecedor: 'Generico' },
  ],
}

export const PILATES_P: KitEquipamentos = {
  tipo_negocio: 'studio_pilates',
  tamanho_preset: 'p',
  area_referencia_m2: 120,
  modelo_operacao: 'Studio compacto (4 reformers, aulas em grupo pequeno)',
  desconto_volume_pct: [0.10, 0.20],
  fontes: ['Stott Pilates BR', 'Balanced Body BR'],
  itens: [
    { cat: 'pilates', nome: 'Reformer profissional', qtd: 4, ref: 'Stott V2 Max Plus', preco_un: 28000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Cadillac/Trapézio', qtd: 1, ref: 'Stott Cadillac', preco_un: 22000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Chair', qtd: 2, ref: 'Stott Stability Chair', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Barrel (ladder)', qtd: 1, ref: 'Stott Ladder Barrel', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Arc Barrel', qtd: 2, ref: 'Stott Arc Barrel', preco_un: 1800, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Bolas suíças (kit completo)', qtd: 8, ref: 'RHS Stability Ball', preco_un: 180, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Bolas pequenas (soft)', qtd: 10, ref: 'Pilates Mini Ball', preco_un: 80, fornecedor: 'Generico' },
    { cat: 'funcional', nome: 'Elásticos resistência', qtd: 4, ref: 'Stott Bands Set', preco_un: 350, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Magic Circle (anel)', qtd: 6, ref: 'Stott Fitness Circle', preco_un: 380, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Bastão wand', qtd: 6, ref: 'Pilates Wand', preco_un: 95, fornecedor: 'Generico' },
    { cat: 'acessorios', nome: 'Tatames + mats', qtd: 10, ref: 'Pilates Mat Pro', preco_un: 220, fornecedor: 'Generico' },
  ],
}

export const PILATES_M: KitEquipamentos = {
  tipo_negocio: 'studio_pilates',
  tamanho_preset: 'm',
  area_referencia_m2: 200,
  modelo_operacao: 'Studio padrão Pilates Pró / Body Pilates (6 reformers + sala mat)',
  desconto_volume_pct: [0.12, 0.22],
  fontes: ['Stott Pilates BR', 'Balanced Body BR', 'ABFPilates Guia 2024'],
  itens: [
    { cat: 'pilates', nome: 'Reformer profissional', qtd: 6, ref: 'Stott V2 Max Plus', preco_un: 28000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Cadillac/Trapézio', qtd: 2, ref: 'Stott Cadillac', preco_un: 22000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Chair', qtd: 3, ref: 'Stott Stability Chair', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Barrel (ladder)', qtd: 2, ref: 'Stott Ladder Barrel', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Arc Barrel', qtd: 3, ref: 'Stott Arc Barrel', preco_un: 1800, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Tower (torre Pilates)', qtd: 2, ref: 'Stott Tower', preco_un: 12500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Wunda Chair (avançada)', qtd: 1, ref: 'Stott Wunda Chair', preco_un: 11500, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Bolas suíças', qtd: 12, ref: 'RHS Stability Ball', preco_un: 180, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Bolas pequenas', qtd: 14, ref: 'Pilates Mini Ball', preco_un: 80, fornecedor: 'Generico' },
    { cat: 'funcional', nome: 'Elásticos resistência', qtd: 6, ref: 'Stott Bands', preco_un: 350, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Magic Circle', qtd: 10, ref: 'Stott Fitness Circle', preco_un: 380, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Foam roller', qtd: 6, ref: 'Stott Foam Roller', preco_un: 280, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Bastão wand', qtd: 8, ref: 'Pilates Wand', preco_un: 95, fornecedor: 'Generico' },
    { cat: 'acessorios', nome: 'Tatames + mats premium', qtd: 16, ref: 'Stott Mat', preco_un: 380, fornecedor: 'Stott' },
    { cat: 'cardio', nome: 'Esteira (sala recuperação)', qtd: 1, ref: 'Movement RT200', preco_un: 9800, fornecedor: 'Movement', nota: 'Opcional p/ aquecimento' },
  ],
}

export const PILATES_G: KitEquipamentos = {
  tipo_negocio: 'studio_pilates',
  tamanho_preset: 'g',
  area_referencia_m2: 380,
  modelo_operacao: 'STOTT Premium / Polestar (multi-equipamentos + reformer tower)',
  desconto_volume_pct: [0.15, 0.25],
  fontes: ['Stott Pilates BR', 'Polestar Education BR'],
  itens: [
    { cat: 'pilates', nome: 'Reformer profissional', qtd: 10, ref: 'Stott V2 Max Plus', preco_un: 28000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Reformer Cadillac combo', qtd: 4, ref: 'Stott Reformer/Cadillac', preco_un: 38000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Cadillac standalone', qtd: 2, ref: 'Stott Cadillac', preco_un: 22000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Chair', qtd: 6, ref: 'Stott Stability Chair', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Wunda Chair', qtd: 3, ref: 'Stott Wunda Chair', preco_un: 11500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Barrel (ladder)', qtd: 4, ref: 'Stott Ladder Barrel', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Arc Barrel', qtd: 6, ref: 'Stott Arc Barrel', preco_un: 1800, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Spine Corrector', qtd: 2, ref: 'Stott Spine Corrector', preco_un: 3200, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Tower', qtd: 4, ref: 'Stott Tower', preco_un: 12500, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Bolas suíças kit', qtd: 20, ref: 'RHS Stability Ball', preco_un: 180, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Magic Circle premium', qtd: 16, ref: 'Stott Fitness Circle', preco_un: 380, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Foam roller pro', qtd: 12, ref: 'Stott Foam Roller', preco_un: 280, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Elásticos resistência kit', qtd: 12, ref: 'Stott Bands Pro', preco_un: 350, fornecedor: 'Stott' },
    { cat: 'acessorios', nome: 'Mats premium', qtd: 30, ref: 'Stott Mat Pro', preco_un: 380, fornecedor: 'Stott' },
  ],
}

export const PILATES_GG: KitEquipamentos = {
  tipo_negocio: 'studio_pilates',
  tamanho_preset: 'gg',
  area_referencia_m2: 700,
  modelo_operacao: 'Reab + Pilates clínico + treinamento de instrutores (Polestar Master Studio)',
  desconto_volume_pct: [0.18, 0.30],
  fontes: ['Stott Pilates BR commercial', 'Polestar Master Studios'],
  itens: [
    { cat: 'pilates', nome: 'Reformer profissional', qtd: 16, ref: 'Stott V2 Max Plus', preco_un: 28000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Reformer/Cadillac combo', qtd: 8, ref: 'Stott Reformer/Cadillac', preco_un: 38000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Cadillac standalone', qtd: 4, ref: 'Stott Cadillac', preco_un: 22000, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Chair', qtd: 12, ref: 'Stott Stability Chair', preco_un: 8500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Wunda Chair', qtd: 6, ref: 'Stott Wunda Chair', preco_un: 11500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Barrel + Spine Corrector', qtd: 10, ref: 'Stott Combo', preco_un: 10500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'Tower', qtd: 8, ref: 'Stott Tower', preco_un: 12500, fornecedor: 'Stott' },
    { cat: 'pilates', nome: 'CoreAlign (Balanced Body)', qtd: 4, ref: 'Balanced Body CoreAlign', preco_un: 42000, fornecedor: 'Balanced Body' },
    { cat: 'funcional', nome: 'Bolas suíças', qtd: 40, ref: 'RHS Stability Ball', preco_un: 180, fornecedor: 'RHS' },
    { cat: 'funcional', nome: 'Magic Circle', qtd: 30, ref: 'Stott Fitness Circle', preco_un: 380, fornecedor: 'Stott' },
    { cat: 'funcional', nome: 'Foam roller pro', qtd: 20, ref: 'Stott Foam Roller', preco_un: 280, fornecedor: 'Stott' },
    { cat: 'acessorios', nome: 'Mats premium', qtd: 60, ref: 'Stott Mat Pro', preco_un: 380, fornecedor: 'Stott' },
  ],
}
