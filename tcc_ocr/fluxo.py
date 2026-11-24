"""Execução com checkpoints, retomada e caches independentes por etapa."""

import time
from collections import Counter
from pathlib import Path

from .persistencia import agora, assinatura, carregar, hash_arquivo, salvar_atomico
from .validacao import sem_identificacao, validar_entrada, validar_resultado

ESTADOS_CONCLUIDOS = {"processado", "reaproveitado"}


def erro_transitorio(erro):
    from google.api_core import exceptions as google_errors
    from httpx import TransportError
    from requests import ConnectionError, Timeout

    if isinstance(
        erro,
        (
            TimeoutError,
            ConnectionError,
            Timeout,
            TransportError,
            google_errors.TooManyRequests,
            google_errors.ServiceUnavailable,
            google_errors.DeadlineExceeded,
            google_errors.InternalServerError,
            google_errors.BadGateway,
            google_errors.GatewayTimeout,
        ),
    ):
        return True
    codigo = getattr(erro, "status_code", None) or getattr(erro, "code", None)
    return codigo in {429, 500, 502, 503, 504}


def erro_autorizacao(erro):
    from google.api_core.exceptions import PermissionDenied, Unauthenticated
    from google.auth.exceptions import DefaultCredentialsError, RefreshError

    codigo = getattr(erro, "status_code", None) or getattr(erro, "code", None)
    return isinstance(
        erro, (PermissionDenied, Unauthenticated, DefaultCredentialsError, RefreshError)
    ) or codigo in {401, 403}


def tentar(funcao, tentativas=3, esperar=None, ao_tentar=None):
    esperar = esperar or time.sleep
    for tentativa in range(1, tentativas + 1):
        if ao_tentar:
            ao_tentar(tentativa)
        try:
            return funcao()
        except Exception as erro:
            if tentativa == tentativas or not erro_transitorio(erro):
                raise
            esperar(min(2 ** (tentativa - 1), 8))


def atualizar_resumo(relatorio):
    contagem = Counter(item["estado"] for item in relatorio["registros"])
    relatorio["resumo"] = {
        estado: contagem[estado]
        for estado in ("processado", "reaproveitado", "erro", "invalido", "pendente", "processando")
    }
    relatorio["atualizado_em"] = agora()
    return relatorio


def carregar_resultados(pasta_resultados, configuracoes, registros=None):
    pasta = Path(pasta_resultados)
    resultados = {atividade: [] for atividade in configuracoes}
    if registros is None:
        caminhos = [
            (atividade, caminho)
            for atividade in configuracoes
            for caminho in sorted((pasta / atividade).glob("*.json"))
        ]
    else:
        caminhos = [
            (item["atividade"], pasta / item["atividade"] / (item["codigo"] + ".json"))
            for item in registros
            if item["estado"] in ESTADOS_CONCLUIDOS
        ]
    for atividade, caminho in caminhos:
        try:
            resultado = sem_identificacao(carregar(caminho))
            validar_resultado(resultado, configuracoes[atividade])
            resultado["codigo_aluno"] = resultado.get("codigo_aluno") or caminho.stem
            resultados[atividade].append(resultado)
        except (ValueError, OSError) as erro:
            raise ValueError(f"Resultado salvo inválido: {caminho}: {erro}") from erro
    enriquecer_fontes(resultados, pasta.parent)
    return resultados


def enriquecer_fontes(resultados, raiz):
    """Localiza fontes antigas apenas quando seu SHA-256 coincide com o registrado.

    Não altera os JSONs históricos nem presume que imagens de mesmo nome tenham
    o mesmo conteúdo. Permite revisar os resultados legados sem novas chamadas.
    """
    raiz = Path(raiz).resolve()
    entradas = [raiz / "entrada"] + sorted(
        (raiz / "entrada_drive").glob("importacao-*"), reverse=True
    )
    hashes = {}
    for atividade, registros in resultados.items():
        for registro in registros:
            fontes = registro.setdefault("_fontes", {})
            esperados = registro.get("_processamento", {}).get("hashes_entrada", {})
            for tipo in ("questao", "resposta"):
                if fontes.get(tipo):
                    continue
                nome = registro.get("arquivo_" + tipo)
                if not nome or Path(nome).name != nome or not esperados.get(tipo):
                    continue
                for entrada in entradas:
                    caminho = entrada / atividade / nome
                    if not caminho.is_file():
                        continue
                    if caminho not in hashes:
                        hashes[caminho] = hash_arquivo(caminho)
                    if hashes[caminho] == esperados[tipo]:
                        fontes[tipo] = {"local": str(caminho), "drive": None}
                        break


def executar_lote(
    entrada,
    pasta_resultados,
    configuracoes,
    ocr,
    interpretar,
    normalizar,
    assinatura_interpretacao,
    config_ocr,
    modelo,
    versao,
    inicializar=lambda: None,
    tentativas=3,
    retomar=False,
    forcar=False,
):
    pasta = Path(pasta_resultados)
    caminho_relatorio = pasta / "relatorio_execucao.json"
    anterior = carregar(caminho_relatorio) if retomar else None
    validacao = validar_entrada(entrada, configuracoes)
    relatorio = {
        **validacao,
        "estado": "validando",
        "config_ocr": config_ocr,
        "assinaturas": assinatura_interpretacao,
        "modelo": modelo,
        "versao": versao,
    }
    if anterior:
        anteriores = {(item["atividade"], item["codigo"]): item for item in anterior["registros"]}
        for registro in relatorio["registros"]:
            antigo = anteriores.get((registro["atividade"], registro["codigo"]))
            if (
                antigo
                and antigo["estado"] in ESTADOS_CONCLUIDOS
                and antigo.get("hashes") == registro["hashes"]
                and anterior.get("assinaturas") == assinatura_interpretacao
                and anterior.get("config_ocr") == config_ocr
                and not forcar
            ):
                # Um checkpoint concluído só é reutilizável se o arquivo ainda
                # existir, respeitar o schema e corresponder à assinatura atual.
                try:
                    salvo = carregar(pasta / registro["atividade"] / (registro["codigo"] + ".json"))
                    validar_resultado(salvo, configuracoes[registro["atividade"]])
                    esperado = assinatura(
                        {
                            "interpretacao": assinatura_interpretacao[registro["atividade"]],
                            "ocr": config_ocr,
                            "imagens": registro["hashes"],
                        }
                    )
                    if salvo.get("_processamento", {}).get("assinatura") == esperado:
                        registro["estado"] = "reaproveitado"
                except (ValueError, OSError, AttributeError):
                    pass
    fontes = (
        carregar(Path(entrada) / "_origem_drive.json")
        if (Path(entrada) / "_origem_drive.json").exists()
        else {}
    )

    def checkpoint():
        salvar_atomico(caminho_relatorio, atualizar_resumo(relatorio))

    checkpoint()
    if any(item["estado"] == "invalido" for item in relatorio["registros"]):
        relatorio["estado"] = "entrada_invalida"
        checkpoint()
        return relatorio, None
    nuvem_pronta = False

    def chamada(funcao, registro):
        nonlocal nuvem_pronta
        if not nuvem_pronta:
            inicializar()
            nuvem_pronta = True

        def tentativa(numero):
            registro["tentativa"] = numero
            checkpoint()

        return tentar(funcao, tentativas=tentativas, ao_tentar=tentativa)

    relatorio["estado"] = "processando"
    for registro in relatorio["registros"]:
        atividade, codigo = registro["atividade"], registro["codigo"]
        assinatura_atual = assinatura(
            {
                "interpretacao": assinatura_interpretacao[atividade],
                "ocr": config_ocr,
                "imagens": registro["hashes"],
            }
        )
        caminho = pasta / atividade / (codigo + ".json")
        registro["estado"] = "processando"
        registro["etapa"] = "cache_resultado"
        checkpoint()
        try:
            existente = None
            if caminho.exists() and not forcar:
                try:
                    existente = carregar(caminho)
                    validar_resultado(existente, configuracoes[atividade])
                except (ValueError, OSError):
                    existente = None
            metadados = existente.get("_processamento", {}) if existente else {}
            if (
                existente
                and isinstance(metadados, dict)
                and metadados.get("assinatura") == assinatura_atual
            ):
                resultado = sem_identificacao(existente)
                registro["estado"] = "reaproveitado"
            else:
                ocrs = {}
                for tipo, imagem in registro["arquivos"].items():
                    registro["etapa"] = "ocr_" + tipo
                    checkpoint()
                    chave_ocr = assinatura(
                        {"imagem": registro["hashes"][tipo], "config": config_ocr}
                    )
                    cache_ocr = pasta / ".cache_ocr" / (chave_ocr + ".json")
                    dado_ocr = None
                    if cache_ocr.exists() and not forcar:
                        try:
                            dado_ocr = carregar(cache_ocr)
                            if not isinstance(dado_ocr.get("texto"), str) or not isinstance(
                                dado_ocr.get("paginas"), list
                            ):
                                dado_ocr = None
                        except (ValueError, OSError, AttributeError):
                            dado_ocr = None
                    if dado_ocr is None:
                        dado_ocr = chamada(lambda: ocr(imagem), registro)
                        salvar_atomico(cache_ocr, dado_ocr)
                    ocrs[tipo] = dado_ocr
                registro["etapa"] = "interpretacao"
                checkpoint()
                texto = "\n\n".join(
                    f"OCR DA IMAGEM {tipo.upper()}:\n{dados['texto']}"
                    for tipo, dados in ocrs.items()
                )

                def extrair():
                    return validar_resultado(
                        interpretar(registro, texto, configuracoes[atividade]),
                        configuracoes[atividade],
                    )

                resultado = normalizar(chamada(extrair, registro))
                resultado["_processamento"] = {
                    "assinatura": assinatura_atual,
                    "hashes_entrada": registro["hashes"],
                    "assinatura_interpretacao": assinatura_interpretacao[atividade],
                    "config_ocr": config_ocr,
                    "modelo": modelo,
                    "versao": versao,
                    "processado_em": agora(),
                }
                resultado["_qualidade_imagens"] = {
                    tipo: dados["paginas"] for tipo, dados in ocrs.items()
                }
                registro["estado"] = "processado"
            resultado = sem_identificacao(resultado)
            resultado["codigo_aluno"], resultado["codigo_atividade"] = codigo, atividade
            resultado["_fontes"] = {}
            for tipo, imagem in registro["arquivos"].items():
                resultado["arquivo_" + tipo] = Path(imagem).name
                origem = fontes.get(atividade + "/" + Path(imagem).name, {})
                resultado["_fontes"][tipo] = {"local": imagem, "drive": origem.get("url")}
            resultado["_avisos_entrada"] = registro["avisos"]
            registro["etapa"] = "salvar_resultado"
            salvar_atomico(caminho, resultado)
            registro["etapa"] = "concluido"
            print(f"  ✓ {atividade}/{codigo}: {registro['estado']}")
        except Exception as erro:
            registro["estado"] = "erro"
            registro["erro"] = {"tipo": type(erro).__name__, "mensagem": str(erro)[:1500]}
            print(f"  ✗ {atividade}/{codigo}: falha em {registro['etapa']} ({type(erro).__name__})")
            if erro_autorizacao(erro):
                relatorio["avisos"].append(
                    "Execução interrompida por falha de autorização. Os demais registros continuam pendentes para --retomar."
                )
                checkpoint()
                break
        checkpoint()
    relatorio["estado"] = (
        "parcial"
        if any(item["estado"] not in ESTADOS_CONCLUIDOS for item in relatorio["registros"])
        else "concluido"
    )
    checkpoint()
    return relatorio, carregar_resultados(pasta, configuracoes, relatorio["registros"])
