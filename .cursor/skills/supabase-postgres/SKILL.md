---
name: supabase-postgres
description: Regras para escrita de Queries SQL, Migrations e interações com o Supabase SDK. Use ao mexer em tabelas de relatórios, dados de CNPJ ou regras de RLS.
---

# ⚡ Supabase & Postgres Standards

## 🏢 Regra de Ouro: Multi-Tenant & Segurança
* **RLS (Row Level Security):** Sempre ativo para tabelas do usuário final. Toda tabela de dados operacionais deve possuir a coluna `org_id`.
* **Dinheiro:** **Sempre** salve valores financeiros como inteiros em centavos (`integer`), nunca use floats.
* **Datas:** Sempre utilize o tipo `timestamptz` (UTC).
* **Busca Semântica:** Consultas de RAG para o Discovery Engine devem usar a extensão `vector` (pgvector).