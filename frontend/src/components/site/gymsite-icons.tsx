// ============================================================
// components/icons/gymsite-icons.tsx
// Ícones SVG dos 5 Setores — GymSite Intelligence v2.1
// Estilo: robô com objeto temático (verde #84cc16 / branco / cinza escuro)
// Uso: <IconeDados className="h-4 w-4" />
// ============================================================

import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement> & { className?: string }

// ============================================================
// DADOS — Robô com gráfico de barras em nuvem (azul no badge)
// ============================================================
export function IconeDados({ className, ...props }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      {/* Cabeça do robô */}
      <rect x="7" y="2" width="10" height="8" rx="3" />
      {/* Olhos */}
      <circle cx="10" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="14" cy="6" r="1" fill="currentColor" stroke="none" />
      {/* Antena */}
      <line x1="12" y1="2" x2="12" y2="0.5" />
      <circle cx="12" cy="0.5" r="0.5" fill="currentColor" stroke="none" />
      {/* Corpo */}
      <rect x="6" y="11" width="12" height="8" rx="2" />
      {/* Braços */}
      <line x1="6" y1="13" x2="3" y2="15" />
      <line x1="18" y1="13" x2="21" y2="15" />
      {/* Gráfico de barras no peito */}
      <line x1="9" y1="17" x2="9" y2="15" strokeWidth="2" />
      <line x1="12" y1="17" x2="12" y2="13.5" strokeWidth="2" />
      <line x1="15" y1="17" x2="15" y2="14.5" strokeWidth="2" />
    </svg>
  )
}

// ============================================================
// FINANCEIRO — Robô com seta de crescimento e baú (emerald no badge)
// ============================================================
export function IconeFinanceiro({ className, ...props }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      {/* Cabeça do robô */}
      <rect x="7" y="2" width="10" height="8" rx="3" />
      <circle cx="10" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="14" cy="6" r="1" fill="currentColor" stroke="none" />
      <line x1="12" y1="2" x2="12" y2="0.5" />
      <circle cx="12" cy="0.5" r="0.5" fill="currentColor" stroke="none" />
      {/* Corpo */}
      <rect x="6" y="11" width="12" height="8" rx="2" />
      {/* Braços */}
      <line x1="6" y1="13" x2="3" y2="15" />
      <line x1="18" y1="13" x2="21" y2="15" />
      {/* Seta de crescimento no peito */}
      <polyline points="8,17 11,14 13,16 16,13" />
      <polyline points="14,13 16,13 16,15" />
    </svg>
  )
}

// ============================================================
// CONTABILIDADE — Robô com ábaco e planilha (amber no badge)
// ============================================================
export function IconeContabilidade({ className, ...props }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      {/* Cabeça do robô */}
      <rect x="7" y="2" width="10" height="8" rx="3" />
      <circle cx="10" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="14" cy="6" r="1" fill="currentColor" stroke="none" />
      <line x1="12" y1="2" x2="12" y2="0.5" />
      <circle cx="12" cy="0.5" r="0.5" fill="currentColor" stroke="none" />
      {/* Corpo */}
      <rect x="6" y="11" width="12" height="8" rx="2" />
      {/* Braços */}
      <line x1="6" y1="13" x2="3" y2="15" />
      <line x1="18" y1="13" x2="21" y2="15" />
      {/* Planilha / grid no peito */}
      <rect x="9" y="13" width="6" height="5" rx="0.5" />
      <line x1="12" y1="13" x2="12" y2="18" />
      <line x1="9" y1="15.5" x2="15" y2="15.5" />
    </svg>
  )
}

// ============================================================
// MARKETING — Robô com alvo e megafone (violet no badge)
// ============================================================
export function IconeMarketing({ className, ...props }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      {/* Cabeça do robô */}
      <rect x="7" y="2" width="10" height="8" rx="3" />
      <circle cx="10" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="14" cy="6" r="1" fill="currentColor" stroke="none" />
      <line x1="12" y1="2" x2="12" y2="0.5" />
      <circle cx="12" cy="0.5" r="0.5" fill="currentColor" stroke="none" />
      {/* Corpo */}
      <rect x="6" y="11" width="12" height="8" rx="2" />
      {/* Braços */}
      <line x1="6" y1="13" x2="3" y2="15" />
      <line x1="18" y1="13" x2="21" y2="15" />
      {/* Alvo no peito */}
      <circle cx="12" cy="15.5" r="3" />
      <circle cx="12" cy="15.5" r="1.2" />
      <circle cx="12" cy="15.5" r="0.3" fill="currentColor" stroke="none" />
    </svg>
  )
}

// ============================================================
// CONHECIMENTO — Robô com cérebro/engrenagem e livro (rose no badge)
// ============================================================
export function IconeConhecimento({ className, ...props }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      {/* Cabeça do robô */}
      <rect x="7" y="2" width="10" height="8" rx="3" />
      <circle cx="10" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="14" cy="6" r="1" fill="currentColor" stroke="none" />
      <line x1="12" y1="2" x2="12" y2="0.5" />
      <circle cx="12" cy="0.5" r="0.5" fill="currentColor" stroke="none" />
      {/* Corpo */}
      <rect x="6" y="11" width="12" height="8" rx="2" />
      {/* Braços */}
      <line x1="6" y1="13" x2="3" y2="15" />
      <line x1="18" y1="13" x2="21" y2="15" />
      {/* Livro aberto + faísca de insight no peito */}
      <path d="M9 14 Q9 13 12 13 Q15 13 15 14 L15 18 Q12 17 9 18 Z" />
      <line x1="12" y1="13" x2="12" y2="18" />
      {/* Faísca acima */}
      <path d="M13.5 11.5 L12.5 13 L14 12.5 L13 14" strokeWidth="1.2" />
    </svg>
  )
}

// ============================================================
// TÉCNICO — Robô com halter (equipamentos)
// ============================================================
export function IconeTecnico({ className, ...props }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
      className={className} aria-hidden="true" {...props}>
      {/* antena + cabeça do robô */}
      <path d="M12 2.5v1.6" />
      <circle cx="12" cy="2" r="0.6" fill="currentColor" stroke="none" />
      <rect x="6" y="4" width="12" height="8.5" rx="2.2" />
      <circle cx="9.5" cy="8" r="1" />
      <circle cx="14.5" cy="8" r="1" />
      <path d="M9.5 10.8h5" />
      {/* halter / barra de peso */}
      <path d="M4 19h16" />
      <path d="M6 16.5v5M9 15.5v7M15 15.5v7M18 16.5v5" />
    </svg>
  )
}
