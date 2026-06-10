import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import type { Parceiro } from "@/hooks/useParceirosAdmin";

const CATEGORIAS = [
  "IMOBILIARIO",
  "LEGAL",
  "OBRAS",
  "EQUIPAMENTOS",
  "TECNOLOGIA",
  "RH",
  "MARKETING",
  "FINANCEIRO",
  "OPERACIONAL",
  "OUTRO",
];

const TIPOS_PARCERIA = [
  { value: "LEAD_GENERATION", label: "Geração de Lead" },
  { value: "AFILIADO", label: "Afiliado (Comissão)" },
  { value: "SPONSORED", label: "Patrocinado (Mensalidade)" },
  { value: "WHITE_LABEL", label: "White Label" },
];

interface ParceiroFormProps {
  initialData?: Partial<Parceiro>;
  onSubmit: (data: Partial<Parceiro>) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function ParceiroForm({ initialData, onSubmit, onCancel, isLoading }: ParceiroFormProps) {
  const [form, setForm] = useState<Partial<Parceiro>>({
    nome: "",
    descricao: "",
    logo_url: "",
    site_url: "",
    telefone: "",
    email: "",
    categorias: [],
    ufs_atuacao: [],
    cidades_atuacao: [],
    tipo_parceria: "LEAD_GENERATION",
    lead_valor: undefined,
    lead_maximo_mes: undefined,
    comissao_percentual: undefined,
    valor_mensalidade: undefined,
    desconto_oferecido: "",
    desconto_codigo: "",
    diferenciais: [],
    ...initialData,
  });

  const [novoDiferencial, setNovoDiferencial] = useState("");
  const [novaUf, setNovaUf] = useState("");

  const toggleCategoria = (cat: string) => {
    const cats = form.categorias || [];
    if (cats.includes(cat)) {
      setForm({ ...form, categorias: cats.filter((c) => c !== cat) });
    } else {
      setForm({ ...form, categorias: [...cats, cat] });
    }
  };

  const addDiferencial = () => {
    if (!novoDiferencial.trim()) return;
    setForm({
      ...form,
      diferenciais: [...(form.diferenciais || []), novoDiferencial.trim()],
    });
    setNovoDiferencial("");
  };

  const removeDiferencial = (idx: number) => {
    setForm({
      ...form,
      diferenciais: (form.diferenciais || []).filter((_, i) => i !== idx),
    });
  };

  const addUf = () => {
    if (!novaUf.trim()) return;
    setForm({
      ...form,
      ufs_atuacao: [...(form.ufs_atuacao || []), novaUf.trim().toUpperCase()],
    });
    setNovaUf("");
  };

  const removeUf = (uf: string) => {
    setForm({
      ...form,
      ufs_atuacao: (form.ufs_atuacao || []).filter((u) => u !== uf),
    });
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(form);
      }}
      className="space-y-6"
    >
      {/* Dados Básicos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="nome">Nome do Parceiro *</Label>
          <Input
            id="nome"
            value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
            placeholder="Ex: Unicold"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={form.email || ""}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="contato@unicold.com.br"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="telefone">Telefone</Label>
          <Input
            id="telefone"
            value={form.telefone || ""}
            onChange={(e) => setForm({ ...form, telefone: e.target.value })}
            placeholder="(11) 99999-9999"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="site_url">Site</Label>
          <Input
            id="site_url"
            value={form.site_url || ""}
            onChange={(e) => setForm({ ...form, site_url: e.target.value })}
            placeholder="https://unicold.com.br"
          />
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="logo_url">URL do Logo</Label>
          <Input
            id="logo_url"
            value={form.logo_url || ""}
            onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
            placeholder="https://..."
          />
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="descricao">Descrição</Label>
          <Textarea
            id="descricao"
            value={form.descricao || ""}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setForm({ ...form, descricao: e.target.value })}
            placeholder="Descrição do parceiro e serviços oferecidos..."
            rows={3}
          />
        </div>
      </div>

      {/* Categorias */}
      <div className="space-y-2">
        <Label>Categorias Atendidas *</Label>
        <div className="flex flex-wrap gap-2">
          {CATEGORIAS.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => toggleCategoria(cat)}
              className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                (form.categorias || []).includes(cat)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background border-border hover:border-primary"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* UF de Atuação */}
      <div className="space-y-2">
        <Label>UFs de Atuação</Label>
        <div className="flex gap-2">
          <Input
            value={novaUf}
            onChange={(e) => setNovaUf(e.target.value)}
            placeholder="Ex: SP"
            className="w-24"
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addUf())}
          />
          <Button type="button" variant="outline" onClick={addUf}>
            Adicionar
          </Button>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {(form.ufs_atuacao || []).map((uf) => (
            <Badge key={uf} variant="secondary" className="gap-1">
              {uf}
              <X className="w-3 h-3 cursor-pointer" onClick={() => removeUf(uf)} />
            </Badge>
          ))}
        </div>
      </div>

      {/* Tipo de Parceria */}
      <div className="space-y-2">
        <Label htmlFor="tipo_parceria">Tipo de Parceria *</Label>
        <Select
          value={form.tipo_parceria}
          onValueChange={(v) => setForm({ ...form, tipo_parceria: v })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIPOS_PARCERIA.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Campos condicionais por tipo */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {form.tipo_parceria === "LEAD_GENERATION" && (
          <>
            <div className="space-y-2">
              <Label htmlFor="lead_valor">Valor por Lead (R$)</Label>
              <Input
                id="lead_valor"
                type="number"
                step="0.01"
                value={form.lead_valor || ""}
                onChange={(e) =>
                  setForm({ ...form, lead_valor: parseFloat(e.target.value) || undefined })
                }
                placeholder="150.00"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lead_maximo_mes">Máx. Leads/Mês</Label>
              <Input
                id="lead_maximo_mes"
                type="number"
                value={form.lead_maximo_mes || ""}
                onChange={(e) =>
                  setForm({ ...form, lead_maximo_mes: parseInt(e.target.value) || undefined })
                }
                placeholder="50"
              />
            </div>
          </>
        )}

        {form.tipo_parceria === "AFILIADO" && (
          <div className="space-y-2">
            <Label htmlFor="comissao_percentual">Comissão (%)</Label>
            <Input
              id="comissao_percentual"
              type="number"
              step="0.01"
              max={100}
              value={form.comissao_percentual || ""}
              onChange={(e) =>
                setForm({ ...form, comissao_percentual: parseFloat(e.target.value) || undefined })
              }
              placeholder="5.00"
            />
          </div>
        )}

        {form.tipo_parceria === "SPONSORED" && (
          <div className="space-y-2">
            <Label htmlFor="valor_mensalidade">Mensalidade (R$)</Label>
            <Input
              id="valor_mensalidade"
              type="number"
              step="0.01"
              value={form.valor_mensalidade || ""}
              onChange={(e) =>
                setForm({ ...form, valor_mensalidade: parseFloat(e.target.value) || undefined })
              }
              placeholder="1500.00"
            />
          </div>
        )}
      </div>

      {/* Desconto */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="desconto_oferecido">Desconto Oferecido (texto)</Label>
          <Input
            id="desconto_oferecido"
            value={form.desconto_oferecido || ""}
            onChange={(e) => setForm({ ...form, desconto_oferecido: e.target.value })}
            placeholder="Ex: 12% para projetos GymSite"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="desconto_codigo">Código de Desconto</Label>
          <Input
            id="desconto_codigo"
            value={form.desconto_codigo || ""}
            onChange={(e) => setForm({ ...form, desconto_codigo: e.target.value })}
            placeholder="GYMSITE12"
          />
        </div>
      </div>

      {/* Diferenciais */}
      <div className="space-y-2">
        <Label>Diferenciais</Label>
        <div className="flex gap-2">
          <Input
            value={novoDiferencial}
            onChange={(e) => setNovoDiferencial(e.target.value)}
            placeholder="Ex: Instalação inclusa"
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addDiferencial())}
          />
          <Button type="button" variant="outline" onClick={addDiferencial}>
            Adicionar
          </Button>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {(form.diferenciais || []).map((diff, idx) => (
            <Badge key={idx} variant="outline" className="gap-1">
              {diff}
              <X className="w-3 h-3 cursor-pointer" onClick={() => removeDiferencial(idx)} />
            </Badge>
          ))}
        </div>
      </div>

      {/* Ações */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={isLoading || !form.nome || !(form.categorias?.length)}>
          {isLoading ? "Salvando..." : initialData?.id ? "Atualizar" : "Criar Parceiro"}
        </Button>
      </div>
    </form>
  );
}
