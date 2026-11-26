import os
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Diretório base do armazenamento interno no Android
ROOT_DIR = '/sdcard'
SERVER_URL = 'https://morbo.serveousercontent.com/upload'  # Altere para o IP do seu servidor se necessário

# Onde fica a "memória" dos arquivos já enviados (evita reenviar tudo de novo)
ENVIADOS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'enviados.json')

# Extensões permitidas para cada categoria
EXTENSOES_FOTO = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
EXTENSOES_VIDEO = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
EXTENSOES_MUSICA = ('.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg')

TODAS_EXTENSOES = EXTENSOES_FOTO + EXTENSOES_VIDEO + EXTENSOES_MUSICA

# Pausa entre cada envio (segundos) - evita sobrecarregar o celular e a rede
PAUSA_ENTRE_ENVIOS = 0.3

# Tamanho máximo (MB) para não travar com arquivos gigantes sem querer
TAMANHO_MAX_MB = 500


def carregar_enviados():
    if os.path.exists(ENVIADOS_JSON):
        try:
            with open(ENVIADOS_JSON, 'r') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def salvar_enviados(enviados):
    with open(ENVIADOS_JSON, 'w') as f:
        json.dump(list(enviados), f)


def criar_sessao():
    sessao = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    sessao.mount('http://', HTTPAdapter(max_retries=retries))
    sessao.mount('https://', HTTPAdapter(max_retries=retries))
    return sessao


def listar_arquivos_pendentes(enviados):
    pendentes = []
    for root, dirs, files in os.walk(ROOT_DIR):
        # Ignora completamente a pasta 'Android' e subpastas dela
        if 'Android' in root.split(os.sep):
            dirs[:] = []  # não entra nas subpastas também (mais rápido)
            continue

        for arquivo in files:
            if not arquivo.lower().endswith(TODAS_EXTENSOES):
                continue
            caminho_completo = os.path.join(root, arquivo)
            if caminho_completo in enviados:
                continue
            if not os.path.isfile(caminho_completo):
                continue
            pendentes.append(caminho_completo)
    return pendentes


def enviar_arquivos():
    if not os.path.exists(ROOT_DIR):
        print(f'Diretório não encontrado: {ROOT_DIR}')
        return

    enviados = carregar_enviados()
    sessao = criar_sessao()

    print('Varrendo pastas (ignorando a pasta Android)...')
    pendentes = listar_arquivos_pendentes(enviados)
    total = len(pendentes)
    print(f'{total} arquivo(s) novo(s) para enviar.')

    if total == 0:
        print('Nada novo para enviar.')
        return

    for i, caminho_completo in enumerate(pendentes, start=1):
        arquivo = os.path.basename(caminho_completo)

        tamanho_mb = os.path.getsize(caminho_completo) / (1024 * 1024)
        if tamanho_mb > TAMANHO_MAX_MB:
            print(f'[{i}/{total}] Pulando (muito grande, {tamanho_mb:.0f}MB): {arquivo}')
            enviados.add(caminho_completo)
            continue

        print(f'[{i}/{total}] Enviando: {arquivo} ({tamanho_mb:.1f}MB)...')
        try:
            with open(caminho_completo, 'rb') as f:
                files_data = {'file': (arquivo, f)}
                response = sessao.post(SERVER_URL, files=files_data, timeout=60)

                if response.status_code == 200:
                    print(f'  Sucesso: {arquivo}')
                    enviados.add(caminho_completo)
                else:
                    print(f'  Erro ({response.status_code}): {arquivo} -> {response.text[:200]}')
        except Exception as e:
            print(f'  Falha na conexão com o servidor: {e}')
            # Para por aqui nesta rodada em vez de martelar o servidor sem parar
            break

        # Salva progresso a cada arquivo, para não perder o que já foi feito
        # se o script for interrompido
        salvar_enviados(enviados)

        # Pequena pausa para não sobrecarregar o celular/rede
        time.sleep(PAUSA_ENTRE_ENVIOS)

    print('Concluído.')


if __name__ == '__main__':
    enviar_arquivos()
