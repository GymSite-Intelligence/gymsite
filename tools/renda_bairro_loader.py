"""
Loader nacional de renda por bairro (IBGE Censo 2022 — Rendimento do Responsável).

Junta os agregados por bairro do IBGE (FTP Agregados_por_Setores_Censitarios_
Rendimento_do_Responsavel + básico p/ nome de município/UF) → tabela Supabase
`renda_bairro` (17k bairros, BR). Fonte nacional única — supersede IPECE/Data.Rio.

Uso:
    python -m tools.renda_bairro_loader --from-json   # carrega do JSON versionado
    python -m tools.renda_bairro_loader --zips A.zip B.zip --build-json  # regenera o JSON
"""
from __future__ import annotations
import argparse, csv, io, json, os, re, unicodedata, zipfile
from tools.db_schema import tbl

JSON_PATH = "tools/data/ibge_renda_bairro_BR_2022.json"

_UF_SIGLA = {"Acre":"AC","Alagoas":"AL","Amapá":"AP","Amazonas":"AM","Bahia":"BA","Ceará":"CE",
 "Distrito Federal":"DF","Espírito Santo":"ES","Goiás":"GO","Maranhão":"MA","Mato Grosso":"MT",
 "Mato Grosso do Sul":"MS","Minas Gerais":"MG","Pará":"PA","Paraíba":"PB","Paraná":"PR",
 "Pernambuco":"PE","Piauí":"PI","Rio de Janeiro":"RJ","Rio Grande do Norte":"RN",
 "Rio Grande do Sul":"RS","Rondônia":"RO","Roraima":"RR","Santa Catarina":"SC",
 "São Paulo":"SP","Sergipe":"SE","Tocantins":"TO"}

def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii","ignore").decode().lower().strip()
    return re.sub(r"\s+"," ",s)
def _num(s):
    s=(s or "").strip().replace(".","").replace(",",".")
    try: return float(s)
    except: return None
def _read_csv(zip_path):
    z=zipfile.ZipFile(zip_path); n=[x for x in z.namelist() if x.lower().endswith(".csv")][0]
    raw=z.read(n)
    for enc in ("utf-8-sig","latin-1","cp1252"):
        try: txt=raw.decode(enc); break
        except: continue
    return list(csv.reader(io.StringIO(txt), delimiter=";"))

def build_json(basico_zip, renda_zip):
    # básico: CD_BAIRRO -> (NM_MUN, NM_UF)
    b=_read_csv(basico_zip); bh={h:i for i,h in enumerate(b[0])}
    geo={}
    for r in b[1:]:
        if len(r)<=bh["CD_BAIRRO"]: continue
        geo[r[bh["CD_BAIRRO"]]]=(r[bh.get("NM_MUN",6)], r[bh.get("NM_UF",4)])
    # renda
    rd=_read_csv(renda_zip); rh={h:i for i,h in enumerate(rd[0])}
    rows=[]
    for r in rd[1:]:
        if len(r)<=rh["NM_BAIRRO"]: continue
        cd=r[rh["CD_BAIRRO"]]; nm=r[rh["NM_BAIRRO"]].strip()
        dom=_num(r[rh["V06001"]]); pes=_num(r[rh["V06002"]])
        media=_num(r[rh["V06004"]]); mediana=_num(r[rh["V06006"]])
        if not nm or media is None: continue
        mun,uf=geo.get(cd,(None,None))
        uf=_UF_SIGLA.get(uf, uf)
        mor=round(pes/dom,2) if dom else None
        rows.append({"municipio_cod":cd[:7],"cidade":mun,"uf":uf,"bairro":nm,"bairro_norm":_norm(nm),
                     "renda_media":round(media,2),"renda_mediana":mediana,
                     "renda_pc":round(media/mor,2) if mor else None,
                     "domicilios":int(dom) if dom else None,"pessoas":int(pes) if pes else None,
                     "moradores_domicilio":mor,"ano":2022,
                     "fonte":"IBGE Censo 2022 — Rendimento do Responsável (agregados por bairro)"})
    # percentil por município
    from collections import defaultdict
    by=defaultdict(list)
    for d in rows: by[d["municipio_cod"]].append(d)
    for grp in by.values():
        grp.sort(key=lambda d:-d["renda_media"]); n=len(grp)
        for i,d in enumerate(grp):
            d["ranking_municipio"]=i+1
            d["percentil_municipio"]=round((n-(i+1))/(n-1),4) if n>1 else 1.0
    json.dump(rows, open(JSON_PATH,"w",encoding="utf-8"), ensure_ascii=False)
    print(f"[build] {len(rows)} bairros -> {JSON_PATH}")
    return rows

def load_supabase(rows=None):
    from dotenv import load_dotenv; load_dotenv()
    from tools.supabase_client import load_create_client
    if rows is None: rows=json.load(open(JSON_PATH,encoding="utf-8"))
    # dedup por (municipio_cod, bairro_norm) — mantém maior renda (evita ON CONFLICT 21000)
    vis={}
    for d in rows:
        k=(d["municipio_cod"], d["bairro_norm"])
        if k not in vis or (d.get("renda_media") or 0) > (vis[k].get("renda_media") or 0):
            vis[k]=d
    rows=list(vis.values())
    print(f"[load] {len(rows)} bairros únicos após dedup")
    cli=load_create_client()(os.environ["SUPABASE_URL"], os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY"))
    B=1000; tot=0
    for i in range(0,len(rows),B):
        tbl(cli, "renda_bairro").upsert(rows[i:i+B], on_conflict="municipio_cod,bairro_norm").execute(); tot+=len(rows[i:i+B])
        print(f"  upsert {tot}/{len(rows)}", flush=True)
    print(f"[load] {tot} bairros no Supabase")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--zips", nargs=2, metavar=("BASICO","RENDA"))
    ap.add_argument("--build-json", action="store_true")
    ap.add_argument("--from-json", action="store_true")
    a=ap.parse_args()
    rows=None
    if a.build_json and a.zips: rows=build_json(a.zips[0], a.zips[1])
    load_supabase(rows)
