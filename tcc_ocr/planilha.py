"""Exportação atômica do Excel, sem estado global e sem chamadas às APIs."""

import os
import tempfile
from pathlib import Path

from .persistencia import agora, hash_arquivo, salvar_atomico

COLUNAS_REVISAO = [
    "Código",
    "Atividade",
    "Questão",
    "Status",
    "Motivo",
    "Dados extraídos",
    "Abrir questão",
    "Abrir resposta",
    "Arquivo questão",
    "Arquivo resposta",
]


def formatar_booleano(valor):
    if valor is True:
        return "Sim"
    if valor is False:
        return "Não"
    return ""


def formatar_lista(valor, separador=", "):
    if not valor:
        return ""
    return separador.join((str(item) for item in valor))


def montar_linha_chaves(resultado):
    q1 = resultado.get("q1", {})
    q2 = resultado.get("q2", {})
    q3 = resultado.get("q3", {})
    q4 = resultado.get("q4", {})
    q5 = resultado.get("q5", {})
    q6 = resultado.get("q6", {})
    q7 = resultado.get("q7", {})
    return {
        "Código": resultado.get("codigo_aluno", ""),
        "Q1 - Alternativa": q1.get("alternativa", ""),
        "Q1 - Status": q1.get("status", ""),
        "Q2 - Sequência": formatar_lista(q2.get("sequencia"), separador=" → "),
        "Q2 - Observação": q2.get("observacao") or "",
        "Q2 - Status": q2.get("status", ""),
        "Q3 - Resposta": q3.get("resposta") or "",
        "Q3 - Status": q3.get("status", ""),
        "Q4 - Testou caminho": formatar_booleano(q4.get("testou_caminho")),
        "Q4 - Representação": q4.get("representacao") or "",
        "Q4 - Status": q4.get("status", ""),
        "Q5 - Resposta": q5.get("resposta") or "",
        "Q5 - Status": q5.get("status", ""),
        "Q6 - Resposta": q6.get("resposta") or "",
        "Q6 - Status": q6.get("status", ""),
        "Q7 - Mudou resposta": formatar_booleano(q7.get("mudou_resposta")),
        "Q7 - Justificativa": q7.get("justificativa") or "",
        "Q7 - Status": q7.get("status", ""),
    }


def montar_linha_agua(resultado):
    q1 = resultado.get("q1", {})
    q2 = resultado.get("q2", {})
    q3 = resultado.get("q3", {})
    q4 = resultado.get("q4", {})
    q5 = resultado.get("q5", {})
    q6 = resultado.get("q6", {})
    q7 = resultado.get("q7", {})
    return {
        "Código": resultado.get("codigo_aluno", ""),
        "Q1 - Alternativa": q1.get("alternativa", ""),
        "Q1 - Status": q1.get("status", ""),
        "Q2 - Representação": q2.get("representacao") or "",
        "Q2 - Status": q2.get("status", ""),
        "Q3 - Pontos considerados": formatar_lista(q3.get("pontos_considerados")),
        "Q3 - Somente resposta final": formatar_booleano(q3.get("somente_resposta_final")),
        "Q3 - Status": q3.get("status", ""),
        "Q4 - Testou ponto": formatar_booleano(q4.get("testou_ponto")),
        "Q4 - Explicação": q4.get("explicacao") or "",
        "Q4 - Status": q4.get("status", ""),
        "Q5 - Resposta": q5.get("resposta") or "",
        "Q5 - Status": q5.get("status", ""),
        "Q6 - Resposta": q6.get("resposta") or "",
        "Q6 - Status": q6.get("status", ""),
        "Q7 - Mudou resposta": formatar_booleano(q7.get("mudou_resposta")),
        "Q7 - Justificativa": q7.get("justificativa") or "",
        "Q7 - Status": q7.get("status", ""),
    }


def montar_linha_sinais(resultado):
    q1 = resultado.get("q1", {})
    q2 = resultado.get("q2", {})
    q3 = resultado.get("q3", {})
    q4 = resultado.get("q4", {})
    q5 = resultado.get("q5", {})
    q6 = resultado.get("q6", {})
    return {
        "Código": resultado.get("codigo_aluno", ""),
        "Q1 - Sinal": q1.get("simbolo") or "",
        "Q1 - Justificativa": q1.get("justificativa") or "",
        "Q1 - Status": q1.get("status", ""),
        "Q2 - Texto": q2.get("texto") or "",
        "Q2 - Desenho": q2.get("desenho") or "",
        "Q2 - Status": q2.get("status", ""),
        "Q3 - Testou significado": formatar_booleano(q3.get("testou_significado")),
        "Q3 - Hipótese descartada": q3.get("hipotese_descartada") or "",
        "Q3 - Como percebeu": q3.get("como_percebeu") or "",
        "Q3 - Status": q3.get("status", ""),
        "Q4 - Resposta": q4.get("resposta") or "",
        "Q4 - Status": q4.get("status", ""),
        "Q5 - Resposta": q5.get("resposta") or "",
        "Q5 - Status": q5.get("status", ""),
        "Q6 - Resposta": q6.get("resposta") or "",
        "Q6 - Status": q6.get("status", ""),
    }


def montar_linha_dinheiro(resultado):
    q1 = resultado.get("q1", {})
    q2 = resultado.get("q2", {})
    q3 = resultado.get("q3", {})
    q4 = resultado.get("q4", {})
    q5 = resultado.get("q5", {})
    q6 = resultado.get("q6", {})
    q7 = resultado.get("q7", {})
    q8 = resultado.get("q8", {})
    return {
        "Código": resultado.get("codigo_aluno", ""),
        "Q1 - Alternativa": q1.get("alternativa") or "",
        "Q1 - Status": q1.get("status", ""),
        "Q2 - Combinações testadas": formatar_lista(q2.get("combinacoes_testadas")),
        "Q2 - Status": q2.get("status", ""),
        "Q3 - Comparação das cédulas": q3.get("comparacao") or "",
        "Q3 - Status": q3.get("status", ""),
        "Q4 - Testou combinação": formatar_booleano(q4.get("testou_combinacao")),
        "Q4 - Combinação ou explicação": q4.get("combinacao_ou_explicacao") or "",
        "Q4 - Status": q4.get("status", ""),
        "Q5 - Resposta": q5.get("resposta") or "",
        "Q5 - Status": q5.get("status", ""),
        "Q6 - Resposta": q6.get("resposta") or "",
        "Q6 - Status": q6.get("status", ""),
        "Q7 - Resposta": q7.get("resposta") or "",
        "Q7 - Status": q7.get("status", ""),
        "Q8 - Mudou resposta/estratégia": formatar_booleano(q8.get("mudou_resposta_ou_estrategia")),
        "Q8 - Justificativa": q8.get("justificativa") or "",
        "Q8 - Status": q8.get("status", ""),
    }


def formatar_dados_revisao(dados):
    partes = []
    for campo, valor in dados.items():
        if campo == "status":
            continue
        if valor is None:
            continue
        if isinstance(valor, bool):
            valor = formatar_booleano(valor)
        elif isinstance(valor, list):
            valor = formatar_lista(valor)
        partes.append(f"{campo}: {valor}")
    return " | ".join(partes)


def gerar_linhas_revisao(resultado, nome_atividade):
    linhas = []
    fontes = resultado.get("_fontes", {})

    def imagem(tipo):
        fonte = fontes.get(tipo, {})
        return fonte.get("drive") or (
            Path(fonte["local"]).resolve().as_uri() if fonte.get("local") else ""
        )

    for numero in range(1, 9):
        chave = f"q{numero}"
        dados = resultado.get(chave)
        if not isinstance(dados, dict):
            continue
        status = dados.get("status")
        if status not in ["revisar", "ilegivel"]:
            continue
        linhas.append(
            {
                "Código": resultado.get("codigo_aluno", ""),
                "Atividade": nome_atividade,
                "Questão": f"Q{numero}",
                "Status": status,
                "Motivo": resultado.get("_motivos_revisao", {}).get(chave)
                or (
                    "Conteúdo ilegível na extração; conferir a imagem."
                    if status == "ilegivel"
                    else "Ambiguidade sinalizada na extração; conferir a imagem."
                ),
                "Abrir questão": imagem("questao"),
                "Abrir resposta": imagem("resposta"),
                "Dados extraídos": formatar_dados_revisao(dados),
                "Arquivo questão": resultado.get("arquivo_questao", ""),
                "Arquivo resposta": resultado.get("arquivo_resposta", ""),
            }
        )
    for tipo, paginas in resultado.get("_qualidade_imagens", {}).items():
        for pagina in paginas:
            defeitos = [
                defeito["tipo"]
                for defeito in pagina.get("defeitos", [])
                if defeito.get("confianca", 0) >= 0.5
            ]
            if defeitos:
                linhas.append(
                    {
                        "Código": resultado.get("codigo_aluno", ""),
                        "Atividade": nome_atividade,
                        "Questão": "Imagem " + tipo,
                        "Status": "revisar",
                        "Motivo": "Indicadores de qualidade da imagem: " + ", ".join(defeitos),
                        "Dados extraídos": f"Qualidade global: {pagina.get('qualidade')}",
                        "Abrir questão": imagem("questao"),
                        "Abrir resposta": imagem("resposta"),
                        "Arquivo questão": resultado.get("arquivo_questao", ""),
                        "Arquivo resposta": resultado.get("arquivo_resposta", ""),
                    }
                )
    for aviso in resultado.get("_avisos_entrada", []):
        linhas.append(
            {
                "Código": resultado.get("codigo_aluno", ""),
                "Atividade": nome_atividade,
                "Questão": "Imagem",
                "Status": "revisar",
                "Motivo": aviso,
                "Dados extraídos": "",
                "Abrir questão": imagem("questao"),
                "Abrir resposta": imagem("resposta"),
                "Arquivo questão": resultado.get("arquivo_questao", ""),
                "Arquivo resposta": resultado.get("arquivo_resposta", ""),
            }
        )
    return linhas


def _escrever_planilha(resultados, caminho, relatorio=None):
    import pandas as pd

    atividades = (
        ("chaves_do_cofre", "Chaves do Cofre", "As chaves do cofre", montar_linha_chaves),
        ("agua_para_todos", "Água para Todos", "Água para Todos", montar_linha_agua),
        ("sinais_de_transito", "Sinais de Trânsito", "Sinais de Trânsito", montar_linha_sinais),
        ("dinheiro_de_castor", "Dinheiro de Castor", "Dinheiro de Castor", montar_linha_dinheiro),
    )
    revisoes = []
    with pd.ExcelWriter(caminho, engine="openpyxl", mode="w") as writer:
        for codigo, aba, nome, montar in atividades:
            registros = resultados.get(codigo, [])
            linhas = [montar(registro) for registro in registros]
            pd.DataFrame(linhas, columns=list(montar({}))).to_excel(
                writer, sheet_name=aba, index=False, freeze_panes=(1, 1)
            )
            for registro in registros:
                revisoes.extend(gerar_linhas_revisao(registro, nome))
        pd.DataFrame(revisoes, columns=COLUNAS_REVISAO).to_excel(
            writer, sheet_name="Revisar", index=False, freeze_panes=(1, 0)
        )
        for coluna in ("Abrir questão", "Abrir resposta"):
            indice = COLUNAS_REVISAO.index(coluna) + 1
            for numero in range(2, len(revisoes) + 2):
                celula = writer.book["Revisar"].cell(numero, indice)
                if celula.value:
                    celula.hyperlink = celula.value
                    celula.value = "Abrir imagem"
                    celula.style = "Hyperlink"
        if relatorio:
            pd.DataFrame(
                [{"Estado da execução": relatorio["estado"], **relatorio.get("resumo", {})}]
            ).to_excel(writer, sheet_name="Execução", index=False)
            erros = [
                {
                    "Atividade": item["atividade"],
                    "Código": item["codigo"],
                    "Estado": item["estado"],
                    "Etapa": item.get("etapa", ""),
                    "Motivo": item.get("erro", {}).get("tipo", "")
                    or "; ".join(item.get("erros_validacao", [])),
                }
                for item in relatorio["registros"]
                if item["estado"] not in {"processado", "reaproveitado"}
            ]
            if erros:
                pd.DataFrame(erros).to_excel(writer, sheet_name="Erros", index=False)
        for folha in writer.book.worksheets:
            for linha in folha.iter_rows():
                for celula in linha:
                    if celula.data_type == "f":
                        celula.data_type = "s"


def filtrar_revisoes(resultados, max_revisar=1):
    """Filtra por registro e atividade, contando apenas status de Q1 a Q8."""
    if type(max_revisar) is not int or not 0 <= max_revisar <= 8:
        raise ValueError("O limite de questões revisar deve estar entre 0 e 8.")
    filtrados, excluidos, totais = {}, [], {}
    for atividade, registros in resultados.items():
        filtrados[atividade] = []
        for registro in registros:
            quantidade = sum(
                isinstance(registro.get(f"q{i}"), dict)
                and registro[f"q{i}"].get("status") == "revisar"
                for i in range(1, 9)
            )
            if quantidade > max_revisar:
                excluidos.append(
                    {
                        "atividade": atividade,
                        "codigo": registro.get("codigo_aluno", ""),
                        "questoes_revisar": quantidade,
                    }
                )
            else:
                filtrados[atividade].append(registro)
        totais[atividade] = {
            "recebidos": len(registros),
            "exportados": len(filtrados[atividade]),
            "excluidos": len(registros) - len(filtrados[atividade]),
        }
    return filtrados, {
        "criado_em": agora(),
        "max_revisar_por_registro": max_revisar,
        "criterio": "Exclui o registro da atividade quando mais que o limite de Q1 a Q8 têm status revisar. Não altera os JSONs ou os status da extração.",
        "exportados": sum(len(registros) for registros in filtrados.values()),
        "total_excluidos": len(excluidos),
        "por_atividade": totais,
        "excluidos": excluidos,
    }


def gerar_planilha(resultados, destino="resultados", relatorio=None, max_revisar=1):
    """Publica apenas um Excel completo; uma falha preserva o arquivo anterior."""
    pasta = Path(destino)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "resultado_turma.xlsx"
    filtrados, exportacao = filtrar_revisoes(resultados, max_revisar)
    if relatorio is not None:
        relatorio = {
            **relatorio,
            "resumo": {
                **relatorio.get("resumo", {}),
                "exportados": exportacao["exportados"],
                "excluidos_por_revisao": exportacao["total_excluidos"],
            },
        }
    with tempfile.TemporaryDirectory(prefix=".planilha-", dir=str(pasta)) as temporario:
        candidato = Path(temporario) / arquivo.name
        _escrever_planilha(filtrados, candidato, relatorio)
        exportacao["sha256_planilha"] = hash_arquivo(candidato)
        diagnostico = Path(temporario) / "relatorio_exportacao.json"
        salvar_atomico(diagnostico, exportacao)
        os.replace(candidato, arquivo)
        os.replace(diagnostico, pasta / diagnostico.name)
    print(f"Planilha salva: {arquivo}")
    print(
        f"  {exportacao['exportados']} registros exportados; {exportacao['total_excluidos']} excluídos pelo limite de revisão."
    )
    return arquivo
