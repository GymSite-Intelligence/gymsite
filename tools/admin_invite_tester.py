"""
admin_invite_tester.py — convites e senhas temporárias para testers GymSite.

Fluxo recomendado:
  1. Admin convida só com OTP (primeiro acesso por código no email):
       python tools/admin_invite_tester.py invite-otp \\
           --email tester@gmail.com --nome "Nome Tester"

  2. Tester entra em /login → aba "Código no email" → recebe OTP → primeiro acesso.

  3. Após o primeiro login, admin define senha com validade:
       python tools/admin_invite_tester.py set-password \\
           --email tester@gmail.com --senha "Temp2026!" --valido-dias 14

  4. Tester passa a usar aba "Senha" até a data de expiração.

Atalho (senha desde o início, sem OTP primeiro):
       python tools/admin_invite_tester.py invite-password \\
           --email tester@gmail.com --senha "Temp2026!" --valido-dias 30 --nome "Nome"
"""
from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

ORG_VECTRA = "00000000-0000-0000-0000-000000000001"


def _client():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        sys.exit("✗ SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórias no .env")
    return create_client(url, key)


def _gerar_senha(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
        ):
            return pwd


def _buscar_user_por_email(sb, email: str):
    normalized = email.strip().lower()
    page = 1
    per_page = 200
    while True:
        res = sb.auth.admin.list_users(page=page, per_page=per_page)
        users = res if isinstance(res, list) else getattr(res, "users", None) or []
        for user in users:
            if (getattr(user, "email", "") or "").lower() == normalized:
                return user
        if len(users) < per_page:
            break
        page += 1
    return None


def _membership_existe(sb, user_id: str, org_id: str) -> bool:
    res = (
        sb.table("organization_members")
        .select("user_id")
        .eq("user_id", user_id)
        .eq("org_id", org_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def _garantir_membership(sb, user_id: str, org_id: str, role: str) -> None:
    if _membership_existe(sb, user_id, org_id):
        print(f"  · membership já existe na org {org_id}")
        return
    sb.table("organization_members").insert(
        {"org_id": org_id, "user_id": user_id, "role": role}
    ).execute()
    print(f"  ✓ membership criada (role={role})")


def _metadata_base(nome: str, *, tester: bool = True) -> dict[str, Any]:
    meta: dict[str, Any] = {"full_name": nome, "tester": tester}
    return meta


def convidar_otp(
    email: str,
    nome: str,
    org_id: str = ORG_VECTRA,
    role: str = "member",
) -> dict[str, Any]:
    """Cria user sem senha — primeiro acesso só via código OTP no email."""
    sb = _client()
    email = email.strip().lower()
    print(f"> Convidando {email} (modo OTP — sem senha)…")

    existente = _buscar_user_por_email(sb, email)
    if existente:
        sys.exit(
            f"✗ Email {email} já existe (id={existente.id}). "
            "Use set-password se já fez o primeiro login."
        )

    res = sb.auth.admin.create_user(
        {
            "email": email,
            "email_confirm": True,
            "user_metadata": {
                **_metadata_base(nome),
                "auth_mode": "otp_first",
            },
            "app_metadata": {"origem": "gymsite"},
        }
    )
    user = res.user
    if not user:
        sys.exit("✗ create_user retornou sem user")

    print(f"  ✓ user.id = {user.id}")
    _garantir_membership(sb, user.id, org_id, role)

    return {
        "user_id": user.id,
        "email": email,
        "nome": nome,
        "modo": "otp_first",
        "org_id": org_id,
        "role": role,
    }


def definir_senha(
    email: str,
    senha: str,
    valido_dias: int,
    *,
    exigir_primeiro_login: bool = True,
) -> dict[str, Any]:
    """Define senha temporária após primeiro acesso OTP."""
    sb = _client()
    email = email.strip().lower()
    print(f"> Definindo senha temporária para {email} ({valido_dias} dias)…")

    user = _buscar_user_por_email(sb, email)
    if not user:
        sys.exit(f"✗ User {email} não encontrado. Rode invite-otp antes.")

    last_sign_in = getattr(user, "last_sign_in_at", None)
    if exigir_primeiro_login and not last_sign_in:
        sys.exit(
            "✗ Tester ainda não fez o primeiro login via código no email.\n"
            "  Peça para entrar em /login → aba 'Código no email' e tente de novo."
        )

    expires = datetime.now(timezone.utc) + timedelta(days=valido_dias)
    meta = dict(getattr(user, "user_metadata", None) or {})
    meta.update(
        {
            "tester": True,
            "auth_mode": "password_temp",
            "password_expires_at": expires.isoformat(),
            "password_set_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if not meta.get("full_name"):
        meta["full_name"] = email.split("@")[0]

    sb.auth.admin.update_user_by_id(
        user.id,
        {"password": senha, "user_metadata": meta},
    )

    print(f"  ✓ senha definida — válida até {expires.astimezone().strftime('%d/%m/%Y %H:%M %Z')}")

    return {
        "user_id": user.id,
        "email": email,
        "senha": senha,
        "password_expires_at": expires.isoformat(),
        "valido_dias": valido_dias,
        "primeiro_login_em": last_sign_in,
    }


def convidar_com_senha(
    email: str,
    senha: str,
    nome: str,
    valido_dias: int,
    org_id: str = ORG_VECTRA,
    role: str = "member",
) -> dict[str, Any]:
    """Atalho: cria user já com senha temporária (pula OTP)."""
    sb = _client()
    email = email.strip().lower()
    print(f"> Convidando {email} com senha temporária ({valido_dias} dias)…")

    existente = _buscar_user_por_email(sb, email)
    if existente:
        sys.exit(f"✗ Email {email} já existe. Use set-password.")

    expires = datetime.now(timezone.utc) + timedelta(days=valido_dias)
    res = sb.auth.admin.create_user(
        {
            "email": email,
            "password": senha,
            "email_confirm": True,
            "user_metadata": {
                **_metadata_base(nome),
                "auth_mode": "password_temp",
                "password_expires_at": expires.isoformat(),
                "password_set_at": datetime.now(timezone.utc).isoformat(),
            },
            "app_metadata": {"origem": "gymsite"},
        }
    )
    user = res.user
    if not user:
        sys.exit("✗ create_user retornou sem user")

    print(f"  ✓ user.id = {user.id}")
    _garantir_membership(sb, user.id, org_id, role)

    return {
        "user_id": user.id,
        "email": email,
        "nome": nome,
        "senha": senha,
        "password_expires_at": expires.isoformat(),
        "valido_dias": valido_dias,
        "org_id": org_id,
        "role": role,
    }


def _print_resultado_otp(r: dict[str, Any]) -> None:
    print()
    print("=" * 60)
    print("✓ Tester convidado (primeiro acesso via código no email)")
    print("=" * 60)
    print(f"  URL   : http://localhost:5174/login")
    print(f"  Email : {r['email']}")
    print(f"  Nome  : {r['nome']}")
    print(f"  Role  : {r['role']}")
    print()
    print("Instruções pro tester:")
    print("  1. /login → aba 'Código no email'")
    print("  2. Após entrar, avise o admin para liberar senha temporária.")


def _print_resultado_senha(r: dict[str, Any], titulo: str) -> None:
    print()
    print("=" * 60)
    print(titulo)
    print("=" * 60)
    print(f"  URL    : http://localhost:5174/login")
    print(f"  Email  : {r['email']}")
    print(f"  Senha  : {r['senha']}")
    if r.get("password_expires_at"):
        exp = datetime.fromisoformat(r["password_expires_at"].replace("Z", "+00:00"))
        print(f"  Válida : até {exp.astimezone().strftime('%d/%m/%Y %H:%M')}")
    print()
    print("Tester entra em /login → aba 'Senha'.")


def main():
    ap = argparse.ArgumentParser(
        description="Convites e senhas temporárias para testers GymSite Intelligence"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_otp = sub.add_parser(
        "invite-otp",
        help="Convida tester — primeiro acesso só via código OTP (sem senha)",
    )
    p_otp.add_argument("--email", required=True)
    p_otp.add_argument("--nome", default="")
    p_otp.add_argument("--org", default=ORG_VECTRA)
    p_otp.add_argument("--role", default="member", choices=["member", "admin", "owner"])

    p_pwd = sub.add_parser(
        "set-password",
        help="Define senha temporária após primeiro login OTP",
    )
    p_pwd.add_argument("--email", required=True)
    p_pwd.add_argument(
        "--senha",
        default="",
        help="Senha (default: gera automaticamente)",
    )
    p_pwd.add_argument(
        "--valido-dias",
        type=int,
        default=14,
        help="Validade da senha em dias (default: 14)",
    )
    p_pwd.add_argument(
        "--sem-exigir-login",
        action="store_true",
        help="Não exige que tester já tenha feito login OTP",
    )

    p_both = sub.add_parser(
        "invite-password",
        help="Atalho: convida já com senha temporária (pula OTP)",
    )
    p_both.add_argument("--email", required=True)
    p_both.add_argument("--senha", default="")
    p_both.add_argument("--nome", default="")
    p_both.add_argument("--valido-dias", type=int, default=30)
    p_both.add_argument("--org", default=ORG_VECTRA)
    p_both.add_argument("--role", default="member", choices=["member", "admin", "owner"])

    args = ap.parse_args()

    if args.cmd == "invite-otp":
        r = convidar_otp(
            email=args.email,
            nome=args.nome or args.email.split("@")[0],
            org_id=args.org,
            role=args.role,
        )
        _print_resultado_otp(r)
        return

    if args.cmd == "set-password":
        senha = args.senha.strip() or _gerar_senha()
        r = definir_senha(
            email=args.email,
            senha=senha,
            valido_dias=args.valido_dias,
            exigir_primeiro_login=not args.sem_exigir_login,
        )
        _print_resultado_senha(r, "✓ Senha temporária definida")
        return

    if args.cmd == "invite-password":
        senha = args.senha.strip() or _gerar_senha()
        r = convidar_com_senha(
            email=args.email,
            senha=senha,
            nome=args.nome or args.email.split("@")[0],
            valido_dias=args.valido_dias,
            org_id=args.org,
            role=args.role,
        )
        _print_resultado_senha(r, "✓ Tester convidado com senha temporária")
        return


if __name__ == "__main__":
    main()
