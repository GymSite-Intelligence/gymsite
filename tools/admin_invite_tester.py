"""
admin_invite_tester.py — convida um tester externo no GymSite.

Uso:
    python tools/admin_invite_tester.py \\
        --email tester@gmail.com \\
        --senha "temp123!" \\
        --nome "Nome do Tester"

O que faz (1 transação atômica via service_role):
  1. Cria user em auth.users com app_metadata.origem='gymsite' (bypassa o
     trigger enforce_company_domain do CFN/Vectra).
  2. Pré-confirma o email (sem precisar de confirmação por email).
  3. Salva nome em user_metadata.full_name (aparece no avatar do GymSite).
  4. Insere membership na org Vectra (00000000-0000-0000-0000-000000000001)
     como 'member' — pode ver relatórios mas não acessa /custos (gated owner/admin).

Após executar, envie pro tester:
    URL:     http://localhost:5174  (ou seu domínio de prod)
    Email:   <email>
    Senha:   <senha>

O tester entra direto na aba "Senha" do /login.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _client():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        sys.exit("✗ SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórias no .env")
    return create_client(url, key)


def convidar(
    email: str,
    senha: str,
    nome: str,
    org_id: str = "00000000-0000-0000-0000-000000000001",
    role: str = "member",
) -> dict[str, Any]:
    sb = _client()

    # 1. Cria user via admin API
    print(f"> Criando user {email}…")
    try:
        res = sb.auth.admin.create_user({
            "email": email,
            "password": senha,
            "email_confirm": True,  # já confirma — sem fluxo de email
            "user_metadata": {"full_name": nome},
            # CRÍTICO: app_metadata.origem='gymsite' bypassa o trigger
            # enforce_company_domain que baniria emails não-vectracargo.com.br.
            "app_metadata": {"origem": "gymsite"},
        })
    except Exception as e:
        msg = str(e)
        if "already been registered" in msg.lower() or "already exists" in msg.lower():
            sys.exit(f"✗ Email {email} já existe. Use outro ou delete antes.")
        sys.exit(f"✗ Falha ao criar user: {e}")

    user = res.user
    if not user:
        sys.exit("✗ create_user retornou sem user — erro silencioso")
    print(f"  ✓ user.id = {user.id}")

    # 2. Insere membership na org
    print(f"> Adicionando membership na org {org_id} (role={role})…")
    sb.table("organization_members").insert({
        "org_id": org_id,
        "user_id": user.id,
        "role": role,
    }).execute()
    print(f"  ✓ membership criada")

    return {
        "user_id": user.id,
        "email": email,
        "nome": nome,
        "senha": senha,
        "org_id": org_id,
        "role": role,
    }


def main():
    ap = argparse.ArgumentParser(description="Convida tester externo no GymSite Intelligence")
    ap.add_argument("--email", required=True, help="Email do tester")
    ap.add_argument("--senha", required=True, help="Senha temporária (sugestão: gerar via password manager)")
    ap.add_argument("--nome", default="", help="Nome de exibição (vai no avatar)")
    ap.add_argument(
        "--org",
        default="00000000-0000-0000-0000-000000000001",
        help="org_id (default: Vectra Cargo)",
    )
    ap.add_argument(
        "--role",
        default="member",
        choices=["member", "admin", "owner"],
        help="Role na org (default: member)",
    )
    args = ap.parse_args()

    resultado = convidar(
        email=args.email,
        senha=args.senha,
        nome=args.nome or args.email.split("@")[0],
        org_id=args.org,
        role=args.role,
    )

    print()
    print("=" * 60)
    print("✓ Tester convidado com sucesso. Envie esses dados:")
    print("=" * 60)
    print(f"  URL    : http://localhost:5174")
    print(f"  Email  : {resultado['email']}")
    print(f"  Senha  : {resultado['senha']}")
    print(f"  Nome   : {resultado['nome']}")
    print(f"  Role   : {resultado['role']}")
    print()
    print("Tester entra no /login → aba 'Senha' → email + senha.")


if __name__ == "__main__":
    main()
