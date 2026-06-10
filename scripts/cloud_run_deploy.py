import os
import re
import sys
import time
import subprocess
import requests
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
API_PATH = PROJECT_ROOT / "api.py"
SERVICE_NAME = "gymsite-intelligence"
REGION = "southamerica-east1"
HEALTH_CHECK_ENDPOINT = "/health"
MAX_RETRIES = 5
RETRY_DELAY = 10

def print_step(msg: str):
    print(f"\n🚀 [STEP] {msg}")

def print_success(msg: str):
    print(f"✅ [SUCCESS] {msg}")

def print_error(msg: str):
    print(f"❌ [ERROR] {msg}")

def get_port_from_code() -> str:
    """Extrai a porta do api.py ou usa 8000 como fallback."""
    print_step("Detectando porta no código fonte...")
    if API_PATH.exists():
        content = API_PATH.read_text(encoding="utf-8")
        match = re.search(r"port\s*=\s*int\(os\.getenv\(.*?,\s*(\d+)\)\)", content)
        if not match:
            match = re.search(r"port\s*=\s*(\d+)", content)
        if match:
            port = match.group(1)
            print_success(f"Porta detectada em api.py: {port}")
            return port
    print_success("Usando porta padrão: 8000")
    return "8000"

def parse_env_example() -> str:
    """Lê o .env.example e formata para o comando gcloud."""
    print_step("Configurando variáveis de ambiente a partir do .env.example...")
    if not ENV_EXAMPLE_PATH.exists():
        print_error(".env.example não encontrado!")
        sys.exit(1)
    
    env_vars = []
    lines = ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            # Tenta pegar a variável de ambiente atual se existir, senão usa o mock
            actual_val = os.getenv(key, val)
            env_vars.append(f"{key}={actual_val}")
    
    formatted = ",".join(env_vars)
    print_success(f"Variáveis mapeadas: {len(env_vars)} chaves.")
    return formatted

def get_current_revision() -> str:
    """Obtém a revisão atual para possível rollback."""
    try:
        res = subprocess.run([
            "gcloud", "run", "services", "describe", SERVICE_NAME,
            "--region", REGION,
            "--format", "value(status.latestReadyRevisionName)"
        ], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return ""

def rollback(revision: str):
    """Realiza o rollback para a revisão anterior segura."""
    print_error("Iniciando processo de Rollback Automático!")
    if not revision:
        print_error("Nenhuma revisão anterior identificada. Rollback falhou.")
        sys.exit(1)
    
    print_step(f"Revertendo tráfego para a revisão: {revision}")
    try:
        subprocess.run([
            "gcloud", "run", "services", "update-traffic", SERVICE_NAME,
            "--region", REGION,
            f"--to-revisions={revision}=100"
        ], check=True)
        print_success("Rollback concluído com sucesso!")
    except subprocess.CalledProcessError as e:
        print_error(f"Falha crítica no rollback: {e}")
        sys.exit(1)

def deploy(port: str, env_vars: str) -> str:
    """Executa o gcloud run deploy e retorna a URL do serviço."""
    print_step("Iniciando deploy no Cloud Run...")
    
    cmd = [
        "gcloud", "run", "deploy", SERVICE_NAME,
        "--source", str(PROJECT_ROOT),
        "--port", port,
        "--set-env-vars", env_vars,
        "--region", REGION,
        "--allow-unauthenticated",
        "--format", "value(status.url)"
    ]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        service_url = res.stdout.strip()
        print_success(f"Deploy finalizado! URL: {service_url}")
        return service_url
    except subprocess.CalledProcessError as e:
        print_error(f"Erro no deploy: {e.stderr}")
        sys.exit(1)

def health_check(url: str) -> bool:
    """Testa a integridade da aplicação."""
    print_step(f"Executando HTTP Health Check em: {url}{HEALTH_CHECK_ENDPOINT}")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = requests.get(f"{url}{HEALTH_CHECK_ENDPOINT}", timeout=10)
            if res.status_code == 200:
                print_success("Health check passou com sucesso!")
                return True
            else:
                print_error(f"Health check retornou status {res.status_code}. Tentativa {attempt}/{MAX_RETRIES}...")
        except requests.RequestException as e:
            print_error(f"Health check falhou (timeout/conexão): {e}. Tentativa {attempt}/{MAX_RETRIES}...")
        
        time.sleep(RETRY_DELAY)
    
    return False

def main():
    print("="*50)
    print("  AUTOMATED DEPLOY PIPELINE - GYMSITE INTELLIGENCE  ")
    print("="*50)
    
    port = get_port_from_code()
    env_vars = parse_env_example()
    
    previous_revision = get_current_revision()
    if previous_revision:
        print_success(f"Revisão ativa anterior: {previous_revision} (salva para rollback)")
    else:
        print_step("Nenhuma revisão anterior encontrada. Deploy inicial assumido.")
    
    service_url = deploy(port, env_vars)
    
    is_healthy = health_check(service_url)
    
    print("\n" + "="*50)
    if is_healthy:
        print("🎉 RELATÓRIO FINAL: SUCESSO ABSOLUTO 🎉")
        print(f"Aplicação rodando saudável em: {service_url}")
    else:
        print("🔥 RELATÓRIO FINAL: FALHA CRÍTICA 🔥")
        print("O Health Check reprovou a nova versão.")
        rollback(previous_revision)
    print("="*50)

if __name__ == "__main__":
    main()
