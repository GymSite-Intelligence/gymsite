// Supabase Edge Function: recebe webhook do GymSite e insere em prospect_profiles
// Deploy: supabase functions deploy gymsite-sync

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const WEBHOOK_SECRET = Deno.env.get("GYMSITE_WEBHOOK_SECRET")!;
const DEFAULT_COMPANY_ID = Deno.env.get("DEFAULT_COMPANY_ID") || "00000000-0000-0000-0000-000000000001";

serve(async (req) => {
  // Validar método
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405 });
  }

  // Validar secret
  const secret = req.headers.get("x-claw-secret") || "";
  if (WEBHOOK_SECRET && secret !== WEBHOOK_SECRET) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401 });
  }

  let payload;
  try {
    payload = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), { status: 400 });
  }

  const data = payload.data || payload;
  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

  // Mapear payload GymSite → prospect_profiles
  const prospect = {
    company_id: DEFAULT_COMPANY_ID,
    nome_razao_social: data.razao_social || data.nome_fantasia || "",
    cnpj: data.cnpj,
    setor: data.segmento || data.segmento_operacao || "",
    cidade: data.cidade || "",
    uf: data.uf || "",
    endereco: data.endereco || null,
    telefone: data.contato?.telefone || "",
    email_contato: data.contato?.email || "",
    decisores: data.contato?.decision_maker
      ? [{ nome: data.contato.decision_maker, cargo: data.contato.cargo || "", email: data.contato.email || "", whatsapp: data.contato.whatsapp || "", linkedin: data.contato.linkedin || "" }]
      : [],
    dados_publicos: {
      nome_obra: data.obra?.nome || data.nome_obra || "",
      situacao_obra: data.obra?.situacao || data.situacao_obra || "",
      area_total_m2: data.obra?.area_m2 || data.area_total_m2 || null,
      cno: data.cno || "",
      segmento_operacao: data.segmento || data.segmento_operacao || "",
      score_match: data.score_match || 0,
      motivo_match: data.motivo_match || "",
      prioridade: data.prioridade || "media",
      origem: "gymsite_webhook",
    },
    status: "COLD",
    temperatura: "frio",
    score: data.score_match || 0,
    origem: "gymsite_webhook",
  };

  // Evitar duplicata por CNPJ
  const { data: existing } = await supabase
    .from("prospect_profiles")
    .select("id")
    .eq("cnpj", data.cnpj)
    .limit(1);

  if (existing && existing.length > 0) {
    return new Response(JSON.stringify({ ok: true, message: "Prospect already exists", id: existing[0].id }), { status: 200 });
  }

  const { data: inserted, error } = await supabase
    .from("prospect_profiles")
    .insert(prospect)
    .select()
    .single();

  if (error) {
    console.error("Insert error:", error);
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }

  return new Response(JSON.stringify({ ok: true, id: inserted.id }), { status: 201 });
});
