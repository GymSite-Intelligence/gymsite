import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * cn() — utilitário padrão do shadcn/ui pra mesclar classes Tailwind
 * resolvendo conflitos (twMerge) e aceitando arrays/booleanos (clsx).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
