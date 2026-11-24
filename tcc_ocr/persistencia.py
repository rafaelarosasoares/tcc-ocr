"""Hashes e arquivos JSON com publicação atômica."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def assinatura(valor):
    return hashlib.sha256(
        json.dumps(valor, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def hash_arquivo(caminho):
    digest = hashlib.sha256()
    with Path(caminho).open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def salvar_atomico(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(caminho.parent), delete=False
        ) as arquivo:
            temporario = arquivo.name
            json.dump(dados, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
            arquivo.write("\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    finally:
        if temporario and os.path.exists(temporario):
            os.unlink(temporario)


def carregar(caminho):
    with Path(caminho).open(encoding="utf-8") as arquivo:
        return json.load(arquivo)
