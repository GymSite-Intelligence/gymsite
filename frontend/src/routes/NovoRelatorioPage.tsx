/**
 * NovoRelatorioPage — Tela 1 (Form de Criar Relatório).
 *
 * Estrutura em árvore Estado → Município → Bairro:
 *  1. Estado (UF) — dataset estático de 27 itens, dropdown nativo instantâneo
 *  2. Município — autocomplete IBGE Localidades restrito à UF escolhida
 *     (~150-500 itens em vez dos 5.5k do BR inteiro)
 *  3. Bairro — autocomplete Google Places via proxy Vite, restrito ao município
 *  4. Área m² mín/máx
 *  5. Público-alvo + Tipo de negócio
 *  6. Estacionamento obrigatório
 *  7. Submit → pipeline ADK (stub hoje, real quando POST /run_sse plugado)
 *
 * Cascata: campo N só habilita após campo N-1 selecionado. Garante que o
 * payload entregue ao pipeline tem (UF, Município, Bairro) sempre consistentes
 * e elimina ambiguidades como "Eusébio como bairro de Fortaleza".
 */
import { useMemo, useState, type FormEvent } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowRight, Clock, Loader2, RefreshCw } from 'lucide-react'
import { API_BASE, supabase } from '@/lib/supabase'
import { Combobox, type ComboboxOption } from '@/components/ui/combobox'
import { SelectGrouped } from '@/components/ui/select-grouped'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import {
  useMunicipioAutocomplete,
  type MunicipioIBGE,
} from '@/hooks/useMunicipioAutocomplete'
import { useBairrosDoMunicipio } from '@/hooks/useBairrosDoMunicipio'
import { useDebounce } from '@/hooks/useDebounce'
import { useIsAdmin } from '@/hooks/useIsAdmin'
import { UFS_BRASIL, type UF } from '@/data/ufs-brasil'
import {
  TAMANHOS_POR_MODELO,
  getTamanhoAncora,
  inferirTamanho,
  type ModeloNegocio,
  type TamanhoCodigo,
} from '@/data/tamanhos-por-modelo'

// Sentinela acordada com o backend (api.py:_build_prompt) — quando o usuário
// marca "rodar pela cidade inteira", o bairro fica com esse valor. Backend
// detecta e amplia o escopo pra o município todo. Evita migrar coluna NOT NULL
// no DB enquanto se mantém a UX clara na listagem.
const BAIRRO_CIDADE_INTEIRA = '(cidade inteira)'

const formSchema = z
  .object({
    uf: z.string().length(2, 'Selecione um estado'),
    municipio: z.string().min(2, 'Selecione um município'),
    codigoIbge: z.number().int().positive('Selecione um município válido'),
    cidadeInteira: z.boolean().default(false),
    bairro: z.string().default(''),
    bairroPlaceId: z.string().optional(),
    areaMin: z
      .number({ invalid_type_error: 'Área mínima inválida' })
      .int()
      .min(200, 'Mínimo 200 m²')
      .max(5000),
    areaMax: z
      .number({ invalid_type_error: 'Área máxima inválida' })
      .int()
      .min(200)
      .max(5000),
    publicoAlvo: z.enum(['18-29', '25-40', '30-50', '40+']),
    generoAlvo: z.enum([
      'misto',
      'predominantemente_feminino',
      'predominantemente_masculino',
      'exclusivamente_feminino',
      'exclusivamente_masculino',
    ]),
    // Valores DEVEM bater com ENUM negocio_tipo do banco (db/schema.sql:60-66)
    // pra não quebrar INSERT em relatorio_inputs.tipo_negocio.
    tipoNegocio: z.enum([
      'academia',
      'crossfit_box',
      'studio_pilates',
      'studio_funcional',
      'outro',
    ]),
    // Tamanho preset (PP/P/M/G/GG). Auto-preenche areaMin/areaMax conforme
    // benchmark do modelo. Usuário pode override manualmente depois.
    tamanho: z.enum(['pp', 'p', 'm', 'g', 'gg']),
    estacionamentoObrigatorio: z.boolean(),
  })
  .refine((d) => d.areaMax >= d.areaMin, {
    message: 'Área máxima deve ser >= mínima',
    path: ['areaMax'],
  })
  .superRefine((d, ctx) => {
    // Bairro só é obrigatório quando NÃO está em modo "cidade inteira".
    if (!d.cidadeInteira && d.bairro.trim().length < 2) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['bairro'],
        message: 'Selecione um bairro ou marque "rodar pela cidade inteira"',
      })
    }
  })

type FormData = z.infer<typeof formSchema>

// UFs agrupadas por região pra dropdown organizado.
const UFS_POR_REGIAO = UFS_BRASIL.reduce<Record<UF['regiao'], UF[]>>(
  (acc, uf) => {
    if (!acc[uf.regiao]) acc[uf.regiao] = []
    acc[uf.regiao].push(uf)
    return acc
  },
  {} as Record<UF['regiao'], UF[]>,
)

export function NovoRelatorioPage() {
  const navigate = useNavigate()
  const isAdmin = useIsAdmin()
  // Search params injetados quando user clica "Tentar de novo" num relatório
  // falho. Pré-preenche os campos do form com os mesmos parâmetros do original.
  const retrySearch = useSearch({ from: '/relatorios/new' })

  // Estado da árvore — inicializa com o que veio do retry quando disponível
  const ufInicial = retrySearch.uf
    ? UFS_BRASIL.find((u) => u.sigla === retrySearch.uf) ?? null
    : null
  const [ufSelecionada, setUfSelecionada] = useState<UF | null>(ufInicial)
  const [municipioQuery, setMunicipioQuery] = useState(retrySearch.cidade ?? '')
  const [municipioSelecionado, setMunicipioSelecionado] =
    useState<MunicipioIBGE | null>(
      retrySearch.cidade && retrySearch.uf
        ? {
            id: 0, // ID IBGE desconhecido aqui — backend não exige
            nome: retrySearch.cidade,
            uf: retrySearch.uf,
            uf_nome: ufInicial?.nome ?? '',
          }
        : null,
    )
  const [bairroQuery, setBairroQuery] = useState(retrySearch.bairro ?? '')

  const debouncedMunicipio = useDebounce(municipioQuery, 200)

  // Municípios da UF selecionada (sem fetch se UF=null)
  const {
    sugestoes: municipiosSugeridos,
    isLoading: loadingMun,
    total: totalMun,
    fonte: fonteMun,
  } = useMunicipioAutocomplete(debouncedMunicipio, ufSelecionada?.sigla ?? '')

  // Bairros — lista COMPLETA pré-carregada ao selecionar município
  // (multi-letter Places, ~12 chamadas paralelas, cache infinito).
  const { data: bairrosDoMunicipio = [], isFetching: loadingBai } =
    useBairrosDoMunicipio(
      municipioSelecionado?.nome ?? '',
      municipioSelecionado?.uf ?? '',
    )

  // Filtro client-side por texto digitado (caller ainda pode digitar pra refinar)
  const bairrosSugeridos = useMemo(() => {
    const q = bairroQuery
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .trim()
    if (!q) return bairrosDoMunicipio
    return bairrosDoMunicipio.filter((b) =>
      b.bairro
        .normalize('NFD')
        .replace(/[̀-ͯ]/g, '')
        .toLowerCase()
        .includes(q),
    )
  }, [bairrosDoMunicipio, bairroQuery])

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      // Default M de academia (800-1500m² = padrão Smart Fit/Bluefit).
      // Search params (retry) sobrescrevem quando presentes.
      uf: retrySearch.uf,
      municipio: retrySearch.cidade,
      bairro:
        retrySearch.bairro === BAIRRO_CIDADE_INTEIRA
          ? ''
          : (retrySearch.bairro ?? ''),
      cidadeInteira: retrySearch.bairro === BAIRRO_CIDADE_INTEIRA,
      areaMin: retrySearch.area_m2_min ?? 800,
      areaMax: retrySearch.area_m2_max ?? 1500,
      publicoAlvo: (retrySearch.publico_alvo as FormData['publicoAlvo']) ?? '25-40',
      generoAlvo: (retrySearch.genero_alvo as FormData['generoAlvo']) ?? 'misto',
      tipoNegocio: (retrySearch.tipo_negocio as FormData['tipoNegocio']) ?? 'academia',
      tamanho: (retrySearch.tamanho_preset as FormData['tamanho']) ?? 'm',
      estacionamentoObrigatorio: retrySearch.estacionamento_obrigatorio ?? true,
    },
  })

  // Quando o user chegou via retry, mostra aviso explicando que está
  // re-disparando um relatório que falhou antes.
  const veioDeRetry =
    !!(retrySearch.cidade || retrySearch.bairro || retrySearch.uf)

  const watchedBairro = watch('bairro')
  const watchedCidadeInteira = watch('cidadeInteira')
  const watchedTipoNegocio = watch('tipoNegocio') as ModeloNegocio
  const watchedAreaMin = watch('areaMin')
  const watchedAreaMax = watch('areaMax')

  /**
   * Toggle "rodar pela cidade inteira" — desabilita o campo bairro e limpa
   * seleção. O valor real do bairro vai pro payload como sentinela
   * `(cidade inteira)` no momento do submit, não enquanto o user edita,
   * pra não atrapalhar caso ele desmarque depois.
   */
  function toggleCidadeInteira(checked: boolean) {
    setValue('cidadeInteira', checked, { shouldValidate: true })
    if (checked) {
      setBairroQuery('')
      setValue('bairro', '', { shouldValidate: true })
      setValue('bairroPlaceId', '', { shouldValidate: false })
    }
  }

  // Inferência reversa: quando user mexe areaMin/areaMax manualmente, descobre
  // qual tamanho preset corresponde — exibido como hint, sem alterar o select
  // (pra não criar loop infinito).
  const tamanhoInferido = inferirTamanho(
    watchedTipoNegocio,
    Number(watchedAreaMin) || 0,
    Number(watchedAreaMax) || 0,
  )

  /**
   * Quando o usuário troca de tipo de negócio, reseta tamanho pra M (âncora)
   * e auto-preenche areaMin/areaMax do benchmark do novo modelo.
   *
   * Ex: trocou de "academia" (M = 800-1500) pra "studio_pilates" (M = 150-280)
   * → areaMin vai pra 150, areaMax pra 280, tamanho fica "m".
   */
  function selecionarTipoNegocio(novoTipo: ModeloNegocio) {
    setValue('tipoNegocio', novoTipo, { shouldValidate: true })
    const ancora = getTamanhoAncora(novoTipo)
    setValue('tamanho', ancora.codigo, { shouldValidate: true })
    setValue('areaMin', ancora.min, { shouldValidate: true })
    setValue('areaMax', ancora.max, { shouldValidate: true })
  }

  function selecionarTamanho(novoTamanho: TamanhoCodigo) {
    setValue('tamanho', novoTamanho, { shouldValidate: true })
    const faixa = TAMANHOS_POR_MODELO[watchedTipoNegocio]?.find(
      (f) => f.codigo === novoTamanho,
    )
    if (faixa) {
      setValue('areaMin', faixa.min, { shouldValidate: true })
      setValue('areaMax', faixa.max, { shouldValidate: true })
    }
  }

  function selecionarUf(sigla: string) {
    const uf = UFS_BRASIL.find((u) => u.sigla === sigla) ?? null
    setUfSelecionada(uf)
    setValue('uf', uf?.sigla ?? '', { shouldValidate: !!uf })
    // Reseta cascata abaixo
    setMunicipioSelecionado(null)
    setMunicipioQuery('')
    setValue('municipio', '')
    setValue('codigoIbge', 0)
    setBairroQuery('')
    setValue('bairro', '')
    setValue('bairroPlaceId', '')
  }

  function selecionarMunicipio(opt: ComboboxOption<MunicipioIBGE>) {
    if (!opt.payload) return
    setMunicipioSelecionado(opt.payload)
    setMunicipioQuery(opt.payload.nome)
    setValue('municipio', opt.payload.nome, { shouldValidate: true })
    setValue('codigoIbge', opt.payload.id, { shouldValidate: true })
    // Reseta bairro
    setBairroQuery('')
    setValue('bairro', '')
    setValue('bairroPlaceId', '')
  }

  function selecionarBairro(opt: ComboboxOption) {
    setBairroQuery(opt.label)
    setValue('bairro', opt.label, { shouldValidate: true })
    setValue('bairroPlaceId', opt.value)
  }

  const municipioOptions: ComboboxOption<MunicipioIBGE>[] =
    municipiosSugeridos.map((m) => ({
      label: m.nome,
      description: m.uf_nome || m.uf,
      value: String(m.id),
      payload: m,
    }))

  const bairroOptions: ComboboxOption[] = bairrosSugeridos.map((b) => ({
    label: b.bairro,
    description: b.contexto,
    value: b.placeId || b.textoCompleto,
  }))

  /**
   * Converte FormData (camelCase) pro contrato ADK (snake_case + prompt natural).
   *
   * Por que prompt natural ao invés de JSON estruturado:
   * O ADK Agent não tem schema de input formal; o `root_agent` extrai parâmetros
   * via LLM da mensagem do usuário. Texto natural funciona melhor pro Gemini
   * extrair (`cidade`, `bairro`, `genero_alvo`, etc).
   *
   * Quando o backend HTTP for plugado, este é o payload que vai pro POST /run_sse.
   */
  function buildPipelinePayload(data: FormData): {
    prompt: string
    structured_params: Record<string, unknown>
  } {
    const bairroEfetivo = data.cidadeInteira ? BAIRRO_CIDADE_INTEIRA : data.bairro
    const escopo = data.cidadeInteira
      ? `em toda a cidade de ${data.municipio}/${data.uf} (sem restrição de bairro)`
      : `em ${data.bairro}, ${data.municipio}/${data.uf}`
    const prompt = [
      `Análise de viabilidade para academia ${escopo}.`,
      `Parâmetros:`,
      `- area_min: ${data.areaMin} m²`,
      `- area_max: ${data.areaMax} m²`,
      `- publico_alvo: ${data.publicoAlvo}`,
      `- genero_alvo: ${data.generoAlvo}`,
      `- tipo_negocio: ${data.tipoNegocio}`,
      `- estacionamento_obrigatorio: ${data.estacionamentoObrigatorio ? 'sim' : 'não'}`,
      ``,
      `Rode o pipeline completo (GymSitePipeline) com esses parâmetros.`,
    ].join('\n')

    // Mantém também estruturado pra DB writer/audit futuro (snake_case canônico)
    const structured_params = {
      cidade: data.municipio,
      uf: data.uf,
      codigo_ibge: data.codigoIbge,
      bairro: bairroEfetivo,
      bairro_place_id: data.cidadeInteira ? null : (data.bairroPlaceId || null),
      area_m2_min: data.areaMin,
      area_m2_max: data.areaMax,
      tamanho_preset: data.tamanho, // pp|p|m|g|gg — facilita debug/audit
      publico_alvo: data.publicoAlvo,
      genero_alvo: data.generoAlvo,
      tipo_negocio: data.tipoNegocio,
      estacionamento_obrigatorio: data.estacionamentoObrigatorio,
    }

    return { prompt, structured_params }
  }

  const [submitError, setSubmitError] = useState<string | null>(null)

  async function onSubmit(data: FormData) {
    setSubmitError(null)
    const { structured_params } = buildPipelinePayload(data)

    try {
      // Envia o JWT do user pro backend — em breve o FastAPI vai exigir
      // auth e amarrar o relatório à org_id do user.
      const { data: { session } } = await supabase.auth.getSession()
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      const res = await fetch(`${API_BASE}/api/relatorios`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          cidade: structured_params.cidade,
          uf: structured_params.uf,
          bairro: structured_params.bairro,
          area_m2_min: structured_params.area_m2_min,
          area_m2_max: structured_params.area_m2_max,
          tamanho_preset: structured_params.tamanho_preset,
          publico_alvo: structured_params.publico_alvo,
          genero_alvo: structured_params.genero_alvo,
          tipo_negocio: structured_params.tipo_negocio,
          estacionamento_obrigatorio: structured_params.estacionamento_obrigatorio,
        }),
      })

      if (!res.ok) {
        const body = await res.text().catch(() => '')
        throw new Error(`API ${res.status}: ${body.slice(0, 200)}`)
      }

      const { id } = (await res.json()) as { id: string }

      // Redirect pra status page que polla até pipeline completar
      navigate({
        to: '/relatorios/$relatorioId/aguardando',
        params: { relatorioId: id },
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setSubmitError(msg)
      console.error('[NovoRelatorio] submit falhou:', err)
    }
  }

  function handleSubmitWrapper(e: FormEvent) {
    void handleSubmit(onSubmit)(e)
  }

  // Pronto pra submeter: UF + município + (bairro OU modo cidade inteira)
  const podeSubmeter =
    !!ufSelecionada &&
    !!municipioSelecionado &&
    (watchedCidadeInteira || (!!watchedBairro && watchedBairro.length >= 2))

  return (
    <div className="container max-w-2xl py-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          Novo Relatório
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Defina o estado, município e bairro alvo. O pipeline produz o
          relatório completo de viabilidade comercial.
        </p>
      </header>

      {/* Aviso de retry quando user veio da tela de falha */}
      {veioDeRetry ? (
        <div className="mb-6 rounded-lg border border-status-warning/40 bg-status-warning/5 p-3.5 flex items-start gap-3 text-xs">
          <RefreshCw size={14} className="text-status-warning flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5 leading-relaxed">
            <p className="text-foreground font-medium">
              Tentando novamente com os mesmos parâmetros
            </p>
            <p className="text-muted-foreground">
              Os campos foram preenchidos automaticamente. Revise se algo precisa
              mudar antes de gerar. Vai criar um relatório novo — o falho continua
              no histórico pra auditoria.
            </p>
          </div>
        </div>
      ) : (
        <div className="mb-6 rounded-lg border border-border bg-card/60 p-3.5 flex items-start gap-3 text-xs">
          <Clock size={14} className="text-muted-foreground flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5 leading-relaxed">
            <p className="text-foreground font-medium">
              Pipelines simultâneos podem demorar mais que 5min
            </p>
            <p className="text-muted-foreground">
              Se outras pessoas da sua organização também estiverem gerando relatórios
              agora, aguarde ~3 minutos entre disparos. Isso evita filas e mantém a
              qualidade da análise.
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmitWrapper} className="space-y-6">
        {/* Localização (árvore Estado → Município → Bairro) */}
        <section className="rounded-lg border border-border bg-card/40 p-5 space-y-4">
          <h2 className="text-xs uppercase tracking-wider font-mono font-medium text-muted-foreground">
            Localização alvo
          </h2>

          {/* 1. Estado */}
          <Field label="Estado" error={errors.uf?.message}>
            <SelectGrouped
              value={ufSelecionada?.sigla}
              onChange={(v) => selecionarUf(v)}
              placeholder="— Selecione um estado —"
              ariaInvalid={!!errors.uf || undefined}
              groups={(
                ['Sudeste', 'Sul', 'Nordeste', 'Centro-Oeste', 'Norte'] as const
              ).map((regiao) => ({
                label: regiao,
                options: (UFS_POR_REGIAO[regiao] ?? []).map((uf) => ({
                  value: uf.sigla,
                  label: `${uf.sigla} — ${uf.nome}`,
                })),
              }))}
            />
          </Field>

          {/* 2. Município */}
          <Field
            label="Município"
            hint={
              !ufSelecionada
                ? 'Selecione um estado primeiro'
                : loadingMun
                  ? 'Carregando municípios do IBGE…'
                  : fonteMun === 'fallback'
                    ? `⚠ IBGE indisponível — usando ${totalMun} municípios em cache local de ${ufSelecionada.nome}`
                    : `${totalMun} municípios em ${ufSelecionada.nome} · digite pra filtrar`
            }
            error={errors.municipio?.message}
          >
            <Combobox<MunicipioIBGE>
              inputValue={municipioQuery}
              onInputChange={(v) => {
                setMunicipioQuery(v)
                if (municipioSelecionado && v !== municipioSelecionado.nome) {
                  setMunicipioSelecionado(null)
                  setValue('municipio', '')
                  setValue('codigoIbge', 0)
                }
              }}
              options={municipioOptions}
              onSelect={selecionarMunicipio}
              isLoading={loadingMun}
              placeholder={
                ufSelecionada
                  ? `Ex: ${ufSelecionada.sigla === 'CE' ? 'Eusébio, Fortaleza' : 'capital, interior'}…`
                  : 'Aguardando estado'
              }
              disabled={!ufSelecionada}
              ariaInvalid={!!errors.municipio}
              minChars={0}
              emptyMessage={
                <span>
                  Nenhum município em {ufSelecionada?.sigla} contém "
                  {municipioQuery}"
                </span>
              }
            />
            {municipioSelecionado && (
              <p className="text-xs text-muted-foreground mt-1.5">
                IBGE {municipioSelecionado.id} ·{' '}
                {municipioSelecionado.uf_nome || municipioSelecionado.uf}
              </p>
            )}
          </Field>

          {/* 3. Bairro — dropdown com lista pré-carregada do município */}
          <Field
            label="Bairro"
            hint={
              !municipioSelecionado
                ? 'Selecione um município primeiro'
                : watchedCidadeInteira
                  ? 'Modo cidade inteira ativo — bairro desabilitado'
                  : loadingBai
                    ? 'Carregando bairros (Google Places)…'
                    : bairrosDoMunicipio.length === 0
                      ? 'Nenhum bairro encontrado — digite manualmente'
                      : `${bairrosDoMunicipio.length} bairros em ${municipioSelecionado.nome} · clique pra abrir`
            }
            error={errors.bairro?.message}
          >
            <Combobox
              inputValue={bairroQuery}
              onInputChange={(v) => {
                setBairroQuery(v)
                if (!v) {
                  setValue('bairro', '')
                  setValue('bairroPlaceId', '')
                }
              }}
              options={bairroOptions}
              onSelect={selecionarBairro}
              isLoading={loadingBai}
              placeholder={
                watchedCidadeInteira
                  ? '— pipeline rodará pela cidade inteira —'
                  : municipioSelecionado
                    ? 'Clique pra abrir lista ou digite pra filtrar'
                    : 'Aguardando município'
              }
              disabled={!municipioSelecionado || watchedCidadeInteira}
              ariaInvalid={!!errors.bairro}
              minChars={0}
              emptyMessage={
                <span>
                  {bairroQuery
                    ? `Sem bairros pra "${bairroQuery}".`
                    : 'Lista vazia.'}{' '}
                  {bairroQuery && (
                    <button
                      type="button"
                      className="underline text-primary"
                      onMouseDown={(e) => {
                        e.preventDefault()
                        setValue('bairro', bairroQuery, {
                          shouldValidate: true,
                        })
                      }}
                    >
                      Usar mesmo assim
                    </button>
                  )}
                </span>
              }
            />

            {/* Checkbox: cidade inteira (libera submit sem bairro) */}
            <label
              className={`mt-2.5 flex items-start gap-2 cursor-pointer text-sm select-none ${
                !municipioSelecionado ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-primary"
                checked={watchedCidadeInteira}
                disabled={!municipioSelecionado}
                onChange={(e) => toggleCidadeInteira(e.target.checked)}
              />
              <span className="leading-tight">
                <span className="font-medium">Rodar pela cidade inteira</span>
                <span className="block text-xs text-muted-foreground">
                  Sem filtro de bairro. Pipeline varre todos os bairros do
                  município — custo e tempo de execução maiores.
                </span>
              </span>
            </label>
          </Field>
        </section>

        {/* Parâmetros do imóvel */}
        <section className="rounded-lg border border-border bg-card/40 p-5 space-y-4">
          <h2 className="text-xs uppercase tracking-wider font-mono font-medium text-muted-foreground">
            Parâmetros do imóvel
          </h2>

          {/* Tipo de negócio — define os presets de tamanho */}
          <Field label="Tipo de negócio" error={errors.tipoNegocio?.message}>
            <SelectGrouped
              value={watchedTipoNegocio}
              onChange={(v) => selecionarTipoNegocio(v as ModeloNegocio)}
              options={[
                { value: 'academia', label: 'Academia tradicional' },
                { value: 'crossfit_box', label: 'CrossFit / Box' },
                { value: 'studio_pilates', label: 'Estúdio Pilates' },
                { value: 'studio_funcional', label: 'Studio Funcional' },
                { value: 'outro', label: 'Outro' },
              ]}
            />
          </Field>

          {/* Tamanho preset (chips PP/P/M/G/GG por modelo) */}
          <Field
            label="Tamanho (benchmark de mercado)"
            hint={`Clique pra preencher área automaticamente · ${tamanhoInferido ? `inferido: ${tamanhoInferido.toUpperCase()}` : 'área custom'}`}
            error={errors.tamanho?.message}
          >
            <div className="grid grid-cols-5 gap-2">
              {TAMANHOS_POR_MODELO[watchedTipoNegocio]?.map((faixa) => {
                const ativo = watch('tamanho') === faixa.codigo
                return (
                  <button
                    type="button"
                    key={faixa.codigo}
                    onClick={() => selecionarTamanho(faixa.codigo)}
                    className={cn(
                      'rounded-md border px-2 py-2 text-left transition-colors',
                      ativo
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50 hover:bg-muted/40',
                    )}
                  >
                    <div className="text-sm font-semibold font-mono">
                      {faixa.label}
                    </div>
                    <div className="text-[10px] text-muted-foreground leading-tight">
                      {faixa.min.toLocaleString('pt-BR')}–
                      {faixa.max.toLocaleString('pt-BR')} m²
                    </div>
                    {faixa.codigo === 'm' && (
                      <div className="text-[9px] text-primary mt-0.5">★ mais comum</div>
                    )}
                  </button>
                )
              })}
            </div>
            {watchedTipoNegocio && (
              <p className="text-[10px] text-muted-foreground mt-1.5">
                {TAMANHOS_POR_MODELO[watchedTipoNegocio]?.find(
                  (f) => f.codigo === watch('tamanho'),
                )?.descricao}
                {(() => {
                  const f = TAMANHOS_POR_MODELO[watchedTipoNegocio]?.find(
                    (f) => f.codigo === watch('tamanho'),
                  )
                  return f?.exemploRede ? ` · ex: ${f.exemploRede}` : ''
                })()}
              </p>
            )}
          </Field>

          {/* Área manual (override do preset) */}
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Área mínima (m²)"
              hint="Override manual do preset acima"
              error={errors.areaMin?.message}
            >
              <Input
                type="number"
                min={50}
                max={10000}
                step={50}
                {...register('areaMin', { valueAsNumber: true })}
              />
            </Field>
            <Field
              label="Área máxima (m²)"
              hint="Override manual do preset acima"
              error={errors.areaMax?.message}
            >
              <Input
                type="number"
                min={50}
                max={10000}
                step={50}
                {...register('areaMax', { valueAsNumber: true })}
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Público-alvo (idade)" error={errors.publicoAlvo?.message}>
              <SelectGrouped
                value={watch('publicoAlvo')}
                onChange={(v) => setValue('publicoAlvo', v as FormData['publicoAlvo'], { shouldDirty: true })}
                options={[
                  { value: '18-29', label: '18–29 anos' },
                  { value: '25-40', label: '25–40 anos' },
                  { value: '30-50', label: '30–50 anos' },
                  { value: '40+', label: '40+ anos' },
                ]}
              />
            </Field>
            <Field
              label="Gênero alvo"
              hint="Calibra ticket e mix de serviços (Pilates ↑ feminino, CrossFit ↑ masculino)"
              error={errors.generoAlvo?.message}
            >
              <SelectGrouped
                value={watch('generoAlvo')}
                onChange={(v) => setValue('generoAlvo', v as FormData['generoAlvo'], { shouldDirty: true })}
                options={[
                  { value: 'misto', label: 'Misto (50/50)' },
                  { value: 'predominantemente_feminino', label: 'Predominantemente feminino' },
                  { value: 'predominantemente_masculino', label: 'Predominantemente masculino' },
                  { value: 'exclusivamente_feminino', label: 'Exclusivamente feminino (academia para mulheres)' },
                  { value: 'exclusivamente_masculino', label: 'Exclusivamente masculino' },
                ]}
              />
            </Field>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              {...register('estacionamentoObrigatorio')}
              className="rounded border-border"
            />
            Estacionamento obrigatório no imóvel
          </label>
        </section>

        {submitError && (
          <div
            role="alert"
            className="rounded-md border border-status-critical/40 bg-status-critical/5 p-3 text-xs space-y-1"
          >
            <p className="font-semibold text-status-critical">
              Falha ao iniciar pipeline
            </p>
            <p className="font-mono text-muted-foreground break-all">
              {submitError}
            </p>
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <Button
            type="submit"
            disabled={isSubmitting || !podeSubmeter}
            className="gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Disparando…
              </>
            ) : (
              <>
                Iniciar análise
                <ArrowRight size={14} />
              </>
            )}
          </Button>
          {isAdmin && (
            <p className="text-xs text-muted-foreground">Pipeline ~5min</p>
          )}
        </div>
      </form>
    </div>
  )
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs uppercase tracking-wider font-mono font-medium text-muted-foreground">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-xs text-veredito-reprovado">{error}</p>
      ) : (
        hint && <p className="text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  )
}
