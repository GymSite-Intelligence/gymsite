/**
 * Validade de senha para testers — metadata em auth.users.user_metadata.
 *
 * Admin define via:
 *   python tools/admin_invite_tester.py set-password --email ... --senha ... --valido-dias 14
 */
import type { User } from '@supabase/supabase-js'

const KEY = 'password_expires_at'

export function getPasswordExpiresAt(user: User | null | undefined): Date | null {
  if (!user) return null
  const raw = user.user_metadata?.[KEY]
  if (typeof raw !== 'string' || !raw.trim()) return null
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? null : d
}

export function isTesterUser(user: User | null | undefined): boolean {
  return user?.user_metadata?.tester === true
}

export function isPasswordExpired(user: User | null | undefined): boolean {
  const expires = getPasswordExpiresAt(user)
  if (!expires) return false
  return Date.now() >= expires.getTime()
}

export function formatPasswordExpiry(user: User | null | undefined): string | null {
  const expires = getPasswordExpiresAt(user)
  if (!expires) return null
  return expires.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function passwordExpiryErrorMessage(user: User | null | undefined): string {
  const when = formatPasswordExpiry(user)
  return when
    ? `Sua senha de teste expirou em ${when}. Peça uma nova ao administrador.`
    : 'Sua senha de teste expirou. Peça uma nova ao administrador.'
}
