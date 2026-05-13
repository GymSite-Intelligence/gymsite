/**
 * PinVeredito — marcador SVG colorido por veredito.
 *
 * Usado dentro de `pigeon-maps` (Marker custom). A cor segue o token
 * `veredito-*` do tailwind config — verde/amarelo/azul/vermelho.
 *
 * Tamanho fixo 32x40 (mesmo aspect ratio que pin Google Maps clássico).
 */
import type { Veredito } from '@/types/domain'

const VEREDITO_HEX: Record<Veredito, string> = {
  APROVADO: 'hsl(142 70% 45%)',
  'APROVADO COM RESSALVAS': 'hsl(45 95% 55%)',
  'INVESTIGAR MAIS': 'hsl(210 80% 55%)',
  REPROVADO: 'hsl(0 70% 50%)',
}

export interface PinVereditoProps {
  veredito: Veredito
  /** Ativo no painel lateral — pin maior + sombra mais forte (preview). */
  ativo?: boolean
  /** Selecionado pra comparação — borda destacada + checkmark sobre o pin. */
  selecionado?: boolean
  /** Quantidade de relatórios co-localizados nesse ponto (default 1). */
  count?: number
}

export function PinVeredito({
  veredito,
  ativo,
  selecionado,
  count = 1,
}: PinVereditoProps) {
  const color = VEREDITO_HEX[veredito] ?? 'hsl(0 0% 50%)'
  const size = selecionado || ativo ? 40 : count > 1 ? 36 : 32

  // ZERO event handlers — todos vão pro `<Marker>` do pigeon-maps que
  // gerencia diferença click/pan/drag corretamente. O div é puro visual.
  return (
    <div
      aria-label={`Relatório ${veredito}${count > 1 ? ` (${count} no mesmo ponto)` : ''}`}
      style={{
        cursor: 'pointer',
        userSelect: 'none',
        marginLeft: -size / 2,
        marginTop: -size,
        padding: 2,
      }}
    >
      <svg
        width={size}
        height={size * 1.25}
        viewBox="0 0 32 40"
        style={{
          filter: selecionado
            ? 'drop-shadow(0 0 0 3px hsl(220 90% 60%)) drop-shadow(0 4px 10px rgba(0,0,0,0.55))'
            : ativo
              ? 'drop-shadow(0 4px 8px rgba(0,0,0,0.5))'
              : 'drop-shadow(0 2px 3px rgba(0,0,0,0.35))',
          transition: 'all 0.15s',
          // pigeon-maps renderiza Marker dentro de `div.pigeon-click-block`
          // que tem `pointer-events: none` hardcoded. Quando usamos children
          // customizados (em vez do SVG default do pigeon), o `<g>` interno
          // com `pointer-events: auto` não existe — nenhum elemento captura
          // o click. Setar auto aqui no SVG resolve.
          pointerEvents: 'auto',
        }}
      >
        <path
          d="M16 0 C7.16 0 0 7.16 0 16 C0 27 16 40 16 40 C16 40 32 27 32 16 C32 7.16 24.84 0 16 0 Z"
          fill={color}
          stroke={selecionado ? 'hsl(220 90% 60%)' : 'white'}
          strokeWidth={selecionado ? 3 : count > 1 ? 2 : 1.5}
        />
        {count > 1 ? (
          // Badge contador no centro do pin
          <text
            x={16}
            y={20}
            textAnchor="middle"
            fontFamily="ui-sans-serif, system-ui"
            fontSize={13}
            fontWeight={700}
            fill="white"
          >
            {count}
          </text>
        ) : selecionado ? (
          // Checkmark grande pra selecionado solo
          <path
            d="M11 16 L14.5 19 L21 12.5"
            stroke="white"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        ) : (
          <circle cx={16} cy={15} r={5} fill="white" />
        )}
      </svg>
    </div>
  )
}
