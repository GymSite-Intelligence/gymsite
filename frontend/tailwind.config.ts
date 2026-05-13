import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: { '2xl': '1400px' },
    },
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        // Paleta GymSite (dark dashboard, distinta da Vectra)
        background: 'hsl(220 14% 8%)',
        foreground: 'hsl(0 0% 98%)',
        card: 'hsl(220 14% 11%)',
        'card-foreground': 'hsl(0 0% 98%)',
        muted: 'hsl(220 10% 18%)',
        'muted-foreground': 'hsl(0 0% 65%)',
        border: 'hsl(220 10% 18%)',
        primary: 'hsl(142 70% 45%)',          // verde fitness
        'primary-foreground': 'hsl(0 0% 100%)',
        // Vereditos (legacy — manter pra compat, novos componentes usam status-*)
        'veredito-aprovado': 'hsl(142 70% 45%)',
        'veredito-ressalvas': 'hsl(45 95% 55%)',
        'veredito-investigar': 'hsl(210 80% 55%)',
        'veredito-reprovado': 'hsl(0 70% 50%)',
        // Tokens semânticos de status (novos componentes preferem estes)
        'status-good': 'hsl(var(--status-good))',
        'status-warning': 'hsl(var(--status-warning))',
        'status-investigate': 'hsl(var(--status-investigate))',
        'status-critical': 'hsl(var(--status-critical))',
        'status-neutral': 'hsl(var(--status-neutral))',
        // Categorias de dor (taxonomia A3a — 14 cats)
        'dor-lotacao': 'hsl(25 90% 55%)',
        'dor-equipamento': 'hsl(0 75% 55%)',
        'dor-climatizacao': 'hsl(195 80% 55%)',
        'dor-limpeza': 'hsl(165 60% 50%)',
        'dor-atendimento': 'hsl(280 65% 60%)',
        'dor-preco': 'hsl(50 90% 55%)',
        'dor-contrato': 'hsl(330 70% 55%)',
        'dor-estacionamento': 'hsl(210 50% 55%)',
        'dor-estrutura': 'hsl(15 65% 50%)',
        'dor-ruido': 'hsl(260 60% 60%)',
        'dor-horarios': 'hsl(180 50% 50%)',
        'dor-servico': 'hsl(85 55% 50%)',
        'dor-seguranca': 'hsl(0 85% 45%)',
        'dor-outra': 'hsl(220 10% 50%)',
      },
      borderRadius: {
        lg: '0.5rem',
        md: '0.375rem',
        sm: '0.25rem',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [animate],
} satisfies Config
