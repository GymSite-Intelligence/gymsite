import os
import re
import json
import ast
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent

# Severidades para ordenação
SEVERITY_MAP = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "INFO": 4
}

class AgentA:
    """Agente A: Analisa lógica Python e exceções não tratadas."""
    def run(self) -> List[Dict[str, Any]]:
        results = []
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if "venv" in py_file.parts or ".venv" in py_file.parts or "node_modules" in py_file.parts:
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                # Check bare excepts and prints
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        if node.type is None:
                            results.append({
                                "file": str(py_file.relative_to(PROJECT_ROOT)),
                                "line": node.lineno,
                                "type": "Bare Except",
                                "severity": "HIGH",
                                "suggestion": "Especificar o tipo de exceção (ex: except Exception as e:)."
                            })
                    elif isinstance(node, ast.Call):
                        if getattr(node.func, "id", None) == "print":
                            results.append({
                                "file": str(py_file.relative_to(PROJECT_ROOT)),
                                "line": node.lineno,
                                "type": "Print in Production",
                                "severity": "MEDIUM",
                                "suggestion": "Substituir print() por logging."
                            })
            except Exception as e:
                results.append({
                    "file": str(py_file.relative_to(PROJECT_ROOT)),
                    "line": 0,
                    "type": "Parse Error",
                    "severity": "HIGH",
                    "suggestion": f"Erro de sintaxe Python: {e}"
                })
        return results

class AgentB:
    """Agente B: Verifica dependências e variáveis de ambiente."""
    def run(self) -> List[Dict[str, Any]]:
        results = []
        env_example = PROJECT_ROOT / ".env.example"
        req_txt = PROJECT_ROOT / "requirements.txt"
        
        if not env_example.exists():
            results.append({
                "file": ".env.example",
                "line": 0,
                "type": "Missing Config",
                "severity": "CRITICAL",
                "suggestion": "Criar o arquivo .env.example para documentar variáveis do projeto."
            })
        
        if req_txt.exists():
            lines = req_txt.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines, 1):
                if "==" not in line and line.strip() and not line.startswith("#"):
                    results.append({
                        "file": "requirements.txt",
                        "line": i,
                        "type": "Unpinned Dependency",
                        "severity": "MEDIUM",
                        "suggestion": f"Fixar a versão da dependência '{line.strip()}' com ==."
                    })
        else:
            results.append({
                "file": "requirements.txt",
                "line": 0,
                "type": "Missing Config",
                "severity": "MEDIUM",
                "suggestion": "Arquivo requirements.txt não encontrado. Sugere-se exportar dependências."
            })
            
        return results

class AgentC:
    """Agente C: Analisa integrações externas e banco de dados."""
    def run(self) -> List[Dict[str, Any]]:
        results = []
        
        # Procura chaves vazadas em arquivos e valida endpoints hardcoded
        sensitive_patterns = [
            (r"['\"]sk-[a-zA-Z0-9]{20,}['\"]", "Possible OpenAI/API Key Leak"),
            (r"['\"]AIzaSy[a-zA-Z0-9_-]{33}['\"]", "Possible Google API Key Leak"),
            (r"['\"]http://(localhost|127\.0\.0\.1)", "Hardcoded Localhost URL")
        ]
        
        for file in PROJECT_ROOT.rglob("*.*"):
            if file.suffix not in [".py", ".js", ".ts", ".tsx"] or "node_modules" in file.parts or ".venv" in file.parts:
                continue
                
            try:
                lines = file.read_text(encoding="utf-8").splitlines()
                for i, line in enumerate(lines, 1):
                    for pattern, issue_type in sensitive_patterns:
                        if re.search(pattern, line):
                            severity = "CRITICAL" if "Key" in issue_type else "MEDIUM"
                            results.append({
                                "file": str(file.relative_to(PROJECT_ROOT)),
                                "line": i,
                                "type": issue_type,
                                "severity": severity,
                                "suggestion": "Mover a credencial/URL para variáveis de ambiente."
                            })
            except Exception:
                pass # Ignora arquivos binários ou erros de decoding
                
        return results

def main():
    print("Iniciando Agentes de Análise Paralela...")
    agents = [AgentA(), AgentB(), AgentC()]
    
    all_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(agent.run): idx for idx, agent in enumerate(agents, 1)}
        
        for future in concurrent.futures.as_completed(futures):
            agent_id = futures[future]
            try:
                res = future.result()
                all_results.extend(res)
                print(f"✅ Agente {agent_id} finalizou sua análise. ({len(res)} issues)")
            except Exception as e:
                print(f"❌ Agente {agent_id} falhou com erro: {e}")
                
    # Ordenar por severidade
    all_results.sort(key=lambda x: SEVERITY_MAP.get(x["severity"], 99))
    
    out_path = PROJECT_ROOT / "scripts" / "consolidated_report.json"
    out_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print("\nRelatório Consolidado Gerado:")
    print(f"Arquivo: {out_path}")
    print(f"Total de issues detectadas: {len(all_results)}")
    
    # Previews
    for severity in ["CRITICAL", "HIGH", "MEDIUM"]:
        count = sum(1 for r in all_results if r["severity"] == severity)
        print(f"  {severity}: {count}")

if __name__ == "__main__":
    main()
