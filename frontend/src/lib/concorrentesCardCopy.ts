/** Rótulo do card: só quando a lista visível é menor que o total da tool. */
export function rotuloMostrando(mostrados: number, total: number): string | null {
  if (!Number.isFinite(mostrados) || !Number.isFinite(total)) return null;
  if (mostrados <= 0 || total <= 0) return null;
  if (mostrados >= total) return null;
  return `mostrando ${Math.floor(mostrados)} de ${Math.floor(total)}`;
}
