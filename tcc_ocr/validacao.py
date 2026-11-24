"""Contratos das respostas e conferência das imagens antes de acessar as APIs."""

import json
import re
import warnings
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from PIL import Image

from .persistencia import agora, carregar, hash_arquivo

CAMPOS_IDENTIFICACAO = {"nome_estudante", "nome_status", "ano"}
PADRAO_ARQUIVO = re.compile(
    r"^(?P<codigo>[A-Za-z0-9-]+)_(?P<tipo>questao|resposta)\.(jpg|jpeg|png)$", re.I
)


def sem_identificacao(resultado):
    if not isinstance(resultado, dict):
        raise ValueError("O resultado deve ser um objeto JSON.")
    return {chave: valor for chave, valor in resultado.items() if chave not in CAMPOS_IDENTIFICACAO}


def schema_local(schema):
    """Converte o subconjunto de schema do Gemini em JSON Schema padrão."""
    convertido = {
        chave: valor
        for chave, valor in schema.items()
        if chave not in {"type", "nullable", "properties", "items"}
    }
    tipo = schema.get("type", "OBJECT").lower()
    convertido["type"] = [tipo, "null"] if schema.get("nullable") else tipo
    if "enum" in convertido and schema.get("nullable"):
        convertido["enum"] = list(convertido["enum"]) + [None]
    if "properties" in schema:
        convertido["properties"] = {
            chave: schema_local(valor) for chave, valor in schema["properties"].items()
        }
        convertido["additionalProperties"] = False
    if "items" in schema:
        convertido["items"] = schema_local(schema["items"])
    return convertido


def validar_resultado(resultado, configuracao):
    dados = {
        chave: valor
        for chave, valor in sem_identificacao(resultado).items()
        if chave in configuracao["schema"]["properties"]
    }
    erros = sorted(
        _validador(json.dumps(configuracao["schema"], sort_keys=True)).iter_errors(dados),
        key=lambda erro: str(list(erro.path)),
    )
    if erros:
        erro = erros[0]
        campo = ".".join(map(str, erro.path)) or "resultado"
        # Não imprime o conteúdo da resposta nem dados da folha no relatório.
        raise ValueError(f"Resposta fora do schema em {campo} ({erro.validator}).")
    return dados


@lru_cache(maxsize=32)
def _validador(schema_serializado):
    return Draft202012Validator(schema_local(json.loads(schema_serializado)))


def validar_entrada(entrada, configuracoes):
    raiz = Path(entrada).resolve()
    registros, avisos = [], []
    if not raiz.is_dir():
        raise ValueError(f"Pasta de entrada não encontrada: {raiz}")
    ignorados_drive = raiz / "_ignorados_drive.json"
    if ignorados_drive.exists():
        for item in carregar(ignorados_drive):
            avisos.append(
                f"Arquivo ignorado no Drive: {item['atividade']}/{item['arquivo']}: {item['motivo']}"
            )
    for atividade, configuracao in configuracoes.items():
        pasta = raiz / atividade
        if not pasta.is_dir():
            avisos.append(f"Atividade sem pasta: {atividade}")
            continue
        grupos = {}
        for caminho in sorted(pasta.iterdir()):
            if caminho.name.startswith("."):
                continue
            nome = PADRAO_ARQUIVO.fullmatch(caminho.name)
            if not nome:
                avisos.append(f"Arquivo ignorado: {atividade}/{caminho.name}")
                continue
            codigo, tipo = nome["codigo"].upper(), nome["tipo"].lower()
            registro = grupos.setdefault(
                codigo,
                {
                    "atividade": atividade,
                    "codigo": codigo,
                    "arquivos": {},
                    "hashes": {},
                    "erros_validacao": [],
                    "avisos": [],
                    "estado": "pendente",
                    "etapa": "validacao",
                },
            )
            if tipo in registro["arquivos"]:
                registro["erros_validacao"].append(f"Mais de uma imagem de {tipo} para {codigo}.")
                continue
            registro["arquivos"][tipo] = str(caminho.resolve())
            try:
                if not caminho.is_file() or caminho.is_symlink():
                    raise ValueError("A entrada deve ser um arquivo regular, sem atalhos locais.")
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(caminho) as imagem:
                        formato = imagem.format
                        largura, altura = imagem.size
                        imagem.verify()
                    with Image.open(caminho) as imagem:
                        imagem.load()
                esperado = "PNG" if caminho.suffix.lower() == ".png" else "JPEG"
                if formato != esperado:
                    raise ValueError("O conteúdo da imagem não corresponde à extensão.")
                if min(largura, altura) < 700:
                    registro["avisos"].append(
                        f"{tipo}: imagem pequena ({largura}×{altura}); confira a legibilidade."
                    )
                registro["hashes"][tipo] = hash_arquivo(caminho)
            except (
                OSError,
                ValueError,
                SyntaxError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
            ) as erro:
                registro["erros_validacao"].append(
                    f"Imagem {tipo} inválida: {type(erro).__name__}: {erro}"
                )
        for registro in grupos.values():
            obrigatorios = {"resposta"}
            if configuracao["modo_entrada"] == "questao_resposta":
                obrigatorios.add("questao")
            faltantes = obrigatorios - registro["arquivos"].keys()
            if faltantes:
                registro["erros_validacao"].append(
                    "Imagem ausente: " + ", ".join(sorted(faltantes))
                )
            if registro["erros_validacao"]:
                registro["estado"] = "invalido"
            registros.append(registro)
    if not registros:
        raise ValueError("Nenhum registro de aluno encontrado na entrada.")
    return {"entrada": str(raiz), "registros": registros, "avisos": avisos, "criado_em": agora()}
