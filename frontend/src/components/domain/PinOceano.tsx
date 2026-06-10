/**
 * PinOceano — marcador SVG colorido por veredito A9 (oceano azul / transição / vermelho).
 */
import {
  normalizeVereditoOceano,
  OCEANO_CONFIG,
  OCEANO_FILL,
  OCEANO_FILL_SEM_A9,
} from '@/lib/oceano'
import type { VereditoOceano } from '@/types/domain'

export interface PinOceanoProps {
  veredito: VereditoOceano | string | null | undefined
  ativo?: boolean
  selecionado?: boolean
  count?: number
}

export function PinOceano({
  veredito,
  ativo,
  selecionado,
  count = 1,
}: PinOceanoProps) {
  const key = normalizeVereditoOceano(veredito)
  const color = key ? OCEANO_FILL[key] : OCEANO_FILL_SEM_A9
  const label = key ? OCEANO_CONFIG[key].label : 'Sem A9'
  const size = selecionado || ativo ? 40 : count > 1 ? 36 : 32

  return (
    <div
      aria-label={`Posicionamento ${label}${count > 1 ? ` (${count} no mesmo ponto)` : ''}`}
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
          <text
            x={16}
            y={20}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="white"
            fontSize={12}
            fontWeight="bold"
          >
            {count}
          </text>
        ) : key ? (
          <text
            x={16}
            y={19}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={14}
          >
            {OCEANO_CONFIG[key].emoji}
          </text>
        ) : null}
      </svg>
    </div>
  )
}
