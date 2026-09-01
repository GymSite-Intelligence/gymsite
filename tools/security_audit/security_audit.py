#!/usr/bin/env python3
"""
SaaS API/Web Security Audit CLI.

AUTHORIZED USE ONLY — run only against systems you own or have written permission to test.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import AuditReport, utc_now_iso
from tools.security_audit.reporter import notify_webhook, write_all
from tools.security_audit.scanners import SCANNERS, run_scanners

DEFAULT_TESTS = list(SCANNERS.keys())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GymSite SaaS security audit toolkit")
    p.add_argument("--target", help="Base URL (https://api.example.com)")
    p.add_argument("--targets-file", help="File with one URL per line")
    p.add_argument("--config", help="JSON config file (overrides CLI)")
    p.add_argument("--token", help="Bearer JWT / access token")
    p.add_argument("--user-a-token", help="Token for user A (IDOR)")
    p.add_argument("--user-b-token", help="Token for user B (IDOR)")
    p.add_argument("--api-key", help="API key value")
    p.add_argument("--proxy", help="HTTP proxy (Burp/ZAP), e.g. http://127.0.0.1:8080")
    p.add_argument("--output", default="report", help="Output file prefix (no extension)")
    p.add_argument("--tests", default=",".join(DEFAULT_TESTS), help="Comma list of tests")
    p.add_argument("--critical-stop", action="store_true", default=True, help="Stop on critical SQLi/IDOR")
    p.add_argument("--no-critical-stop", action="store_false", dest="critical_stop")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    p.add_argument("--webhook", help="Slack/Teams webhook URL")
    return p.parse_args(argv)


async def audit_target(
    target: str,
    config: AuditConfig,
    tests: list[str],
    output: Path,
    log: AuditLogger,
    critical_stop: bool,
    webhook: str | None,
) -> AuditReport:
    started = utc_now_iso()
    log.info(f"Target: {target}")
    log.warning("Authorized testing only — ensure you have permission.")

    client = RateLimitedClient(target, config)
    try:
        findings, stopped, reason = await run_scanners(client, config, log, tests, critical_stop)
    finally:
        await client.close()

    report = AuditReport(
        target=target,
        started_at=started,
        finished_at=utc_now_iso(),
        findings=findings,
        stopped_early=stopped,
        stop_reason=reason,
        tests_run=tests,
    )
    paths = write_all(report, output)
    log.info(f"JSON: {paths['json']}")
    log.info(f"HTML: {paths['html']}")
    log.info(f"CSV:  {paths['csv']}")
    if webhook:
        await notify_webhook(webhook, report)
    return report


async def main_async(args: argparse.Namespace) -> int:
    log = AuditLogger(verbose=args.verbose)

    if args.config:
        config = AuditConfig.from_file(Path(args.config))
        if args.target:
            config.targets = [args.target.rstrip("/")]
    else:
        if not args.target and not args.targets_file:
            log.error("Provide --target or --targets-file or --config")
            return 2
        targets = []
        if args.target:
            targets.append(args.target.rstrip("/"))
        if args.targets_file:
            targets.extend(
                line.strip()
                for line in Path(args.targets_file).read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            )
        config = AuditConfig(
            targets=targets,
            token=args.token,
            user_a_token=args.user_a_token,
            user_b_token=args.user_b_token,
            api_key=args.api_key,
            proxy=args.proxy,
            verify_ssl=not args.insecure,
            webhook_url=args.webhook,
            critical_stop=args.critical_stop,
        )

    if args.token:
        config.token = args.token
    if args.proxy:
        config.proxy = args.proxy
    if args.insecure:
        config.verify_ssl = False

    tests = [t.strip() for t in args.tests.split(",") if t.strip()]
    exit_code = 0

    for i, target in enumerate(config.targets):
        out = Path(args.output)
        if len(config.targets) > 1:
            safe = target.replace("https://", "").replace("http://", "").replace("/", "_")
            out = out.parent / f"{out.name}_{safe}"
        report = await audit_target(
            target,
            config,
            tests,
            out,
            log,
            config.critical_stop,
            args.webhook or config.webhook_url,
        )
        if report.counts.get("critical", 0) or report.stopped_early:
            exit_code = 1

    return exit_code


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
