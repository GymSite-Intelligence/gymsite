import type { PlantaLayoutResult } from "@/lib/siteAgent";
import { Download } from "lucide-react";

function svgDataUri(svg: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function baixarSvg(svg: string) {
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "gymsite-planta-anteprojeto.svg";
  a.click();
  URL.revokeObjectURL(url);
}

/** Planta SVG das zonas (tool gerar_planta_layout_zonas) — anteprojeto, não RRT. */
export function PlantaLayoutCard({ data }: { data: PlantaLayoutResult }) {
  if (data.erro) {
    return (
      <div className="mt-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
        Não deu pra gerar a planta agora ({data.erro}).
      </div>
    );
  }

  const svg = data.svg?.trim();
  const dims = data.dimensoes_m;
  const zonas = data.zonas ?? [];

  return (
    <div className="mt-2 rounded-lg border border-lime/30 bg-card/80 px-3 py-2.5 text-sm">
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-foreground">Planta · anteprojeto</p>
          {dims ? (
            <p className="text-xs text-muted-foreground">
              {dims.comprimento}×{dims.largura} m
              {dims.area_informada_m2 != null ? ` · ${dims.area_informada_m2} m²` : null}
            </p>
          ) : null}
          {data.fluxo ? (
            <p className="mt-0.5 text-[10px] text-muted-foreground/90">{data.fluxo}</p>
          ) : null}
        </div>
        {svg ? (
          <button
            type="button"
            onClick={() => baixarSvg(svg)}
            className="inline-flex items-center gap-1 rounded-md border border-lime/40 px-2 py-1 text-[10px] font-medium text-lime hover:bg-lime/10"
          >
            <Download className="h-3 w-3" aria-hidden />
            SVG
          </button>
        ) : null}
      </div>

      {svg ? (
        <div className="mb-2 overflow-auto rounded-md border border-border/60 bg-[#13161b] p-2">
          <img
            src={svgDataUri(svg)}
            alt="Planta baixa anteprojeto — zonas da musculação"
            className="mx-auto max-h-72 w-full object-contain"
          />
        </div>
      ) : null}

      {zonas.length > 0 ? (
        <ul className="max-h-40 space-y-1 overflow-y-auto text-xs text-muted-foreground">
          {zonas.map((z, i) => (
            <li key={`${z.nome}-${i}`} className="flex justify-between gap-2 border-b border-border/30 pb-1 last:border-0">
              <span className="text-foreground">{z.nome}</span>
              {z.area_m2 != null ? <span className="shrink-0 tabular-nums">{z.area_m2} m²</span> : null}
            </li>
          ))}
        </ul>
      ) : null}

      {data.aviso ? (
        <p className="mt-2 text-[10px] leading-snug text-muted-foreground/90">{data.aviso}</p>
      ) : null}
    </div>
  );
}
