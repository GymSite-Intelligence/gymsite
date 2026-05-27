/**
 * PerfilPage — edita nome de exibição + avatar do user logado.
 *
 * Storage:
 *   - Avatar salvo em bucket `avatars/{user_id}/avatar.{ext}`
 *   - RLS impede upload em folder de outro user (policy `Avatar uploads pelo dono`)
 *   - Bucket é público (leitura) — URL direta no AppShell sem precisar signed URL
 *
 * User metadata:
 *   - full_name: salvo em `auth.users.user_metadata.full_name` via updateUser
 *   - avatar_url: idem
 */
import { useEffect, useRef, useState } from 'react'
import { Loader2, Upload, Trash2, Check, User as UserIcon } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import { notify } from '@/lib/notify'
import {
  formatPasswordExpiry,
  isPasswordExpired,
  isTesterUser,
} from '@/lib/password-expiry'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const TIPOS_ACEITOS = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
const TAMANHO_MAX_BYTES = 2 * 1024 * 1024 // 2MB

function iniciaisDoNome(email: string, nome?: string | null): string {
  if (nome?.trim()) {
    return nome
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase())
      .join('')
  }
  const local = email.split('@')[0] ?? ''
  return (
    local
      .split(/[._-]/)
      .map((p) => p[0]?.toUpperCase())
      .join('')
      .slice(0, 2) || '?'
  )
}

export function PerfilPage() {
  const { user } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [nome, setNome] = useState('')
  const [nomeOriginal, setNomeOriginal] = useState('')
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)
  const [savingNome, setSavingNome] = useState(false)
  const [uploading, setUploading] = useState(false)

  // Hidrata estado inicial do user_metadata
  useEffect(() => {
    if (!user) return
    const md = (user.user_metadata ?? {}) as { full_name?: string; avatar_url?: string }
    const n = md.full_name ?? ''
    setNome(n)
    setNomeOriginal(n)
    setAvatarUrl(md.avatar_url ?? null)
  }, [user])

  if (!user) {
    return (
      <div className="py-12 text-center text-muted-foreground flex items-center justify-center gap-2">
        <Loader2 size={16} className="animate-spin" />
        Carregando…
      </div>
    )
  }

  const iniciais = iniciaisDoNome(user.email ?? '', nome)
  const nomeMudou = nome.trim() !== nomeOriginal.trim()

  async function salvarNome() {
    setSavingNome(true)
    const { error } = await supabase.auth.updateUser({
      data: { full_name: nome.trim() },
    })
    setSavingNome(false)
    if (error) {
      notify.error(error.message)
      return
    }
    setNomeOriginal(nome.trim())
    notify.success('Nome atualizado.')
  }

  async function handleArquivoSelecionado(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = '' // permite re-selecionar mesmo arquivo
    if (!file || !user) return

    if (!TIPOS_ACEITOS.includes(file.type)) {
      notify.error(`Tipo de arquivo não suportado (${file.type}). Use JPG, PNG, WebP ou GIF.`)
      return
    }
    if (file.size > TAMANHO_MAX_BYTES) {
      notify.error(`Arquivo muito grande (${(file.size / 1024 / 1024).toFixed(1)} MB). Máximo 2 MB.`)
      return
    }

    setUploading(true)
    try {
      const ext = file.name.split('.').pop()?.toLowerCase() || 'jpg'
      const path = `${user.id}/avatar.${ext}`

      // Remove avatar antigo se for de extensão diferente (evita ficar 2 arquivos).
      const { data: existentes } = await supabase.storage.from('avatars').list(user.id)
      const antigos = (existentes ?? [])
        .map((o) => `${user.id}/${o.name}`)
        .filter((p) => p !== path)
      if (antigos.length > 0) {
        await supabase.storage.from('avatars').remove(antigos)
      }

      const { error: upErr } = await supabase.storage
        .from('avatars')
        .upload(path, file, { upsert: true, contentType: file.type })
      if (upErr) throw upErr

      // URL pública + cache-bust (timestamp) pra forçar recarga
      const { data } = supabase.storage.from('avatars').getPublicUrl(path)
      const finalUrl = `${data.publicUrl}?t=${Date.now()}`

      const { error: metaErr } = await supabase.auth.updateUser({
        data: { avatar_url: finalUrl },
      })
      if (metaErr) throw metaErr

      setAvatarUrl(finalUrl)
      notify.success('Foto de perfil atualizada.')
    } catch (err) {
      notify.error(err)
    } finally {
      setUploading(false)
    }
  }

  async function removerAvatar() {
    if (!user) return
    setUploading(true)
    try {
      const { data: existentes } = await supabase.storage.from('avatars').list(user.id)
      const paths = (existentes ?? []).map((o) => `${user.id}/${o.name}`)
      if (paths.length > 0) {
        await supabase.storage.from('avatars').remove(paths)
      }
      const { error } = await supabase.auth.updateUser({ data: { avatar_url: null } })
      if (error) throw error
      setAvatarUrl(null)
      notify.success('Foto removida.')
    } catch (err) {
      notify.error(err)
    } finally {
      setUploading(false)
    }
  }

  const senhaExpiraEm = user ? formatPasswordExpiry(user) : null
  const senhaExpirada = user ? isPasswordExpired(user) : false
  const contaTeste = user ? isTesterUser(user) : false

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <UserIcon size={22} />
          Editar perfil
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Esses dados aparecem no avatar do topo e em relatórios compartilhados.
        </p>
      </header>

      {contaTeste && senhaExpiraEm && (
        <Alert variant={senhaExpirada ? 'destructive' : 'warning'}>
          <AlertDescription>
            {senhaExpirada
              ? `Senha de teste expirada em ${senhaExpiraEm}. Use código no email ou peça nova senha ao admin.`
              : `Conta de teste — senha válida até ${senhaExpiraEm}.`}
          </AlertDescription>
        </Alert>
      )}

      <section className="rounded-lg border border-border bg-card p-6 space-y-6">
        {/* Avatar + upload */}
        <div className="flex items-center gap-5">
          <Avatar className="h-20 w-20">
            {avatarUrl && <AvatarImage src={avatarUrl} alt="Avatar" />}
            <AvatarFallback className="bg-primary/10 text-primary text-xl">
              {iniciais}
            </AvatarFallback>
          </Avatar>

          <div className="space-y-2">
            <input
              ref={fileInputRef}
              type="file"
              accept={TIPOS_ACEITOS.join(',')}
              onChange={handleArquivoSelecionado}
              className="hidden"
            />
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Enviando…
                  </>
                ) : (
                  <>
                    <Upload size={14} />
                    {avatarUrl ? 'Trocar foto' : 'Enviar foto'}
                  </>
                )}
              </Button>
              {avatarUrl && (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={uploading}
                  onClick={removerAvatar}
                >
                  <Trash2 size={14} />
                  Remover
                </Button>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground font-mono">
              JPG, PNG, WebP ou GIF · até 2 MB
            </p>
          </div>
        </div>

        <div className="border-t border-border pt-6 space-y-4">
          {/* Email (readonly) */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider font-mono">
              Email
            </label>
            <Input
              value={user.email ?? ''}
              readOnly
              disabled
              className="bg-muted/30 font-mono"
            />
            <p className="text-[10px] text-muted-foreground">
              Pra trocar email, contate o administrador.
            </p>
          </div>

          {/* Nome */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider font-mono">
              Nome de exibição
            </label>
            <div className="flex gap-2">
              <Input
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Como você prefere ser chamado"
                maxLength={80}
                disabled={savingNome}
              />
              <Button
                onClick={salvarNome}
                disabled={!nomeMudou || savingNome || !nome.trim()}
              >
                {savingNome ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Check size={14} />
                )}
                Salvar
              </Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
