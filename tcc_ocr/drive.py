"""Importação de imagens do Google Drive para a entrada do processamento."""

import hashlib
import json
import os
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, urlparse

API = "https://www.googleapis.com/drive/v3/files"
PASTA_MIME = "application/vnd.google-apps.folder"
ESCOPOS = ["https://www.googleapis.com/auth/drive.readonly"]


def extrair_id_pasta(valor):
    """Aceita um ID, um link /folders/ID ou /open?id=ID."""
    valor = valor.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]+", valor):
        return valor
    url = urlparse(valor)
    if url.scheme == "https" and url.hostname == "drive.google.com":
        trecho = re.search(r"/folders/([A-Za-z0-9_-]+)(?:/|$)", url.path)
        identificador = trecho.group(1) if trecho else parse_qs(url.query).get("id", [""])[0]
        if re.fullmatch(r"[A-Za-z0-9_-]+", identificador):
            return identificador
    raise ValueError("Informe o ID ou o link de uma pasta do Google Drive.")


def _nome_seguro(nome):
    if (
        not nome
        or nome in (".", "..")
        or "/" in nome
        or "\\" in nome
        or any(ord(caractere) < 32 for caractere in nome)
    ):
        raise ValueError(f"Nome de arquivo inválido no Drive: {nome!r}")
    return nome


def _md5(caminho):
    digest = hashlib.md5()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _listar_filhos(sessao, pasta_id):
    parametros = {
        "q": f"'{pasta_id}' in parents and trashed = false",
        "fields": "nextPageToken,incompleteSearch,files(id,name,mimeType,md5Checksum,webViewLink)",
        "pageSize": 1000,
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
    }
    arquivos = []
    while True:
        with sessao.get(API, params=parametros, timeout=60) as resposta:
            resposta.raise_for_status()
            dados = resposta.json()
        if dados.get("incompleteSearch"):
            raise ValueError("O Drive retornou uma listagem incompleta. Tente novamente.")
        arquivos.extend(dados.get("files", []))
        token = dados.get("nextPageToken")
        if not token:
            return arquivos
        parametros["pageToken"] = token


def baixar_entrada(
    pasta,
    destino,
    atividades,
    sessao,
    pastas_atividades=None,
    pastas_atividades_por_id=None,
):
    """Cria uma entrada completa em um diretório novo; nunca altera a origem.

    Cada execução recebe seu próprio diretório para que arquivos removidos do
    Drive não entrem no OCR por terem sobrado de uma importação anterior.
    """
    pasta_id = extrair_id_pasta(pasta)

    def listar_pasta(pasta_id_atual):
        with sessao.get(
            f"{API}/{pasta_id_atual}",
            params={"fields": "id,mimeType,trashed", "supportsAllDrives": "true"},
            timeout=60,
        ) as resposta:
            resposta.raise_for_status()
            metadados = resposta.json()
        if metadados.get("mimeType") != PASTA_MIME or metadados.get("trashed"):
            raise ValueError("A origem deve ser uma pasta do Drive fora da lixeira.")
        return _listar_filhos(sessao, pasta_id_atual)

    pastas_raiz = listar_pasta(pasta_id)

    mapa = {codigo: codigo for codigo in atividades}
    mapa.update(pastas_atividades or {})
    pastas_por_id = pastas_atividades_por_id or {}
    if any(codigo not in atividades for codigo in mapa.values()) or any(
        codigo not in atividades for codigo in pastas_por_id
    ):
        raise ValueError("O mapeamento do Drive contém uma atividade desconhecida.")
    imagens = []
    ignoradas = 0
    arquivos_ignorados = []
    pastas_vistas = set()

    def incluir_imagens(atividade, arquivos):
        nonlocal ignoradas
        nomes_vistos = set()
        for imagem in arquivos:
            nome = imagem["name"]
            if imagem["mimeType"].startswith("application/vnd.google-apps."):
                continue
            if not Path(nome).suffix:
                nome += {"image/jpeg": ".jpg", "image/png": ".png"}.get(imagem["mimeType"], "")
            if Path(nome).suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            _nome_seguro(nome)
            if not re.fullmatch(r".+_(questao|resposta)\.(jpg|jpeg|png)", nome, re.IGNORECASE):
                ignoradas += 1
                arquivos_ignorados.append(
                    {
                        "atividade": atividade,
                        "arquivo": nome,
                        "motivo": "Nome sem sufixo _questao/_resposta.",
                    }
                )
                continue
            chave = unicodedata.normalize("NFC", nome).casefold()
            if chave in nomes_vistos:
                raise ValueError(f"Há imagens com nomes duplicados em {atividade}: {nome}")
            nomes_vistos.add(chave)
            imagens.append((atividade, {**imagem, "name": nome}))

    def registrar_pasta(atividade):
        if atividade in pastas_vistas:
            raise ValueError(f"Há pastas duplicadas no Drive: {atividade}")
        _nome_seguro(atividade)
        pastas_vistas.add(atividade)

    for item in pastas_raiz:
        atividade = mapa.get(item["name"])
        if item["mimeType"] != PASTA_MIME or atividade is None:
            continue
        registrar_pasta(atividade)
        incluir_imagens(atividade, _listar_filhos(sessao, item["id"]))

    for atividade, pasta_atividade in pastas_por_id.items():
        registrar_pasta(atividade)
        incluir_imagens(atividade, listar_pasta(extrair_id_pasta(pasta_atividade)))

    if not imagens:
        raise ValueError(
            "Nenhuma imagem JPG/PNG encontrada nas pastas configuradas para as atividades: "
            + ", ".join(atividades)
        )

    destino = Path(destino)
    # O destino novo evita misturar arquivos locais e importações anteriores.
    # mkdtemp também impede sobrescritas e colisões em execuções simultâneas.
    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".baixando-", dir=str(destino)) as temporario:
        raiz = Path(temporario)
        origens = {}
        reaproveitadas = 0
        for atividade, imagem in imagens:
            caminho = raiz / atividade / imagem["name"]
            caminho.parent.mkdir(exist_ok=True)
            md5 = imagem.get("md5Checksum") or ""
            cache = destino / ".cache_drive" / md5 if re.fullmatch(r"[a-f0-9]{32}", md5) else None
            if cache and cache.is_file() and _md5(cache) == md5:
                shutil.copyfile(cache, caminho)
                reaproveitadas += 1
            else:
                with sessao.get(
                    f"{API}/{imagem['id']}",
                    params={"alt": "media", "supportsAllDrives": "true"},
                    stream=True,
                    timeout=60,
                ) as resposta:
                    resposta.raise_for_status()
                    with caminho.open("wb") as arquivo:
                        for bloco in resposta.iter_content(chunk_size=1024 * 1024):
                            arquivo.write(bloco)
            if imagem.get("md5Checksum") and _md5(caminho) != imagem["md5Checksum"]:
                raise ValueError(f"Download incompleto ou alterado no Drive: {imagem['name']}")
            if cache:
                cache.parent.mkdir(exist_ok=True)
                # Publicação atômica também no cache, sem compartilhar arquivos mutáveis.
                with tempfile.TemporaryDirectory(dir=str(cache.parent)) as temporario_cache:
                    arquivo_cache = Path(temporario_cache) / "imagem"
                    shutil.copyfile(caminho, arquivo_cache)
                    os.replace(arquivo_cache, cache)
            origens[atividade + "/" + imagem["name"]] = {
                "id": imagem["id"],
                "md5": md5,
                "url": imagem.get("webViewLink")
                or f"https://drive.google.com/file/d/{imagem['id']}/view",
            }
            print(f"  ✓ {atividade}/{imagem['name']}")

        (raiz / "_origem_drive.json").write_text(
            json.dumps(origens, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (raiz / "_ignorados_drive.json").write_text(
            json.dumps(arquivos_ignorados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Só disponibiliza a entrada depois que todos os downloads terminarem.
        pasta_final = Path(tempfile.mkdtemp(prefix="importacao-", dir=str(destino)))
        os.replace(raiz, pasta_final)

    print(f"\n✓ {len(imagens)} imagem(ns) importada(s) em {pasta_final}")
    print(f"  {reaproveitadas} imagem(ns) reaproveitada(s) do cache local.")
    if ignoradas:
        print(f"  {ignoradas} imagem(ns) sem sufixo _questao/_resposta ignorada(s).")
    return str(pasta_final)


def preparar_entrada(atividades, argumentos=None, configuracao_drive=None, opcoes=None, raiz=None):
    configuracao_drive = configuracao_drive or {}
    from .cli import criar_parser

    parser = criar_parser()
    opcoes = opcoes or parser.parse_args(argumentos)
    pasta_drive = opcoes.drive_folder or (
        configuracao_drive.get("pasta_id")
        if opcoes.drive
        else (os.environ.get("GOOGLE_DRIVE_FOLDER_ID") if not opcoes.entrada else None)
    )
    if opcoes.drive and not pasta_drive:
        parser.error("Configure pasta_id em config/projeto.json ou informe --drive-folder.")
    if not pasta_drive:
        if opcoes.somente_baixar:
            parser.error(
                "--somente-baixar exige --drive, --drive-folder ou GOOGLE_DRIVE_FOLDER_ID."
            )
        return opcoes.entrada or str(Path(raiz or ".") / "entrada"), False

    import google.auth
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import AuthorizedSession
    from requests import RequestException
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    try:
        # Valida antes de procurar credenciais ou fazer chamadas de rede.
        extrair_id_pasta(pasta_drive)
        credenciais, _ = google.auth.default(scopes=ESCOPOS)
        with AuthorizedSession(credenciais) as sessao:
            sessao.mount(
                "https://",
                HTTPAdapter(
                    max_retries=Retry(
                        total=3,
                        backoff_factor=1,
                        status_forcelist=(429, 500, 502, 503, 504),
                        allowed_methods=("GET",),
                    )
                ),
            )
            entrada = baixar_entrada(
                pasta_drive,
                opcoes.entrada or str(Path(raiz or ".") / "entrada_drive"),
                atividades,
                sessao,
                pastas_atividades=configuracao_drive.get("pastas_atividades"),
                pastas_atividades_por_id=configuracao_drive.get("pastas_atividades_por_id"),
            )
    except GoogleAuthError as erro:
        parser.exit(
            1,
            f"Erro de autenticação no Drive: {erro}\nConfigure as credenciais conforme docs/autenticacao.md.\n",
        )
    except RequestException as erro:
        detalhe = str(erro)
        if erro.response is not None:
            try:
                detalhe = erro.response.json().get("error", {}).get("message") or detalhe
            except ValueError:
                pass
        parser.exit(
            1,
            f"Erro ao acessar o Drive: {detalhe}\nVerifique a API, o acesso à pasta e o escopo drive.readonly (docs/autenticacao.md).\n",
        )
    except (ValueError, OSError) as erro:
        parser.exit(1, f"Erro ao importar entrada: {erro}\n")
    return entrada, opcoes.somente_baixar
