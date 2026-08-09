# Runbook canônico — API 503 e falhas de `gcloud`

> **Escopo:** o que fazer quando a API de produção (`gymsite-api`) retorna **503 Service Unavailable** ou quando o comando `gcloud` falha na sua máquina. Documenta o incidente de **2026-08-05** (faturamento GCP desativado) para não perdermos tempo diagnosticando de novo.
>
> **Canônico junto de:** [`.agent/skills/gymsite-devops/SKILL.md`](../.agent/skills/gymsite-devops/SKILL.md) · [`docs/CONVERGENCE_DEPLOY.md`](CONVERGENCE_DEPLOY.md).
> **Substituição do hospedeiro (sair do Cloud Run):** [PLAN_HETZNER_VPS_TUNNEL.md](PLAN_HETZNER_VPS_TUNNEL.md).

---

## TL;DR — o 503 quase nunca é bug de código

Quando `https://gymsite-api.vectracargo.com.br/health` responde **503** e o Cloud Run diz que o serviço está `Ready`, a causa mais provável **não é deploy quebrado**: é o **Google barrando o projeto por faturamento desativado**. O serviço fica de pé, mas nenhuma requisição chega até ele.

Frase que engana: `The service you requested is not available yet. Please try again in 30 seconds.` — parece problema temporário; na prática o projeto está suspenso.

**Correção:** reativar a conta de faturamento no [Console de Billing](https://console.cloud.google.com/billing). A API volta sozinha, **sem redeploy**.

---

## Fatos fixos (decorar / colar)

| Item | Valor |
|---|---|
| Projeto GCP (produção) | `gen-lang-client-0106729343` |
| Região | `us-central1` (**não** southamerica-east1) |
| Serviço API | `gymsite-api` |
| Serviço worker | `gymsite-worker` (mesma imagem da API) |
| URL direta Cloud Run | `https://gymsite-api-zlbaasuc6a-uc.a.run.app` |
| Conta billing do incidente | `01CDFB-0F0E83-D2ECDB` |
| **Projeto órfão (NÃO usar)** | `gen-lang-client-0662901510` |
| `gcloud` no Windows | `C:\Users\marce\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd` |
| venv do projeto | `C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe` |

> ⚠️ **`gcloud` não está no PATH.** Chamar `gcloud ...` direto no PowerShell dá `termo não reconhecido`. Use sempre o caminho completo acima (ou `& "...\gcloud.cmd"`).

---

## Diagnóstico rápido (3 comandos, nesta ordem)

Cole o caminho do gcloud numa variável para encurtar:

```powershell
$g = "C:\Users\marce\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
```

**1. O serviço está de pé?** (se `Ready True`, o problema NÃO é o container)

```powershell
& $g run services describe gymsite-api --region=us-central1 --project=gen-lang-client-0106729343 `
  --format="value(status.url,status.latestReadyRevisionName,status.conditions[0].type,status.conditions[0].status)"
```

**2. As requisições estão chegando?** (só linhas `Starting new instance` e nenhum request = tráfego barrado antes do container)

```powershell
& $g logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="gymsite-api"' `
  --project=gen-lang-client-0106729343 --limit=5 --freshness=1h `
  --format="value(timestamp,severity,httpRequest.status,textPayload)"
```

**3. O faturamento está ligado?** (a causa-raiz do incidente)

```powershell
& $g beta billing projects describe gen-lang-client-0106729343
```

Interpretação:

- `billingEnabled: false` → **é isto.** Projeto suspenso. Vá para *Recuperação*.
- `billingEnabled: true` + serviço `Ready` + zero requests nos logs → checar roteamento/domínio (Cloudflare → Cloud Run), não billing.
- Serviço **não** `Ready` / logs com `severity>=ERROR` → aí sim é deploy/código; siga o `/deploy` normal.

Conferir também se **alguma** conta de billing está aberta:

```powershell
& $g beta billing accounts list   # coluna OPEN precisa ter ao menos uma True
```

---

## Recuperação (faturamento desativado)

1. Abrir o [Console de Faturamento](https://console.cloud.google.com/billing).
2. Verificar a conta `01CDFB-0F0E83-D2ECDB` (ou a vinculada ao projeto): causa comum = **cartão vencido/recusado** ou débito em aberto.
3. Atualizar o meio de pagamento / quitar o pendente → a conta volta a `open: true`.
4. Confirmar o vínculo projeto ↔ billing:
   ```powershell
   & $g beta billing projects link gen-lang-client-0106729343 --billing-account=01CDFB-0F0E83-D2ECDB
   ```
5. Aguardar alguns minutos e revalidar:
   ```powershell
   Invoke-RestMethod https://gymsite-api.vectracargo.com.br/health
   ```

**Não precisa redeploy.** Com `minScale=1`, o Cloud Run re-provisiona a instância assim que o faturamento volta.

---

## Plano B — enquanto a produção não volta

A **API local** lê o **mesmo Supabase** de produção. Serve para conferir dados e gerar PDF de relatórios já prontos.

Subir a API local (a partir da **raiz** `C:\Users\marce\gymsite`, nunca de `backend/`):

```powershell
& "C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Health local:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

> **PDF local:** o endpoint `/pdf` exige autenticação (JWT ou `access_code`). Sem credencial dá 401. Para conferência offline, gerar o PDF chamando `pdf.adapters.relatorio_from_api_payload` + `generate_relatorio_pdf` direto pelo venv. **Atenção:** no Windows o WeasyPrint cai para ReportLab (faltam pango/cairo), então o visual **não** é o final de produção — serve só para ler o conteúdo.

---

## Prevenção (para não repetir)

- **Alerta de orçamento (budget) no billing** com notificação por e-mail em 50/90/100% — pega cartão recusado antes do corte.
- **Manter o meio de pagamento válido** na conta `01CDFB-0F0E83-D2ECDB`; cartão vencido é o gatilho nº 1.
- **Monitor externo de uptime** batendo em `/health` (ex.: UptimeRobot) — avisa o 503 antes do usuário.
- Não migrar produção para o **projeto órfão** `gen-lang-client-0662901510`.

---

## Terminologia — não é "deprecação"

O incidente foi **desativação de faturamento** (billing suspenso), não *deprecation* de serviço/API do Google. "Deprecação" seria o Google encerrar um produto/versão de API com aviso prévio. Aqui o serviço continua existindo e saudável; só o pagamento parou. Tratar como problema de **conta**, não de **arquitetura**.
