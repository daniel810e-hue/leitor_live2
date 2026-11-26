import os
import requests

# Diretório base do armazenamento interno no Android
ROOT_DIR = '/sdcard'
SERVER_URL = 'http://192.168.0.111:5000/upload'  # Altere para o IP do seu servidor se necessário

# Extensões permitidas para cada categoria
EXTENSOES_FOTO = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
EXTENSOES_VIDEO = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
EXTENSOES_MUSICA = ('.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg')

TODAS_EXTENSOES = EXTENSOES_FOTO + EXTENSOES_VIDEO + EXTENSOES_MUSICA

def enviar_arquivos():
    if not os.path.exists(ROOT_DIR):
        print(f'Diretório não encontrado: {ROOT_DIR}')
        return

    print('Varrendo pastas (ignorando a pasta Android)...')

    # Percorre todas as pastas e arquivos recursivamente
    for root, dirs, files in os.walk(ROOT_DIR):
        # Ignora completamente a pasta 'Android' e subpastas dela
        if 'Android' in root.split(os.sep):
            continue

        for arquivo in files:
            if arquivo.lower().endswith(TODAS_EXTENSOES):
                caminho_completo = os.path.join(root, arquivo)
                
                if os.path.isfile(caminho_completo):
                    print(f'Enviando: {arquivo}...')
                    try:
                        with open(caminho_completo, 'rb') as f:
                            files_data = {'file': (arquivo, f)}
                            response = requests.post(SERVER_URL, files=files_data)
                            
                            if response.status_code == 200:
                                print(f'Sucesso: {arquivo} enviado!')
                            else:
                                print(f'Erro ao enviar {arquivo}: {response.text}')
                    except Exception as e:
                        print(f'Falha na conexão com o servidor: {e}')

if __name__ == '__main__':
    enviar_arquivos()
