import type { BuscarConcorrentesResult } from "@/lib/siteAgent";
import { rotuloMostrando } from "@/lib/concorrentesCardCopy";
import { ExternalLink, MapPin } from "lucide-react";

/** Lista autoritativa de concorrentes (Formato 1) — total só do JSON da tool. */
export function ConcorrentesCard({ data }: { data: BuscarConcorrentesResult }) {
  if (data.erro) {
    return (
      <div className="mt-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
        Não deu pra mapear concorrentes agora ({data.erro}). Tente de novo.
      </div>
    );
  }

  const lista = data.concorrentes ?? [];
  const total = data.total_concorrentes ?? lista.length;
  const avisoLista = rotuloMostrando(lista.length, total);

  return (
    <div className="mt-2 rounded-lg border border-lime/30 bg-card/80 px-3 py-2.5 text-sm">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-semibold text-foreground">
          {total} {total === 1 ? "academia" : "academias"}
          {data.nivel_saturacao ? (
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              saturação {data.nivel_saturacao}
            </span>
          ) : null}
        </p>
        {avisoLista ? (
          <span className="text-[10px] uppercase tracking-wide text-amber-200/90">
            {avisoLista}
          </span>
        ) : null}
      </div>

      {lista.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          Nenhuma academia no filtro atual (tipo={data.tipo_negocio || "academia"}).
        </p>
      ) : (
        <ul className="max-h-56 space-y-2 overflow-y-auto text-xs">
          {lista.map((c, i) => (
            <li key={c.place_id || `${c.nome}-${i}`} className="border-b border-border/40 pb-1.5 last:border-0">
              <div className="font-medium text-foreground">{c.nome}</div>
              {c.endereco ? (
                <div className="mt-0.5 flex gap-1 text-muted-foreground">
                  <MapPin className="mt-0.5 h-3 w-3 shrink-0 opacity-70" />
                  <span>{c.endereco}</span>
                </div>
              ) : null}
              {(c.rating != null || c.distancia_m != null) && (
                <div className="mt-0.5 text-muted-foreground/80">
                  {c.rating != null ? `${c.rating}★` : null}
                  {c.rating != null && c.distancia_m != null ? " · " : null}
                  {c.distancia_m != null ? `${c.distancia_m} m` : null}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
        {data.query ? <span className="font-mono opacity-80">{data.query}</span> : null}
        {data.maps_smoke_url ? (
          <a
            href={data.maps_smoke_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-lime hover:underline"
          >
            Maps <ExternalLink className="h-3 w-3" />
          </a>
        ) : null}
      </div>
    </div>
  );
}
