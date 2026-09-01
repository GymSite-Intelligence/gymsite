from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path

import httpx

from tools.security_audit.models import AuditReport, Finding, Severity


SEVERITY_COLOR = {
    Severity.CRITICAL: "#dc2626",
    Severity.HIGH: "#ea580c",
    Severity.MEDIUM: "#ca8a04",
    Severity.LOW: "#2563eb",
    Severity.INFO: "#6b7280",
}


def write_json(report: AuditReport, path: Path) -> None:
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(report: AuditReport, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "test_id",
                "title",
                "severity",
                "cvss",
                "owasp",
                "description",
                "evidence",
                "recommendation",
            ],
        )
        writer.writeheader()
        for f in report.findings:
            writer.writerow(
                {
                    "test_id": f.test_id,
                    "title": f.title,
                    "severity": f.severity.value,
                    "cvss": f.cvss,
                    "owasp": f.owasp,
                    "description": f.description,
                    "evidence": f.evidence,
                    "recommendation": f.recommendation,
                }
            )


def _executive_summary(report: AuditReport) -> str:
    c = report.counts
    if c.get("critical", 0):
        return (
            f"Foram encontradas {c['critical']} vulnerabilidade(s) crítica(s). "
            "Interrompa deploy até correção e reteste."
        )
    if c.get("high", 0):
        return f"{c['high']} achado(s) de alta severidade exigem plano de remediação em 7 dias."
    return "Nenhum achado crítico/alto nos testes automatizados. Manter monitoramento contínuo."


def write_html(report: AuditReport, path: Path) -> None:
    rows = []
    for f in report.findings:
        color = SEVERITY_COLOR.get(f.severity, "#333")
        rows.append(
            f"<tr>"
            f"<td><span style='color:{color};font-weight:700'>{escape(f.severity.value.upper())}</span></td>"
            f"<td>{escape(f.title)}</td>"
            f"<td>{f.cvss}</td>"
            f"<td>{escape(f.owasp)}</td>"
            f"<td><pre>{escape(f.evidence[:800])}</pre></td>"
            f"<td>{escape(f.recommendation)}</td>"
            f"</tr>"
        )

    poc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <title>Security Audit — {escape(report.target)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0f1115; color: #eef1f4; }}
    h1 {{ color: #84cc01; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
    th, td {{ border: 1px solid #2b323d; padding: 0.5rem; vertical-align: top; }}
    th {{ background: #181c22; }}
    pre {{ white-space: pre-wrap; font-size: 12px; }}
    .summary {{ background: #181c22; padding: 1rem; border-radius: 8px; border: 1px solid #2b323d; }}
  </style>
</head>
<body>
  <h1>Security Audit Report</h1>
  <p><strong>Target:</strong> {escape(report.target)}</p>
  <p><strong>Period:</strong> {escape(report.started_at)} → {escape(report.finished_at)}</p>
  <div class="summary">
    <h2>Executive summary</h2>
    <p>{escape(_executive_summary(report))}</p>
    <p><strong>Counts:</strong> {escape(str(report.counts))}</p>
    {"<p><strong>Stopped early:</strong> " + escape(report.stop_reason or "") + "</p>" if report.stopped_early else ""}
  </div>
  <h2>Technical findings</h2>
  <table>
    <thead><tr><th>Severity</th><th>Title</th><th>CVSS</th><th>OWASP</th><th>Evidence</th><th>Recommendation</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
</body>
</html>"""
    path.write_text(poc, encoding="utf-8")


def write_poc_clickjacking(report: AuditReport, path: Path) -> None:
    html = f"""<!DOCTYPE html>
<html><head><title>Clickjacking PoC</title></head>
<body>
  <h1>Clickjacking PoC — authorized test only</h1>
  <iframe src="{escape(report.target)}" width="800" height="600" style="border:2px solid red;"></iframe>
</body></html>"""
    path.write_text(html, encoding="utf-8")


async def notify_webhook(url: str, report: AuditReport) -> None:
    payload = {
        "text": f"Security audit {report.target}: critical={report.counts.get('critical',0)} high={report.counts.get('high',0)}",
        "summary": _executive_summary(report),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)


def write_all(report: AuditReport, output_prefix: Path) -> dict[str, Path]:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output_prefix.with_suffix(".json"),
        "html": output_prefix.with_suffix(".html"),
        "csv": output_prefix.with_suffix(".csv"),
        "poc_clickjacking": output_prefix.parent / f"{output_prefix.name}_clickjacking_poc.html",
    }
    write_json(report, paths["json"])
    write_html(report, paths["html"])
    write_csv(report, paths["csv"])
    write_poc_clickjacking(report, paths["poc_clickjacking"])
    return paths
