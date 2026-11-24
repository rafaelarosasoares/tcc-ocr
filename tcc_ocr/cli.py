"""Interface de linha de comando."""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .atividades import CONFIGURACOES
from .configuracoes import carregar_configuracao
from .drive import preparar_entrada


def criar_parser():
    parser = argparse.ArgumentParser(
        description="Processa as atividades a partir do disco ou Google Drive."
    )
    parser.add_argument(
        "--drive",
        action="store_true",
        help="Usa a pasta do Drive definida em config/projeto.json.",
    )
    parser.add_argument(
        "--drive-folder",
        help="ID ou link da pasta raiz do Drive (ou GOOGLE_DRIVE_FOLDER_ID).",
    )
    parser.add_argument(
        "--entrada",
        help="Pasta local de entrada; com Drive, diretório onde salvar as importações.",
    )
    parser.add_argument(
        "--somente-baixar",
        action="store_true",
        help="Baixa do Drive sem executar Document AI/Gemini.",
    )
    modos = parser.add_mutually_exclusive_group()
    modos.add_argument(
        "--validar",
        action="store_true",
        help="Valida todas as imagens e pares sem chamar as APIs de OCR/IA.",
    )
    modos.add_argument(
        "--somente-planilha", action="store_true", help="Recria o Excel apenas com os JSONs salvos."
    )
    modos.add_argument(
        "--preparar-avaliacao",
        action="store_true",
        help="Cria amostra para transcrição e conferência manual.",
    )
    modos.add_argument(
        "--avaliar",
        metavar="ARQUIVO",
        help="Compara uma avaliação manual preenchida com os resultados salvos.",
    )
    modos.add_argument(
        "--retomar", action="store_true", help="Retoma a última execução usando os checkpoints."
    )
    parser.add_argument(
        "--config", help="Arquivo de configuração do projeto (padrão: config/projeto.json)."
    )
    parser.add_argument("--resultados", help="Diretório de resultados, relatórios e caches.")
    parser.add_argument(
        "--tentativas", type=int, help="Tentativas por chamada em falhas transitórias (1 a 5)."
    )
    parser.add_argument(
        "--forcar", action="store_true", help="Ignora caches de OCR e interpretação."
    )
    parser.add_argument(
        "--sem-qualidade-imagem",
        action="store_true",
        help="Desabilita métricas de qualidade para processadores que não as suportam.",
    )
    parser.add_argument(
        "--amostra",
        type=int,
        default=10,
        help="Número de registros na amostra manual, distribuídos por atividade.",
    )
    parser.add_argument(
        "--semente", type=int, default=42, help="Semente da amostragem reproduzível."
    )
    parser.add_argument(
        "--arquivo-amostra",
        help="Caminho do novo arquivo de avaliação manual (não sobrescreve arquivos existentes).",
    )
    return parser


def _resultados_salvos(pasta):
    from .fluxo import carregar_resultados
    from .persistencia import carregar

    caminho = pasta / "relatorio_execucao.json"
    relatorio = carregar(caminho) if caminho.exists() else None
    resultados = carregar_resultados(
        pasta, CONFIGURACOES, relatorio["registros"] if relatorio else None
    )
    if not any(resultados.values()):
        raise ValueError("Não há resultados concluídos para esta operação.")
    return resultados, relatorio


def _executar_offline(opcoes, pasta, config):
    resultados, relatorio = _resultados_salvos(pasta)
    if opcoes.somente_planilha:
        from .planilha import gerar_planilha

        gerar_planilha(
            resultados,
            destino=pasta,
            relatorio=relatorio,
            max_revisar=config.max_revisar_por_registro,
        )
    elif opcoes.preparar_avaliacao:
        from .avaliacao import preparar_avaliacao

        destino = (
            Path(opcoes.arquivo_amostra)
            if opcoes.arquivo_amostra
            else pasta / "avaliacao_manual.json"
        )
        documento = preparar_avaliacao(
            resultados, CONFIGURACOES, destino, opcoes.amostra, opcoes.semente
        )
        print(
            f"Amostra com {documento['registros_na_amostra']} registros para conferência: {destino}"
        )
    else:
        from .avaliacao import avaliar

        destino = pasta / "relatorio_avaliacao.json"
        metricas = avaliar(opcoes.avaliar, resultados, CONFIGURACOES, destino)
        print(
            f"Campos conferidos: {metricas['campos_conferidos']}; concordância: {metricas['concordancia_exata']}"
        )
        print(f"Relatório de avaliação: {destino}")
    return 0


def _validar(entrada, pasta):
    from .persistencia import salvar_atomico
    from .validacao import validar_entrada

    validacao = validar_entrada(entrada, CONFIGURACOES)
    destino = pasta / "validacao_entrada.json"
    salvar_atomico(destino, validacao)
    invalidos = sum(item["estado"] == "invalido" for item in validacao["registros"])
    for item in validacao["registros"]:
        for erro in item["erros_validacao"]:
            print(f"  ✗ {item['atividade']}/{item['codigo']}: {erro}")
        for aviso in item["avisos"]:
            print(f"  Aviso {item['codigo']}: {aviso}")
    for aviso in validacao["avisos"]:
        print("  Aviso:", aviso)
    print(f"Validação: {len(validacao['registros'])} registros, {invalidos} inválidos. {destino}")
    return 1 if invalidos else 0


def _resumo(relatorio, pasta):
    print("\nEstado da execução:", relatorio["estado"])
    for estado, total in relatorio["resumo"].items():
        print(f"  {estado}: {total}")
    for registro in relatorio["registros"]:
        for erro in registro.get("erros_validacao", []):
            print(f"  ✗ {registro['atividade']}/{registro['codigo']}: {erro}")
    for aviso in relatorio.get("avisos", []):
        print("  Aviso:", aviso)
    print(f"Relatório: {pasta / 'relatorio_execucao.json'}")


def _processar(opcoes, config, pasta):
    from .persistencia import carregar, salvar_atomico

    caminho_relatorio = pasta / "relatorio_execucao.json"
    if opcoes.retomar:
        if not caminho_relatorio.exists():
            raise ValueError("Não há execução anterior para retomar.")
        if not opcoes.entrada and not opcoes.drive and not opcoes.drive_folder:
            opcoes.entrada = carregar(caminho_relatorio)["entrada"]
    entrada, somente_baixar = preparar_entrada(
        CONFIGURACOES, configuracao_drive=config.drive, opcoes=opcoes, raiz=config.raiz
    )
    if somente_baixar:
        return 0
    if opcoes.validar:
        return _validar(entrada, pasta)

    from .extracao import Extrator
    from .fluxo import executar_lote
    from .normalizacao import normalizar_resultado
    from .planilha import gerar_planilha

    with Extrator(config) as extrator:
        relatorio, resultados = executar_lote(
            entrada,
            pasta,
            CONFIGURACOES,
            extrator.executar_ocr,
            extrator.interpretar,
            normalizar_resultado,
            extrator.assinaturas_interpretacao(CONFIGURACOES),
            extrator.config_ocr(),
            config.modelo_gemini,
            config.versao,
            tentativas=config.tentativas,
            retomar=opcoes.retomar,
            forcar=opcoes.forcar,
        )
    _resumo(relatorio, pasta)
    if resultados and any(resultados.values()):
        relatorio["planilha"] = "pendente"
        salvar_atomico(caminho_relatorio, relatorio)
        try:
            gerar_planilha(
                resultados,
                destino=pasta,
                relatorio=relatorio,
                max_revisar=config.max_revisar_por_registro,
            )
            relatorio["planilha"] = "concluida"
        except Exception:
            relatorio["planilha"] = "erro"
            salvar_atomico(caminho_relatorio, relatorio)
            raise
        salvar_atomico(caminho_relatorio, relatorio)
    if relatorio["estado"] != "concluido":
        print("Há pendências. Corrija a entrada ou use --retomar para tentar novamente.")
        return 1
    return 0


def main(argumentos=None):
    parser = criar_parser()
    opcoes = parser.parse_args(argumentos)
    if opcoes.tentativas is not None and not 1 <= opcoes.tentativas <= 5:
        parser.error("--tentativas deve estar entre 1 e 5.")
    if opcoes.amostra < 1:
        parser.error("--amostra deve ser positivo.")
    offline = opcoes.somente_planilha or opcoes.preparar_avaliacao or opcoes.avaliar
    if opcoes.somente_baixar and (offline or opcoes.retomar or opcoes.validar):
        parser.error("--somente-baixar não pode ser combinado com outros modos de execução.")
    if offline and (opcoes.drive or opcoes.drive_folder or opcoes.entrada):
        parser.error("O modo offline usa --resultados; não informe opções de entrada/Drive.")
    try:
        config = carregar_configuracao(opcoes.config)
        if opcoes.tentativas is not None:
            config = replace(config, tentativas=opcoes.tentativas)
        if opcoes.sem_qualidade_imagem:
            config = replace(config, qualidade_imagem=False)
        pasta = (
            Path(opcoes.resultados).expanduser().resolve()
            if opcoes.resultados
            else config.raiz / "resultados"
        )
        return (
            _executar_offline(opcoes, pasta, config)
            if offline
            else _processar(opcoes, config, pasta)
        )
    except KeyboardInterrupt:
        print("\nExecução interrompida. Use --retomar para continuar pelo relatório salvo.")
        return 130
    except Exception as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
