import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export interface Parceiro {
  id: string;
  nome: string;
  descricao?: string;
  logo_url?: string;
  site_url?: string;
  telefone?: string;
  email?: string;
  categorias: string[];
  ufs_atuacao: string[];
  cidades_atuacao: string[];
  tipo_parceria: string;
  lead_valor?: number;
  lead_maximo_mes?: number;
  comissao_percentual?: number;
  valor_mensalidade?: number;
  desconto_oferecido?: string;
  desconto_codigo?: string;
  diferenciais: string[];
  status: string;
  curadoria_nota?: number;
  curadoria_observacao?: string;
  leads_gerados: number;
  leads_convertidos: number;
  rating_medio: number;
  created_at: string;
}

export interface ParceiroFilters {
  status?: string;
  categoria?: string;
  uf?: string;
  tipo_parceria?: string;
  busca?: string;
}

export interface ParceiroListResponse {
  items: Parceiro[];
  total: number;
  limit: number;
  offset: number;
}

async function fetchParceiros(
  filters: ParceiroFilters & { limit: number; offset: number }
): Promise<ParceiroListResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.categoria) params.set("categoria", filters.categoria);
  if (filters.uf) params.set("uf", filters.uf);
  if (filters.tipo_parceria) params.set("tipo_parceria", filters.tipo_parceria);
  if (filters.busca) params.set("busca", filters.busca);
  params.set("limit", String(filters.limit));
  params.set("offset", String(filters.offset));

  const res = await fetch(`${API_URL}/admin/parceiros?${params}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
  });
  if (!res.ok) throw new Error("Erro ao carregar parceiros");
  return res.json();
}

async function createParceiro(data: Partial<Parceiro>): Promise<Parceiro> {
  const res = await fetch(`${API_URL}/admin/parceiros`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("token")}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Erro ao criar parceiro");
  return res.json();
}

async function updateParceiro(id: string, data: Partial<Parceiro>): Promise<Parceiro> {
  const res = await fetch(`${API_URL}/admin/parceiros/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("token")}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Erro ao atualizar parceiro");
  return res.json();
}

async function deleteParceiro(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/admin/parceiros/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
  });
  if (!res.ok) throw new Error("Erro ao excluir parceiro");
}

async function aprovarParceiro(
  id: string,
  nota: number,
  observacao?: string
): Promise<Parceiro> {
  const params = new URLSearchParams();
  params.set("nota", String(nota));
  if (observacao) params.set("observacao", observacao);

  const res = await fetch(`${API_URL}/admin/parceiros/${id}/curadoria?${params}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
  });
  if (!res.ok) throw new Error("Erro ao aprovar parceiro");
  return res.json();
}

export function useParceiros(
  filters: ParceiroFilters & { limit: number; offset: number }
) {
  return useQuery({
    queryKey: ["parceiros", filters],
    queryFn: () => fetchParceiros(filters),
  });
}

export function useCreateParceiro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createParceiro,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parceiros"] }),
  });
}

export function useUpdateParceiro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Parceiro> }) =>
      updateParceiro(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parceiros"] }),
  });
}

export function useDeleteParceiro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteParceiro,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parceiros"] }),
  });
}

export function useAprovarParceiro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nota, observacao }: { id: string; nota: number; observacao?: string }) =>
      aprovarParceiro(id, nota, observacao),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parceiros"] }),
  });
}
