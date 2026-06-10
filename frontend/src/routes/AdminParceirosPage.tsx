import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useParceiros,
  useCreateParceiro,
  useUpdateParceiro,
  useDeleteParceiro,
  useAprovarParceiro,
  type Parceiro,
  type ParceiroFilters,
} from "@/hooks/useParceirosAdmin";
import { ParceiroForm } from "@/components/admin/ParceiroForm";
import { Plus, Pencil, Trash2, CheckCircle, Star, ExternalLink } from "lucide-react";

const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "PENDENTE", label: "Pendente" },
  { value: "ATIVO", label: "Ativo" },
  { value: "PAUSADO", label: "Pausado" },
  { value: "CANCELADO", label: "Cancelado" },
  { value: "REPROVADO", label: "Reprovado" },
];

const CATEGORIA_OPTIONS = [
  { value: "", label: "Todas" },
  { value: "IMOBILIARIO", label: "Imobiliário" },
  { value: "LEGAL", label: "Legal" },
  { value: "OBRAS", label: "Obras" },
  { value: "EQUIPAMENTOS", label: "Equipamentos" },
  { value: "TECNOLOGIA", label: "Tecnologia" },
  { value: "RH", label: "RH" },
  { value: "MARKETING", label: "Marketing" },
  { value: "FINANCEIRO", label: "Financeiro" },
  { value: "OPERACIONAL", label: "Operacional" },
];

const TIPO_PARCERIA_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "LEAD_GENERATION", label: "Lead Generation" },
  { value: "AFILIADO", label: "Afiliado" },
  { value: "SPONSORED", label: "Sponsored" },
  { value: "WHITE_LABEL", label: "White Label" },
];

export default function AdminParceirosPage() {
  const [filters, setFilters] = useState<ParceiroFilters & { limit: number; offset: number }>({
    limit: 50,
    offset: 0,
  });

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingParceiro, setEditingParceiro] = useState<Parceiro | null>(null);
  const [curadoriaParceiro, setCuradoriaParceiro] = useState<Parceiro | null>(null);
  const [curadoriaNota, setCuradoriaNota] = useState(5);
  const [curadoriaObs, setCuradoriaObs] = useState("");

  const { data, isLoading } = useParceiros(filters);
  const createMutation = useCreateParceiro();
  const updateMutation = useUpdateParceiro();
  const deleteMutation = useDeleteParceiro();
  const aprovarMutation = useAprovarParceiro();

  const handleSubmit = (formData: Partial<Parceiro>) => {
    if (editingParceiro) {
      updateMutation.mutate(
        { id: editingParceiro.id, data: formData },
        { onSuccess: () => setIsModalOpen(false) }
      );
    } else {
      createMutation.mutate(formData, {
        onSuccess: () => setIsModalOpen(false),
      });
    }
  };

  const handleAprovar = () => {
    if (!curadoriaParceiro) return;
    aprovarMutation.mutate(
      { id: curadoriaParceiro.id, nota: curadoriaNota, observacao: curadoriaObs },
      { onSuccess: () => setCuradoriaParceiro(null) }
    );
  };

  const getStatusColor = (status: string) => {
    const map: Record<string, string> = {
      PENDENTE: "bg-yellow-100 text-yellow-800",
      ATIVO: "bg-green-100 text-green-800",
      PAUSADO: "bg-gray-100 text-gray-800",
      CANCELADO: "bg-red-100 text-red-800",
      REPROVADO: "bg-red-100 text-red-800",
    };
    return map[status] || "bg-gray-100";
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Parceiros Fornecedores</h1>
          <p className="text-muted-foreground">
            Curadoria e gestão de fornecedores para o playbook
          </p>
        </div>
        <Button onClick={() => { setEditingParceiro(null); setIsModalOpen(true); }}>
          <Plus className="w-4 h-4 mr-2" />
          Novo Parceiro
        </Button>
      </div>

      {/* Filtros */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <Input
          placeholder="Buscar por nome..."
          value={filters.busca || ""}
          onChange={(e) => setFilters({ ...filters, busca: e.target.value, offset: 0 })}
        />
        <Select
          value={filters.status || ""}
          onValueChange={(v) => setFilters({ ...filters, status: v || undefined, offset: 0 })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.categoria || ""}
          onValueChange={(v) => setFilters({ ...filters, categoria: v || undefined, offset: 0 })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Categoria" />
          </SelectTrigger>
          <SelectContent>
            {CATEGORIA_OPTIONS.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={filters.tipo_parceria || ""}
          onValueChange={(v) => setFilters({ ...filters, tipo_parceria: v || undefined, offset: 0 })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            {TIPO_PARCERIA_OPTIONS.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="UF"
          value={filters.uf || ""}
          onChange={(e) => setFilters({ ...filters, uf: e.target.value.toUpperCase(), offset: 0 })}
          className="uppercase"
        />
      </div>

      {/* Tabela */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Parceiro</TableHead>
              <TableHead>Categorias</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Curadoria</TableHead>
              <TableHead>Leads</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  Carregando...
                </TableCell>
              </TableRow>
            ) : !data?.items.length ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  Nenhum parceiro encontrado
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      {p.logo_url ? (
                        <img
                          src={p.logo_url}
                          alt={p.nome}
                          className="w-10 h-10 rounded object-contain border"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded bg-muted flex items-center justify-center text-sm font-bold">
                          {p.nome.charAt(0)}
                        </div>
                      )}
                      <div>
                        <div className="font-medium">{p.nome}</div>
                        <div className="text-xs text-muted-foreground">
                          {p.email} {p.telefone && `• ${p.telefone}`}
                        </div>
                        {p.site_url && (
                          <a
                            href={p.site_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary flex items-center gap-1 hover:underline"
                          >
                            <ExternalLink className="w-3 h-3" />
                            Site
                          </a>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {p.categorias.slice(0, 3).map((c) => (
                        <Badge key={c} variant="secondary" className="text-xs">
                          {c}
                        </Badge>
                      ))}
                      {p.categorias.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{p.categorias.length - 3}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {TIPO_PARCERIA_OPTIONS.find((t) => t.value === p.tipo_parceria)?.label ||
                        p.tipo_parceria}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(p.status)}>{p.status}</Badge>
                  </TableCell>
                  <TableCell>
                    {p.curadoria_nota ? (
                      <div className="flex items-center gap-1">
                        <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                        <span className="text-sm font-medium">{p.curadoria_nota}/5</span>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">Não avaliado</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      <span className="font-medium">{p.leads_gerados}</span>{" "}
                      <span className="text-muted-foreground">
                        ({p.leads_convertidos} convertidos)
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {p.status === "PENDENTE" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setCuradoriaParceiro(p);
                            setCuradoriaNota(5);
                            setCuradoriaObs("");
                          }}
                          title="Aprovar"
                        >
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setEditingParceiro(p);
                          setIsModalOpen(true);
                        }}
                        title="Editar"
                      >
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          if (confirm(`Excluir "${p.nome}"?`)) {
                            deleteMutation.mutate(p.id);
                          }
                        }}
                        title="Excluir"
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Paginação */}
      {data && data.total > filters.limit && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Mostrando {filters.offset + 1}-{Math.min(filters.offset + filters.limit, data.total)}{" "}
            de {data.total}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={filters.offset === 0}
              onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - filters.limit) })}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              disabled={filters.offset + filters.limit >= data.total}
              onClick={() => setFilters({ ...filters, offset: filters.offset + filters.limit })}
            >
              Próxima
            </Button>
          </div>
        </div>
      )}

      {/* Modal de Cadastro/Edição */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingParceiro ? "Editar Parceiro" : "Novo Parceiro"}
            </DialogTitle>
          </DialogHeader>
          <ParceiroForm
            initialData={editingParceiro || undefined}
            onSubmit={handleSubmit}
            onCancel={() => setIsModalOpen(false)}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      {/* Modal de Curadoria */}
      <Dialog open={!!curadoriaParceiro} onOpenChange={() => setCuradoriaParceiro(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Aprovar Parceiro</DialogTitle>
          </DialogHeader>
          {curadoriaParceiro && (
            <div className="space-y-4">
              <div className="text-sm">
                <span className="font-medium">{curadoriaParceiro.nome}</span>
                <p className="text-muted-foreground mt-1">{curadoriaParceiro.descricao}</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Nota de Curadoria (1-5)</label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setCuradoriaNota(n)}
                      className={`w-10 h-10 rounded-lg border flex items-center justify-center text-lg transition-colors ${
                        curadoriaNota >= n
                          ? "bg-yellow-100 border-yellow-400 text-yellow-700"
                          : "bg-background border-border hover:border-yellow-300"
                      }`}
                    >
                      <Star
                        className={`w-5 h-5 ${curadoriaNota >= n ? "fill-yellow-400 text-yellow-400" : ""}`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Observação</label>
                <textarea
                  className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={curadoriaObs}
                  onChange={(e) => setCuradoriaObs(e.target.value)}
                  placeholder="Por que este parceiro foi aprovado/reprovado..."
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <Button variant="outline" onClick={() => setCuradoriaParceiro(null)}>
                  Cancelar
                </Button>
                <Button
                  onClick={handleAprovar}
                  disabled={aprovarMutation.isPending}
                  className="bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Aprovar Parceiro
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
