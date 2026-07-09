import { useMemo, useState } from 'react'
import { UFS_BRASIL } from '@/data/ufs-brasil'
import { MUNICIPIOS_BRASIL } from '@/data/municipios-brasil'
import { buscarObrasCno, type CnoObra } from '@/lib/cno-api'

// Ferramenta interna de teste: busca obras EM CURSO do CNO por UF + Cidade (+ bairro).
// Read-only. Cidade -> id IBGE via MUNICIPIOS_BRASIL (offline).

const SITUACAO_LABEL: Record<string, string> = {
  '01': 'Ativo',
  '02': 'Ativo',
  '03': 'Em curso',
  '04': 'Em curso',
  '1': 'Ativo',
  '2': 'Ativo',
  '3': 'Em curso',
  '4': 'Em curso',
}

function endereco(o: CnoObra): string {
  const p = [o.tipo_logradouro, o.logradouro].filter(Boolean).join(' ')
  return [p, o.numero_logradouro].filter(Boolean).join(', ') || '—'
}
function fmtArea(a: number | null): string {
  return a == null ? '—' : `${a.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} m²`
}
function fmtData(d: string | null): string {
  return d ? new Date(d).toLocaleDateString('pt-BR') : '—'
}

export function CnoObrasPage() {
  const [uf, setUf] = useState('')
  const [municipioId, setMunicipioId] = useState<number | ''>('')
  const [bairro, setBairro] = useState('')
  const [residencial, setResidencial] = useState(true)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [resultado, setResultado] = useState<{ total: number; obras: CnoObra[] } | null>(null)

  const cidadesDaUf = useMemo(
    () => (uf ? MUNICIPIOS_BRASIL.filter((m) => m.uf === uf) : []),
    [uf],
  )

  const buscar = async () => {
    if (!uf) {
      setErro('Escolha a UF.')
      return
    }
    setCarregando(true)
    setErro(null)
    try {
      const r = await buscarObrasCno({
        uf,
        municipioId: municipioId === '' ? undefined : municipioId,
        bairro: bairro.trim() || undefined,
        residencial,
      })
      setResultado(r)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao buscar.')
      setResultado(null)
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Obras CNO em curso</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Busca obras residenciais em andamento (Cadastro Nacional de Obras) por UF e cidade.
          Fonte: RFB CNO · basedosdados. Ferramenta interna de consulta.
        </p>
      </header>

      <div className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border border-border bg-card p-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">UF</span>
          <select
            className="h-9 rounded-md border border-border bg-background px-2"
            value={uf}
            onChange={(e) => {
              setUf(e.target.value)
              setMunicipioId('')
            }}
          >
            <option value="">Selecione…</option>
            {UFS_BRASIL.map((u) => (
              <option key={u.sigla} value={u.sigla}>
                {u.sigla} — {u.nome}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">Cidade</span>
          <select
            className="h-9 min-w-52 rounded-md border border-border bg-background px-2 disabled:opacity-50"
            value={municipioId}
            disabled={!uf}
            onChange={(e) => setMunicipioId(e.target.value ? Number(e.target.value) : '')}
          >
            <option value="">Todas as cidades da UF</option>
            {cidadesDaUf.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nome}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">Bairro (opcional)</span>
          <input
            className="h-9 rounded-md border border-border bg-background px-2"
            value={bairro}
            onChange={(e) => setBairro(e.target.value)}
            placeholder="Ex.: Manaíra"
          />
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={residencial}
            onChange={(e) => setResidencial(e.target.checked)}
          />
          <span>Só residencial</span>
        </label>

        <button
          type="button"
          onClick={buscar}
          disabled={carregando}
          className="h-9 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {carregando ? 'Buscando…' : 'Buscar'}
        </button>
      </div>

      {erro && <p className="mb-4 text-sm text-destructive">{erro}</p>}

      {resultado && (
        <>
          <p className="mb-2 text-sm text-muted-foreground">
            {resultado.total} obra(s) em curso · exibindo {resultado.obras.length}
          </p>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">Nome</th>
                  <th className="px-3 py-2 font-medium">Área</th>
                  <th className="px-3 py-2 font-medium">Endereço</th>
                  <th className="px-3 py-2 font-medium">Bairro</th>
                  <th className="px-3 py-2 font-medium">Início</th>
                  <th className="px-3 py-2 font-medium">Situação</th>
                  <th className="px-3 py-2 font-medium">CNO</th>
                </tr>
              </thead>
              <tbody>
                {resultado.obras.map((o) => (
                  <tr key={o.id_cno} className="border-t border-border">
                    <td className="px-3 py-2">{o.nome?.trim() || '—'}</td>
                    <td className="px-3 py-2 tabular-nums">{fmtArea(o.area_m2)}</td>
                    <td className="px-3 py-2">{endereco(o)}</td>
                    <td className="px-3 py-2">{o.bairro?.trim() || '—'}</td>
                    <td className="px-3 py-2 tabular-nums">{fmtData(o.data_inicio)}</td>
                    <td className="px-3 py-2">{SITUACAO_LABEL[o.situacao ?? ''] ?? o.situacao ?? '—'}</td>
                    <td className="px-3 py-2 tabular-nums text-muted-foreground">{o.id_cno}</td>
                  </tr>
                ))}
                {resultado.obras.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-6 text-center text-muted-foreground">
                      Nenhuma obra em curso para esse filtro.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
