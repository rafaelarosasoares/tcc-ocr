"""Amostragem reproduzível e comparação com transcrições humanas independentes."""

import random
import unicodedata
from collections import defaultdict
from pathlib import Path

from .persistencia import assinatura, carregar, salvar_atomico


def _questoes(configuracao):
    return sorted(
        (
            chave
            for chave in configuracao["schema"]["properties"]
            if chave.startswith("q") and chave[1:].isdigit()
        ),
        key=lambda chave: int(chave[1:]),
    )


def _normalizar(valor):
    if isinstance(valor, str):
        return " ".join(unicodedata.normalize("NFC", valor).split())
    if isinstance(valor, list):
        return [_normalizar(item) for item in valor]
    if isinstance(valor, dict):
        return {chave: _normalizar(item) for chave, item in valor.items()}
    return valor


def preparar_avaliacao(resultados, configuracoes, destino, tamanho=10, semente=42):
    if tamanho < 1:
        raise ValueError("O tamanho da amostra deve ser positivo.")
    destino = Path(destino)
    if destino.exists():
        raise ValueError(
            f"A avaliação já existe: {destino}. Use outro nome ou preserve a anterior antes de gerar outra."
        )
    grupos = defaultdict(list)
    for atividade, registros in resultados.items():
        for registro in registros:
            tem_pendencia = any(
                registro.get(questao, {}).get("status") in {"revisar", "ilegivel"}
                for questao in _questoes(configuracoes[atividade])
            )
            grupos[(atividade, tem_pendencia)].append(registro)
    aleatorio = random.Random(semente)
    for chave in sorted(grupos):
        grupos[chave].sort(key=lambda item: item["codigo_aluno"])
        aleatorio.shuffle(grupos[chave])
    amostra = []
    while len(amostra) < tamanho and any(grupos.values()):
        for chave in sorted(grupos):
            if grupos[chave] and len(amostra) < tamanho:
                amostra.append((chave[0], grupos[chave].pop()))
    if not amostra:
        raise ValueError("Não há resultados salvos para preparar a avaliação.")
    itens = []
    for atividade, registro in amostra:
        for questao in _questoes(configuracoes[atividade]):
            campos = configuracoes[atividade]["schema"]["properties"][questao]["properties"]
            itens.append(
                {
                    "atividade": atividade,
                    "codigo": registro["codigo_aluno"],
                    "questao": questao,
                    "fontes": registro.get("_fontes", {}),
                    "referencia": {campo: None for campo in campos if campo != "status"},
                    "conferido": False,
                    "assinatura_extracao": assinatura(registro[questao]),
                }
            )
    documento = {
        "versao": 1,
        "semente": semente,
        "registros_na_amostra": len(amostra),
        "instrucoes": "Transcreva a imagem sem consultar a extração automática. Preencha referencia com os mesmos tipos do schema (texto, booleano ou lista). Use null para campo realmente vazio e só marque conferido como true depois da conferência. Não invente referências para conteúdo ilegível: deixe conferido=false. A amostra distribui registros por atividade e presença de pendências; os percentuais descrevem esta amostra, não toda a turma.",
        "itens": itens,
    }
    salvar_atomico(destino, documento)
    return documento


def avaliar(referencia, resultados, configuracoes, destino):
    documento = carregar(referencia)
    if documento.get("versao") != 1 or not isinstance(documento.get("itens"), list):
        raise ValueError("Formato de avaliação não reconhecido.")
    indice = {
        (atividade, registro["codigo_aluno"]): registro
        for atividade, registros in resultados.items()
        for registro in registros
    }
    detalhes, grupos, vistos = [], defaultdict(list), set()
    nao_conferidos = 0
    for item in documento["itens"]:
        if item.get("conferido") is not True:
            nao_conferidos += 1
            continue
        chave = item["atividade"], item["codigo"], item["questao"]
        if chave in vistos:
            raise ValueError("Questão repetida na referência manual: " + "/".join(chave))
        vistos.add(chave)
        atividade, codigo, questao = chave
        if atividade not in configuracoes or questao not in _questoes(configuracoes[atividade]):
            raise ValueError("Atividade ou questão desconhecida na referência.")
        registro = indice.get((atividade, codigo))
        if registro is None:
            raise ValueError("Registro da referência não encontrado: " + atividade + "/" + codigo)
        extraido = registro[questao]
        if assinatura(extraido) != item.get("assinatura_extracao"):
            raise ValueError("A extração mudou depois da criação da amostra: " + "/".join(chave))
        schema = configuracoes[atividade]["schema"]["properties"][questao]
        campos = {campo for campo in schema["properties"] if campo != "status"}
        referencia_manual = item.get("referencia")
        if not isinstance(referencia_manual, dict) or set(referencia_manual) != campos:
            raise ValueError("Preencha todos os campos da referência em " + "/".join(chave))
        # Valida os tipos, incluindo campos vazios, sem avaliar a correção pedagógica.
        from jsonschema import Draft202012Validator

        from .validacao import schema_local

        schema_referencia = {
            "type": "OBJECT",
            "properties": {campo: schema["properties"][campo] for campo in campos},
            "required": sorted(campos),
        }
        if not Draft202012Validator(schema_local(schema_referencia)).is_valid(referencia_manual):
            raise ValueError("Tipo inválido na referência manual de " + "/".join(chave))
        for campo in sorted(campos):
            correto = _normalizar(extraido.get(campo)) == _normalizar(referencia_manual[campo])
            detalhe = {
                "atividade": atividade,
                "codigo": codigo,
                "questao": questao,
                "campo": campo,
                "concorda": correto,
                "status_modelo": extraido.get("status"),
            }
            detalhes.append(detalhe)
            grupos[atividade].append(correto)
    acertos = sum(item["concorda"] for item in detalhes)
    total = len(detalhes)
    relatorio = {
        "campos_conferidos": total,
        "campos_concordantes": acertos,
        "concordancia_exata": acertos / total if total else None,
        "questoes_nao_conferidas": nao_conferidos,
        "divergencias_marcadas_ok": sum(
            not item["concorda"] and item["status_modelo"] == "ok" for item in detalhes
        ),
        "por_atividade": {
            atividade: {"campos": len(valores), "concordancia_exata": sum(valores) / len(valores)}
            for atividade, valores in grupos.items()
        },
        "criterio": "Correspondência de conteúdo por campo, normalizando apenas Unicode e espaços. Listas preservam ordem. Descrições semanticamente equivalentes podem divergir; confira os casos antes de interpretar as métricas. Não é uma nota do estudante nem uma estimativa de precisão da turma.",
        "detalhes": detalhes,
    }
    salvar_atomico(destino, relatorio)
    return relatorio
