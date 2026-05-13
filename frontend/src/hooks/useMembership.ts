/**
 * hooks/useMembership.ts — memberships do user logado.
 *
 * Retorna a lista completa de memberships. Multi-tenant ready: quando o
 * user é membro de várias orgs (ex.: consultoria operando N academias),
 * podemos exibir tudo no dashboard de custos.
 *
 * Compat: `orgId`/`role`/`isOwnerOrAdmin` apontam pro membership "ativo"
 * (hoje o primeiro retornado). Quando OrgDropdown #122 chegar, este hook
 * passa a aceitar `activeOrgId` e filtra.
 */
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'

export type MembershipRole = 'owner' | 'admin' | 'member' | string

export interface Membership {
  orgId: string
  orgNome: string
  role: MembershipRole
}

export interface MembershipInfo {
  memberships: Membership[]
  /** Membership "ativo" — hoje o primeiro. Conveniente pra single-tenant. */
  orgId: string | null
  orgNome: string | null
  role: MembershipRole | null
  isOwner: boolean
  isAdmin: boolean
  isOwnerOrAdmin: boolean
  /** True se user tem 2+ orgs distintas (visão multi-tenant). */
  isMultiOrg: boolean
  loading: boolean
}

export function useMembership(): MembershipInfo {
  const { user } = useAuth()

  const { data, isLoading } = useQuery({
    queryKey: ['memberships', user?.id ?? 'anon'],
    enabled: !!user,
    meta: { silent: true },
    queryFn: async (): Promise<Membership[]> => {
      const { data, error } = await supabase
        .from('organization_members')
        .select('org_id, role, organizations(nome)')
        .eq('user_id', user!.id)
      if (error) throw new Error(`Supabase: ${error.message}`)

      return ((data ?? []) as Array<{
        org_id: string
        role: string
        organizations: { nome: string } | { nome: string }[] | null
      }>).map((row) => {
        const org = Array.isArray(row.organizations)
          ? row.organizations[0]
          : row.organizations
        return {
          orgId: row.org_id,
          orgNome: org?.nome ?? '?',
          role: row.role as MembershipRole,
        }
      })
    },
  })

  const memberships = data ?? []
  const active = memberships[0] ?? null
  const role = active?.role ?? null
  const isOwner = role === 'owner'
  const isAdmin = role === 'admin'

  return {
    memberships,
    orgId: active?.orgId ?? null,
    orgNome: active?.orgNome ?? null,
    role,
    isOwner,
    isAdmin,
    isOwnerOrAdmin: isOwner || isAdmin,
    isMultiOrg: memberships.length >= 2,
    loading: isLoading,
  }
}
