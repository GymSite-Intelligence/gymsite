"""
DAG Airflow — espelha scripts/batch/run_weekly_market_batch.py (Fase C).

Copiar para a pasta DAGs do Airflow na VM, ex.:
  cp scripts/batch/dags/gym_market_weekly_dag.py /opt/airflow/dags/

Requer: apache-airflow instalado no scheduler.
"""
from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
except ImportError as exc:  # pragma: no cover — só importado no Airflow
    raise ImportError(
        "Instale apache-airflow no ambiente do scheduler para carregar este DAG."
    ) from exc

# Ajuste REPO_ROOT na VM
REPO_ROOT = "/opt/gymsite_intelligence"

default_args = {
    "owner": "gymsite",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=15),
}

with DAG(
    dag_id="gym_market_weekly_batch",
    default_args=default_args,
    description="CVM + SINAPI + benchmarks + market bundles (market_waves)",
    schedule="0 3 * * 0",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["gymsite", "market_data"],
) as dag:
    BashOperator(
        task_id="run_weekly_market_batch",
        bash_command=(
            f"cd {REPO_ROOT} && "
            "python3 scripts/batch/run_weekly_market_batch.py --skip-enrichment "
            ">> /var/log/gym_market_batch.log 2>&1"
        ),
    )

    BashOperator(
        task_id="golden_bundle_a0_gate",
        bash_command=(
            f"cd {REPO_ROOT} && "
            "python3 scripts/batch/golden_bundle_a0_gate.py --wave red"
        ),
    )

    run_weekly >> golden_gate
