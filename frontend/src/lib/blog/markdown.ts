import { marked } from "marked";

marked.setOptions({
  gfm: true,
  breaks: false,
});

/** Render markdown → HTML seguro o bastante pra posts internos (sem script). */
export function renderMarkdown(md: string): string {
  return marked.parse(md, { async: false }) as string;
}
