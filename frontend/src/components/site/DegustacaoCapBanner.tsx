type DegustacaoCapBannerProps = {
  texto: string;
  onCta: () => void;
};

/** Cap diário do chat — lime, mesmo DNA dos CTAs da degustação. */
export function DegustacaoCapBanner({ texto, onCta }: DegustacaoCapBannerProps) {
  return (
    <div
      role="status"
      className="rounded-xl border border-lime/40 bg-lime/10 px-3 py-3 text-sm text-foreground sm:px-4"
    >
      <p className="leading-relaxed">{texto}</p>
      <button
        type="button"
        onClick={onCta}
        className="mt-3 inline-flex rounded-md bg-lime px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-lime-glow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lime"
      >
        Pedir análise gratuita
      </button>
    </div>
  );
}
