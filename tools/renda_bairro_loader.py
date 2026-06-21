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

# Código IBGE de UF (2 primeiros dígitos do municipio_cod) → sigla. Usado quando o CSV não
# traz coluna de UF/município (caso do agregado por DISTRITO) — uf é derivada do código.
_UF_COD = {"11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO",
 "21":"MA","22":"PI","23":"CE","24":"RN","25":"PB","26":"PE","27":"AL","28":"SE","29":"BA",
 "31":"MG","32":"ES","33":"RJ","35":"SP","41":"PR","42":"SC","43":"RS","50":"MS","51":"MT",
 "52":"GO","53":"DF"}

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

def build_json_distritos(distrito_zip, json_atual=JSON_PATH):
    """Complementa o JSON de bairros com renda por DISTRITO (IBGE 2022) — APENAS pras
    munis SEM bairro na base (SP capital cod 3550308, DF, TO). IBGE não define 'bairro'
    nessas (usam distrito/RA); aqui o distrito vira 'bairro'. Dedup por município já
    coberto (não duplica Fortaleza/Rio). Mesmas colunas V060xx do agregado por bairro.

    Uso: python -m tools.renda_bairro_loader --distritos <zip> --merge
    """
    todos_existentes = json.load(open(json_atual, encoding="utf-8")) if os.path.exists(json_atual) else []
    # Idempotência: mantém SÓ os bairros originais; descarta distritos de runs anteriores pra
    # reconstruir limpo (senão re-run pula as munis já anexadas e não corrige uf/cidade).
    existentes = [d for d in todos_existentes if "DISTRITO" not in (d.get("fonte") or "")]
    cobertos = {d.get("municipio_cod") for d in existentes}  # munis que JÁ têm camada de bairro

    # código de município → (cidade, uf): reusa o catálogo curado _MUNICIPIOS_IBGE (capitais +
    # RMs). O CSV de distrito não traz nome de cidade/UF — daqui vêm cidade+uf das munis-alvo
    # (SP capital, Brasília/DF, Palmas/TO...). Fallback de uf = _UF_COD (2 dígitos do código).
    try:
        from tools.ibge_tools import _MUNICIPIOS_IBGE
        _cod_mun = {cod: (nome, uf) for (cod, nome, uf) in _MUNICIPIOS_IBGE.values()}
    except Exception:
        _cod_mun = {}

    d = _read_csv(distrito_zip)
    dh = {h.strip().upper(): i for i, h in enumerate(d[0])}
    print(f"[distritos] colunas do CSV: {list(dh.keys())[:25]}")

    def col(*names):
        for n in names:
            if n.upper() in dh:
                return dh[n.upper()]
        return None

    c_cd = col("CD_DIST", "CD_DISTRITO", "CD_GEOCODD")
    c_nm = col("NM_DIST", "NM_DISTRITO")
    c_mun = col("NM_MUN", "NM_MUNIC", "NM_MUNICIP")
    c_uf = col("NM_UF", "SIGLA_UF", "NM_REGIAO_UF")
    c_dom = col("V06001"); c_pes = col("V06002"); c_med = col("V06004"); c_mdn = col("V06006")
    if None in (c_cd, c_med):
        raise SystemExit(f"[distritos] colunas-chave ausentes (CD_DIST/V06004). Header: {list(dh.keys())}")

    novos = []
    for r in d[1:]:
        if len(r) <= c_cd:
            continue
        cd = (r[c_cd] or "").strip()
        muni = cd[:7]
        if not muni or muni in cobertos:   # já tem bairro → não duplica
            continue
        nm = (r[c_nm].strip() if c_nm is not None and len(r) > c_nm else "")
        media = _num(r[c_med]) if len(r) > c_med else None
        if not nm or media is None:
            continue
        dom = _num(r[c_dom]) if c_dom is not None and len(r) > c_dom else None
        pes = _num(r[c_pes]) if c_pes is not None and len(r) > c_pes else None
        uf_raw = (r[c_uf].strip() if c_uf is not None and len(r) > c_uf else "")
        # cidade+uf: catálogo curado por código (_cod_mun); senão cidade do CSV (se houver) e
        # uf derivada do código (2 díg). Sem isso o app filtra .eq('uf','SP') e não acha.
        cat = _cod_mun.get(muni)
        cidade = (cat[0] if cat else (r[c_mun].strip() if c_mun is not None and len(r) > c_mun else None))
        uf = ((cat[1] if cat else None)
              or _UF_SIGLA.get(uf_raw) or (uf_raw if len(uf_raw) == 2 else None)
              or _UF_COD.get(muni[:2]))
        mor = round(pes / dom, 2) if (dom and pes) else None
        novos.append({
            "municipio_cod": muni, "cidade": cidade,
            "uf": uf, "bairro": nm, "bairro_norm": _norm(nm),
            "renda_media": round(media, 2), "renda_mediana": (_num(r[c_mdn]) if c_mdn is not None and len(r) > c_mdn else None),
            "renda_pc": round(media / mor, 2) if mor else None,
            "domicilios": int(dom) if dom else None, "pessoas": int(pes) if pes else None,
            "moradores_domicilio": mor, "ano": 2022,
            "fonte": "IBGE Censo 2022 — Rendimento do Responsável (agregado por DISTRITO; muni sem camada de bairro)",
        })

    # percentil por município (só pros novos — mesma fórmula do build_json)
    from collections import defaultdict
    by = defaultdict(list)
    for x in novos:
        by[x["municipio_cod"]].append(x)
    for grp in by.values():
        grp.sort(key=lambda x: -x["renda_media"]); n = len(grp)
        for i, x in enumerate(grp):
            x["ranking_municipio"] = i + 1
            x["percentil_municipio"] = round((n - (i + 1)) / (n - 1), 4) if n > 1 else 1.0

    munis_novas = len(by)
    print(f"[distritos] {len(novos)} distritos novos em {munis_novas} munis sem bairro (ex SP capital/DF/TO)")
    todos = existentes + novos
    json.dump(todos, open(json_atual, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[distritos] JSON agora com {len(todos)} registros (era {len(existentes)})")
    return todos


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
    ap.add_argument("--distritos", metavar="DISTRITO_ZIP",
                    help="Agregados_por_distritos_renda_responsavel_BR*.zip — complementa "
                         "munis sem bairro (SP capital/DF/TO)")
    ap.add_argument("--merge", action="store_true",
                    help="com --distritos: anexa ao JSON e carrega só os novos via load_supabase")
    a=ap.parse_args()
    rows=None
    if a.build_json and a.zips: rows=build_json(a.zips[0], a.zips[1])
    if a.distritos:
        rows=build_json_distritos(a.distritos)   # já anexa ao JSON
        # carrega TUDO (upsert idempotente — munis já existentes não mudam)
    load_supabase(rows)
