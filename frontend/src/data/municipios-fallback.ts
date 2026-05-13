/**
 * Fallback estático de municípios — usado quando a API IBGE Localidades
 * está indisponível (caso real observado em 2026-05-11).
 *
 * Cobertura: 27 capitais + 30 cidades fitness-relevantes (RMs principais,
 * RM Fortaleza completa pra suportar Eusébio que motivou esse trabalho).
 *
 * Pra município fora do dict, useMunicipioAutocomplete mostra mensagem
 * "API do IBGE indisponível — digite o nome manualmente". Não bloqueia o form.
 */
import type { MunicipioIBGE } from '@/hooks/useMunicipioAutocomplete'

export const MUNICIPIOS_FALLBACK: MunicipioIBGE[] = [
  // ── Capitais ──
  { id: 1200401, nome: 'Rio Branco', uf: 'AC', uf_nome: 'Acre' },
  { id: 2704302, nome: 'Maceió', uf: 'AL', uf_nome: 'Alagoas' },
  { id: 1600303, nome: 'Macapá', uf: 'AP', uf_nome: 'Amapá' },
  { id: 1302603, nome: 'Manaus', uf: 'AM', uf_nome: 'Amazonas' },
  { id: 2927408, nome: 'Salvador', uf: 'BA', uf_nome: 'Bahia' },
  { id: 2304400, nome: 'Fortaleza', uf: 'CE', uf_nome: 'Ceará' },
  { id: 5300108, nome: 'Brasília', uf: 'DF', uf_nome: 'Distrito Federal' },
  { id: 3205309, nome: 'Vitória', uf: 'ES', uf_nome: 'Espírito Santo' },
  { id: 5208707, nome: 'Goiânia', uf: 'GO', uf_nome: 'Goiás' },
  { id: 2111300, nome: 'São Luís', uf: 'MA', uf_nome: 'Maranhão' },
  { id: 5103403, nome: 'Cuiabá', uf: 'MT', uf_nome: 'Mato Grosso' },
  { id: 5002704, nome: 'Campo Grande', uf: 'MS', uf_nome: 'Mato Grosso do Sul' },
  { id: 3106200, nome: 'Belo Horizonte', uf: 'MG', uf_nome: 'Minas Gerais' },
  { id: 1501402, nome: 'Belém', uf: 'PA', uf_nome: 'Pará' },
  { id: 2507507, nome: 'João Pessoa', uf: 'PB', uf_nome: 'Paraíba' },
  { id: 4106902, nome: 'Curitiba', uf: 'PR', uf_nome: 'Paraná' },
  { id: 2611606, nome: 'Recife', uf: 'PE', uf_nome: 'Pernambuco' },
  { id: 2211001, nome: 'Teresina', uf: 'PI', uf_nome: 'Piauí' },
  { id: 3304557, nome: 'Rio de Janeiro', uf: 'RJ', uf_nome: 'Rio de Janeiro' },
  { id: 2408102, nome: 'Natal', uf: 'RN', uf_nome: 'Rio Grande do Norte' },
  { id: 4314902, nome: 'Porto Alegre', uf: 'RS', uf_nome: 'Rio Grande do Sul' },
  { id: 1100205, nome: 'Porto Velho', uf: 'RO', uf_nome: 'Rondônia' },
  { id: 1400100, nome: 'Boa Vista', uf: 'RR', uf_nome: 'Roraima' },
  { id: 4205407, nome: 'Florianópolis', uf: 'SC', uf_nome: 'Santa Catarina' },
  { id: 3550308, nome: 'São Paulo', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 2800308, nome: 'Aracaju', uf: 'SE', uf_nome: 'Sergipe' },
  { id: 1721000, nome: 'Palmas', uf: 'TO', uf_nome: 'Tocantins' },

  // ── RM Fortaleza (motivou a refatoração — caso Eusébio) ──
  { id: 2304285, nome: 'Eusébio', uf: 'CE', uf_nome: 'Ceará' },
  { id: 2303709, nome: 'Caucaia', uf: 'CE', uf_nome: 'Ceará' },
  { id: 2307650, nome: 'Maracanaú', uf: 'CE', uf_nome: 'Ceará' },
  { id: 2301109, nome: 'Aquiraz', uf: 'CE', uf_nome: 'Ceará' },
  { id: 2309706, nome: 'Pacatuba', uf: 'CE', uf_nome: 'Ceará' },
  { id: 2307700, nome: 'Maranguape', uf: 'CE', uf_nome: 'Ceará' },
  { id: 2305233, nome: 'Horizonte', uf: 'CE', uf_nome: 'Ceará' },
  { id: 2306256, nome: 'Itaitinga', uf: 'CE', uf_nome: 'Ceará' },

  // ── RM São Paulo (top players) ──
  { id: 3509502, nome: 'Campinas', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 3518800, nome: 'Guarulhos', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 3547809, nome: 'Santo André', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 3548708, nome: 'São Bernardo do Campo', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 3534401, nome: 'Osasco', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 3543402, nome: 'Ribeirão Preto', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 3548500, nome: 'Santos', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 3552205, nome: 'Sorocaba', uf: 'SP', uf_nome: 'São Paulo' },
  { id: 3549904, nome: 'São José dos Campos', uf: 'SP', uf_nome: 'São Paulo' },

  // ── RM Rio de Janeiro ──
  { id: 3303302, nome: 'Niterói', uf: 'RJ', uf_nome: 'Rio de Janeiro' },
  { id: 3304904, nome: 'São Gonçalo', uf: 'RJ', uf_nome: 'Rio de Janeiro' },
  { id: 3301702, nome: 'Duque de Caxias', uf: 'RJ', uf_nome: 'Rio de Janeiro' },
  { id: 3303500, nome: 'Nova Iguaçu', uf: 'RJ', uf_nome: 'Rio de Janeiro' },

  // ── Outras cidades grandes ──
  { id: 4209102, nome: 'Joinville', uf: 'SC', uf_nome: 'Santa Catarina' },
  { id: 4202404, nome: 'Blumenau', uf: 'SC', uf_nome: 'Santa Catarina' },
  { id: 4204202, nome: 'Itajaí', uf: 'SC', uf_nome: 'Santa Catarina' },
  { id: 4119905, nome: 'Londrina', uf: 'PR', uf_nome: 'Paraná' },
  { id: 4115200, nome: 'Maringá', uf: 'PR', uf_nome: 'Paraná' },
  { id: 3170206, nome: 'Uberlândia', uf: 'MG', uf_nome: 'Minas Gerais' },
  { id: 3136702, nome: 'Juiz de Fora', uf: 'MG', uf_nome: 'Minas Gerais' },
]
