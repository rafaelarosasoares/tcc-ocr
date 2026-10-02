import os
import json
import time
import hashlib
import re

from datetime import datetime

import pandas as pd

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HttpOptions,
    Part,
)

from configuracoes import CONFIGURACOES


# =========================================================
# CONFIGURAÇÕES
# =========================================================

PROJECT_ID = "project-5e3bf1fd-47b5-442e-90d"

DOCUMENT_AI_LOCATION = "us"
PROCESSOR_ID = "15f792d10b41ff08"

VERTEX_LOCATION = "global"

MODELO_GEMINI = "gemini-2.5-flash"

PASTA_ENTRADA = "entrada"
PASTA_RESULTADOS = "resultados"

# Se alterarmos significativamente o prompt ou a forma
# de interpretar as atividades, basta trocar a versão.
# Isso fará os alunos serem processados novamente.
VERSAO_PROCESSAMENTO = "2.1"

# True = reprocessa tudo, independentemente dos hashes.
# False = só reprocessa quando a imagem mudou ou
#         quando a versão do processamento mudou.
FORCAR_REPROCESSAMENTO = False


# =========================================================
# DOCUMENT AI
# =========================================================

document_ai_client = documentai.DocumentProcessorServiceClient(
    client_options=ClientOptions(
        api_endpoint=(
            f"{DOCUMENT_AI_LOCATION}-documentai.googleapis.com"
        )
    )
)

processor_name = document_ai_client.processor_path(
    PROJECT_ID,
    DOCUMENT_AI_LOCATION,
    PROCESSOR_ID
)


# =========================================================
# GEMINI
# =========================================================

gemini_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=VERTEX_LOCATION,
    http_options=HttpOptions(
        api_version="v1"
    ),
)


# =========================================================
# UTILIDADES
# =========================================================

def descobrir_mime_type(caminho):

    extensao = os.path.splitext(caminho)[1].lower()

    if extensao in [".jpg", ".jpeg"]:
        return "image/jpeg"

    if extensao == ".png":
        return "image/png"

    raise ValueError(
        f"Formato não suportado: {extensao}"
    )


def calcular_hash_arquivo(caminho):

    sha256 = hashlib.sha256()

    with open(caminho, "rb") as arquivo:

        while True:

            bloco = arquivo.read(1024 * 1024)

            if not bloco:
                break

            sha256.update(bloco)

    return sha256.hexdigest()


def formatar_booleano(valor):

    if valor is True:
        return "Sim"

    if valor is False:
        return "Não"

    return ""


def formatar_lista(valor, separador=", "):

    if not valor:
        return ""

    return separador.join(
        str(item)
        for item in valor
    )

# =========================================================
# NORMALIZAÇÃO DOS RESULTADOS
# =========================================================

TERMOS_INCERTEZA = [
    "possivelmente",
    "provavelmente",
    "parece",
    "parecendo",
    "aparenta",
    "aparentemente",
    "talvez",
    "incerto",
    "incerta",
    "não está claro",
    "não é claro",
    "não claramente",
    "não foi possível identificar",
    "difícil identificar"
]


def normalizar_ano(valor):

    if valor is None:
        return ""

    texto = str(valor).strip()

    if not texto:
        return ""

    numeros = re.findall(r"\d+", texto)

    if numeros:
        return f"{numeros[0]}º"

    return texto


def contem_incerteza(valor):

    if valor is None:
        return False

    if isinstance(valor, str):

        texto = valor.lower()

        return any(
            termo in texto
            for termo in TERMOS_INCERTEZA
        )

    if isinstance(valor, list):

        return any(
            contem_incerteza(item)
            for item in valor
        )

    if isinstance(valor, dict):

        return any(
            contem_incerteza(conteudo)
            for chave, conteudo in valor.items()
            if chave != "status"
        )

    return False


def normalizar_resultado(resultado):

    # -----------------------------------------
    # Nome
    # -----------------------------------------

    nome = resultado.get(
        "nome_estudante"
    )

    if isinstance(nome, str):
        nome = nome.strip()

        if not nome:
            nome = None

    resultado[
        "nome_estudante"
    ] = nome

    nome_status = resultado.get(
        "nome_status"
    )

    # Segurança adicional:
    # se não existe nome, nunca deixar como "ok".
    if not nome:

        if nome_status == "ok":
            resultado[
                "nome_status"
            ] = "ausente"

        elif not nome_status:
            resultado[
                "nome_status"
            ] = "ausente"

    # -----------------------------------------
    # Ano
    # -----------------------------------------

    resultado["ano"] = normalizar_ano(
        resultado.get("ano")
    )

    # -----------------------------------------
    # Questões
    # -----------------------------------------

    for numero in range(1, 8):

        chave = f"q{numero}"

        dados = resultado.get(
            chave
        )

        if not isinstance(
            dados,
            dict
        ):
            continue

        # Se a própria descrição gerada pela IA
        # apresenta linguagem de incerteza,
        # não aceitamos status "ok".
        if (
            dados.get("status") == "ok"
            and contem_incerteza(dados)
        ):

            dados[
                "status"
            ] = "revisar"

    return resultado

# =========================================================
# OCR
# =========================================================

def executar_ocr(caminho_imagem):

    mime_type = descobrir_mime_type(
        caminho_imagem
    )

    with open(
        caminho_imagem,
        "rb"
    ) as arquivo:

        conteudo = arquivo.read()

    raw_document = documentai.RawDocument(
        content=conteudo,
        mime_type=mime_type
    )

    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=raw_document
    )

    result = document_ai_client.process_document(
        request=request
    )

    return result.document.text


def salvar_ocr(
    texto_ocr,
    pasta_saida,
    aluno
):

    pasta_ocr = os.path.join(
        pasta_saida,
        "ocr"
    )

    os.makedirs(
        pasta_ocr,
        exist_ok=True
    )

    caminho = os.path.join(
        pasta_ocr,
        f"{aluno}_ocr.txt"
    )

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            texto_ocr
        )


# =========================================================
# JSON
# =========================================================

def salvar_json(
    resultado,
    pasta_saida,
    aluno
):

    os.makedirs(
        pasta_saida,
        exist_ok=True
    )

    caminho = os.path.join(
        pasta_saida,
        f"{aluno}.json"
    )

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            resultado,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    return caminho


def carregar_json(caminho):

    with open(
        caminho,
        "r",
        encoding="utf-8"
    ) as arquivo:

        return json.load(
            arquivo
        )


# =========================================================
# VERIFICAR SE PRECISA REPROCESSAR
# =========================================================

def resultado_esta_atualizado(
    resultado,
    hashes_atuais
):

    if FORCAR_REPROCESSAMENTO:
        return False

    processamento = resultado.get(
        "_processamento"
    )

    if not processamento:
        # JSON criado pelas versões antigas.
        return False

    if (
        processamento.get("versao")
        != VERSAO_PROCESSAMENTO
    ):
        return False

    hashes_anteriores = processamento.get(
        "hashes_entrada"
    )

    if hashes_anteriores != hashes_atuais:
        return False

    return True


def adicionar_metadados(
    resultado,
    codigo_atividade,
    aluno,
    arquivos,
    hashes
):

    resultado["codigo_aluno"] = aluno

    resultado[
        "codigo_atividade"
    ] = codigo_atividade

    if "resposta" in arquivos:

        resultado[
            "arquivo_resposta"
        ] = arquivos["resposta"]

    if "questao" in arquivos:

        resultado[
            "arquivo_questao"
        ] = arquivos["questao"]

    resultado[
        "_processamento"
    ] = {
        "versao": VERSAO_PROCESSAMENTO,
        "modelo": MODELO_GEMINI,
        "processado_em": datetime.now().isoformat(
            timespec="seconds"
        ),
        "hashes_entrada": hashes
    }

    return resultado


# =========================================================
# PROMPT - CHAVES DO COFRE
# =========================================================

def montar_prompt_unico(
    texto_ocr,
    configuracao
):

    return f"""
Você está analisando uma folha de registro de um estudante
na atividade Bebras:

"{configuracao['nome']}"

A imagem contém elementos impressos da atividade
e respostas produzidas pelo estudante.

As respostas podem conter:

- texto manuscrito;
- alternativas marcadas;
- desenhos;
- setas;
- formas geométricas;
- sequências;
- riscos;
- outras representações.

O texto abaixo foi extraído pelo Google Document AI.

--- INÍCIO DO OCR ---

{texto_ocr}

--- FIM DO OCR ---

ESTRUTURA DA ATIVIDADE:

{configuracao["descricao"]}

REGRAS:

- Use a imagem como principal fonte.
- Use o OCR somente como apoio.
- Diferencie elementos impressos das respostas do estudante.
- Não invente informações.
- Não determine a resposta correta da atividade.
- Não avalie o desempenho do estudante.
- Não atribua habilidades de Pensamento Computacional.

IMPORTANTE SOBRE DESENHOS E MARCAÇÕES:

- Descreva apenas aquilo que é diretamente visível.
- Não atribua intenção ao estudante.
- Não explique por que o estudante fez determinada marcação,
  a menos que isso esteja explicitamente escrito por ele.
- Não transforme uma marcação visual em uma conclusão
  sobre o raciocínio do estudante.
- Não use expressões como "para verificar",
  "com o objetivo de", "indicando que" ou semelhantes
  para explicar a intenção do estudante,
  a menos que essas palavras tenham sido escritas pelo próprio estudante.

Exemplo:

CORRETO:
"Ponto 4 circulado. Há linhas traçadas entre o ponto 4
e outros nós."

INCORRETO:
"O estudante circulou o ponto 4 para verificar se todas
as vilas estavam a duas estradas."

STATUS DAS QUESTÕES:

Use "ok" SOMENTE quando a informação estiver
diretamente legível ou visualmente identificável
sem necessidade de interpretação incerta.

Use "revisar" quando:

- alguma parte estiver ambígua;
- existir mais de uma interpretação possível;
- uma forma ou símbolo não puder ser identificado
  com total segurança;
- apenas parte de uma sequência estiver clara;
- você sentir necessidade de usar palavras como
  "parece", "possivelmente", "provavelmente",
  "aparentemente" ou "talvez".

Se houver dúvida, prefira "revisar" em vez de "ok".

Use "ilegivel" quando houver conteúdo produzido
pelo estudante, mas não for possível interpretá-lo.

Uma resposta realmente em branco deve ser null.
Uma resposta em branco pode ter status "ok",
pois foi possível verificar que o campo está vazio.

NOME DO ESTUDANTE:

- Se estiver claramente legível:
  nome_status = "ok".
- Se houver uma leitura provável, mas com dúvida:
  registre a leitura provável e use nome_status = "revisar".
- Se houver um nome escrito mas não for possível lê-lo:
  nome_estudante = null e nome_status = "ilegivel".
- Se o campo estiver vazio:
  nome_estudante = null e nome_status = "ausente".

Preserve o sentido original das respostas.
Corrija erros do OCR somente quando a imagem
permitir confirmar claramente o conteúdo.

Retorne somente JSON.
"""


# =========================================================
# PROMPT - ÁGUA PARA TODOS
# =========================================================

def montar_prompt_par(
    texto_ocr,
    configuracao
):

    return f"""
Você está analisando o registro de um estudante
na atividade Bebras:

"{configuracao['nome']}"

Você recebeu DUAS imagens do mesmo estudante.

IMAGEM 1:
É a folha da questão/mapa.

Ela contém elementos originalmente impressos,
mas também pode conter anotações feitas pelo estudante,
como:

- caminhos;
- setas;
- riscos;
- círculos;
- números;
- símbolos;
- marcações;
- pequenas anotações.

Essas anotações fazem parte do processo
de resolução do estudante.

IMAGEM 2:
É a folha de registro/resposta.

O texto abaixo foi extraído pelo
Google Document AI da folha de resposta.

REGRAS:

- Use a imagem como principal fonte.
- Use o OCR somente como apoio.
- Diferencie elementos impressos das respostas do estudante.
- Não invente informações.
- Não determine a resposta correta da atividade.
- Não avalie o desempenho do estudante.
- Não atribua habilidades de Pensamento Computacional.

IMPORTANTE SOBRE DESENHOS E MARCAÇÕES:

- Descreva apenas aquilo que é diretamente visível.
- Não atribua intenção ao estudante.
- Não explique por que o estudante fez determinada marcação,
  a menos que isso esteja explicitamente escrito por ele.
- Não transforme uma marcação visual em uma conclusão
  sobre o raciocínio do estudante.
- Não use expressões como "para verificar",
  "com o objetivo de", "indicando que" ou semelhantes
  para explicar a intenção do estudante,
  a menos que essas palavras tenham sido escritas pelo próprio estudante.

Exemplo:

CORRETO:
"Ponto 4 circulado. Há linhas traçadas entre o ponto 4
e outros nós."

INCORRETO:
"O estudante circulou o ponto 4 para verificar se todas
as vilas estavam a duas estradas."

STATUS DAS QUESTÕES:

Use "ok" SOMENTE quando a informação estiver
diretamente legível ou visualmente identificável
sem necessidade de interpretação incerta.

Use "revisar" quando:

- alguma parte estiver ambígua;
- existir mais de uma interpretação possível;
- uma forma ou símbolo não puder ser identificado
  com total segurança;
- apenas parte de uma sequência estiver clara;
- você sentir necessidade de usar palavras como
  "parece", "possivelmente", "provavelmente",
  "aparentemente" ou "talvez".

Se houver dúvida, prefira "revisar" em vez de "ok".

Use "ilegivel" quando houver conteúdo produzido
pelo estudante, mas não for possível interpretá-lo.

Uma resposta realmente em branco deve ser null.
Uma resposta em branco pode ter status "ok",
pois foi possível verificar que o campo está vazio.

NOME DO ESTUDANTE:

- Se estiver claramente legível:
  nome_status = "ok".
- Se houver uma leitura provável, mas com dúvida:
  registre a leitura provável e use nome_status = "revisar".
- Se houver um nome escrito mas não for possível lê-lo:
  nome_estudante = null e nome_status = "ilegivel".
- Se o campo estiver vazio:
  nome_estudante = null e nome_status = "ausente".

Preserve o sentido original das respostas.
Corrija erros do OCR somente quando a imagem
permitir confirmar claramente o conteúdo.

Retorne somente JSON.

--- INÍCIO DO OCR ---

{texto_ocr}

--- FIM DO OCR ---

ESTRUTURA DA ATIVIDADE:

{configuracao["descricao"]}

REGRAS:

- Analise as duas imagens em conjunto.
- Use as imagens como principal fonte.
- Use o OCR somente como apoio textual.
- Considere as anotações feitas na folha da questão.
- Diferencie elementos impressos dos elementos
  acrescentados pelo estudante.
- Não invente informações.
- Não determine a resposta correta.
- Não avalie o estudante.
- Não atribua habilidades de Pensamento Computacional.
- Apenas transcreva e descreva aquilo que foi registrado.
- Preserve o sentido original das respostas.
- Uma resposta realmente em branco deve ser null.
- Não confunda resposta em branco com conteúdo ilegível.
- Se houver ambiguidade, use status "revisar".
- Se houver conteúdo ilegível, use status "ilegivel".
- Se estiver claro, use status "ok".
- Se um campo não puder ser determinado com segurança,
  retorne null e continue preenchendo os demais.

Retorne somente JSON.
"""


# =========================================================
# GEMINI - UMA IMAGEM
# =========================================================

def interpretar_imagem_unica(
    caminho_resposta,
    texto_ocr,
    configuracao
):

    mime_type = descobrir_mime_type(
        caminho_resposta
    )

    with open(
        caminho_resposta,
        "rb"
    ) as arquivo:

        imagem = arquivo.read()

    response = gemini_client.models.generate_content(
        model=MODELO_GEMINI,

        contents=[
            Part.from_bytes(
                data=imagem,
                mime_type=mime_type
            ),

            montar_prompt_unico(
                texto_ocr,
                configuracao
            )
        ],

        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=configuracao["schema"],
            temperature=0
        )
    )

    if not response.text:

        print(
            "\n===== RESPOSTA BRUTA DO GEMINI ====="
        )

        print(response)

        print(
            "====================================\n"
        )

        raise ValueError(
            "O Gemini não retornou conteúdo."
        )

    return json.loads(
        response.text
    )


# =========================================================
# GEMINI - DUAS IMAGENS
# =========================================================

def interpretar_par(
    caminho_questao,
    caminho_resposta,
    texto_ocr,
    configuracao
):

    mime_questao = descobrir_mime_type(
        caminho_questao
    )

    mime_resposta = descobrir_mime_type(
        caminho_resposta
    )

    with open(
        caminho_questao,
        "rb"
    ) as arquivo:

        imagem_questao = arquivo.read()

    with open(
        caminho_resposta,
        "rb"
    ) as arquivo:

        imagem_resposta = arquivo.read()

    response = gemini_client.models.generate_content(
        model=MODELO_GEMINI,

        contents=[
            "IMAGEM 1 - QUESTÃO/MAPA COM ANOTAÇÕES:",

            Part.from_bytes(
                data=imagem_questao,
                mime_type=mime_questao
            ),

            "IMAGEM 2 - FOLHA DE RESPOSTA:",

            Part.from_bytes(
                data=imagem_resposta,
                mime_type=mime_resposta
            ),

            montar_prompt_par(
                texto_ocr,
                configuracao
            )
        ],

        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=configuracao["schema"],
            temperature=0
        )
    )

    if not response.text:

        print(
            "\n===== RESPOSTA BRUTA DO GEMINI ====="
        )

        print(response)

        print(
            "====================================\n"
        )

        raise ValueError(
            "O Gemini não retornou conteúdo."
        )

    return json.loads(
        response.text
    )


# =========================================================
# ENCONTRAR ARQUIVOS
# =========================================================

def encontrar_imagens_unicas(
    pasta_atividade
):

    alunos = {}

    for nome in os.listdir(
        pasta_atividade
    ):

        nome_lower = nome.lower()

        if not nome_lower.endswith(
            (".jpg", ".jpeg", ".png")
        ):
            continue

        if "_resposta" not in nome_lower:
            continue

        indice = nome_lower.find(
            "_resposta"
        )

        aluno = nome[:indice]

        alunos[aluno] = {
            "resposta": nome
        }

    return alunos


def encontrar_pares(
    pasta_atividade
):

    alunos = {}

    for nome in os.listdir(
        pasta_atividade
    ):

        nome_lower = nome.lower()

        if not nome_lower.endswith(
            (".jpg", ".jpeg", ".png")
        ):
            continue

        if "_questao" in nome_lower:

            indice = nome_lower.find(
                "_questao"
            )

            aluno = nome[:indice]

            alunos.setdefault(
                aluno,
                {}
            )

            alunos[aluno][
                "questao"
            ] = nome

        elif "_resposta" in nome_lower:

            indice = nome_lower.find(
                "_resposta"
            )

            aluno = nome[:indice]

            alunos.setdefault(
                aluno,
                {}
            )

            alunos[aluno][
                "resposta"
            ] = nome

    return alunos


# =========================================================
# LINHA EXCEL - CHAVES DO COFRE
# =========================================================

def montar_linha_chaves(
    resultado
):

    q1 = resultado.get("q1", {})
    q2 = resultado.get("q2", {})
    q3 = resultado.get("q3", {})
    q4 = resultado.get("q4", {})
    q5 = resultado.get("q5", {})
    q6 = resultado.get("q6", {})
    q7 = resultado.get("q7", {})

    return {

        "Código": resultado.get(
            "codigo_aluno",
            ""
        ),

        "Nome": resultado.get(
            "nome_estudante",
            ""
        ),

        "Nome - Status": resultado.get(
            "nome_status",
            ""
        ),

        "Ano": resultado.get(
            "ano",
            ""
        ),

        "Q1 - Alternativa":
            q1.get("alternativa", ""),

        "Q1 - Status":
            q1.get("status", ""),

        "Q2 - Sequência":
            formatar_lista(
                q2.get("sequencia"),
                separador=" → "
            ),

        "Q2 - Observação":
            q2.get("observacao") or "",

        "Q2 - Status":
            q2.get("status", ""),

        "Q3 - Resposta":
            q3.get("resposta") or "",

        "Q3 - Status":
            q3.get("status", ""),

        "Q4 - Testou caminho":
            formatar_booleano(
                q4.get("testou_caminho")
            ),

        "Q4 - Representação":
            q4.get("representacao") or "",

        "Q4 - Status":
            q4.get("status", ""),

        "Q5 - Resposta":
            q5.get("resposta") or "",

        "Q5 - Status":
            q5.get("status", ""),

        "Q6 - Resposta":
            q6.get("resposta") or "",

        "Q6 - Status":
            q6.get("status", ""),

        "Q7 - Mudou resposta":
            formatar_booleano(
                q7.get("mudou_resposta")
            ),

        "Q7 - Justificativa":
            q7.get("justificativa") or "",

        "Q7 - Status":
            q7.get("status", ""),
    }


# =========================================================
# LINHA EXCEL - ÁGUA PARA TODOS
# =========================================================

def montar_linha_agua(
    resultado
):

    q1 = resultado.get("q1", {})
    q2 = resultado.get("q2", {})
    q3 = resultado.get("q3", {})
    q4 = resultado.get("q4", {})
    q5 = resultado.get("q5", {})
    q6 = resultado.get("q6", {})
    q7 = resultado.get("q7", {})

    return {

        "Código": resultado.get(
            "codigo_aluno",
            ""
        ),

        "Nome": resultado.get(
            "nome_estudante",
            ""
        ),

        "Nome - Status": resultado.get(
            "nome_status",
            ""
        ),

        "Ano": resultado.get(
            "ano",
            ""
        ),

        "Q1 - Alternativa":
            q1.get("alternativa", ""),

        "Q1 - Status":
            q1.get("status", ""),

        "Q2 - Representação":
            q2.get("representacao") or "",

        "Q2 - Status":
            q2.get("status", ""),

        "Q3 - Pontos considerados":
            formatar_lista(
                q3.get("pontos_considerados")
            ),

        "Q3 - Somente resposta final":
            formatar_booleano(
                q3.get("somente_resposta_final")
            ),

        "Q3 - Status":
            q3.get("status", ""),

        "Q4 - Testou ponto":
            formatar_booleano(
                q4.get("testou_ponto")
            ),

        "Q4 - Explicação":
            q4.get("explicacao") or "",

        "Q4 - Status":
            q4.get("status", ""),

        "Q5 - Resposta":
            q5.get("resposta") or "",

        "Q5 - Status":
            q5.get("status", ""),

        "Q6 - Resposta":
            q6.get("resposta") or "",

        "Q6 - Status":
            q6.get("status", ""),

        "Q7 - Mudou resposta":
            formatar_booleano(
                q7.get("mudou_resposta")
            ),

        "Q7 - Justificativa":
            q7.get("justificativa") or "",

        "Q7 - Status":
            q7.get("status", ""),
    }


# =========================================================
# ABA REVISAR
# =========================================================

def formatar_dados_revisao(
    dados
):

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

        partes.append(
            f"{campo}: {valor}"
        )

    return " | ".join(
        partes
    )


def gerar_linhas_revisao(
    resultado,
    nome_atividade
):

    linhas = []

    # =====================================================
    # IDENTIFICAÇÃO DO ESTUDANTE
    # =====================================================

    nome_status = resultado.get(
        "nome_status",
        ""
    )

    nome = resultado.get(
        "nome_estudante"
    )

    if (
        nome_status in [
            "revisar",
            "ilegivel",
            "ausente"
        ]
        or not nome
    ):

        if not nome_status:
            nome_status = "ausente"

        linhas.append(
            {
                "Código": resultado.get(
                    "codigo_aluno",
                    ""
                ),

                "Nome": nome or "",

                "Atividade": nome_atividade,

                "Questão": "Identificação",

                "Status": nome_status,

                "Dados extraídos": (
                    f"nome_estudante: {nome}"
                    if nome
                    else "Nome não identificado"
                ),

                "Arquivo questão":
                    resultado.get(
                        "arquivo_questao",
                        ""
                    ),

                "Arquivo resposta":
                    resultado.get(
                        "arquivo_resposta",
                        ""
                    ),
            }
        )

    # =====================================================
    # QUESTÕES
    # =====================================================

    for numero in range(
        1,
        8
    ):

        chave = f"q{numero}"

        dados = resultado.get(
            chave
        )

        if not isinstance(
            dados,
            dict
        ):
            continue

        status = dados.get(
            "status"
        )

        if status not in [
            "revisar",
            "ilegivel"
        ]:
            continue

        linhas.append(
            {
                "Código": resultado.get(
                    "codigo_aluno",
                    ""
                ),

                "Nome": nome or "",

                "Atividade": nome_atividade,

                "Questão": f"Q{numero}",

                "Status": status,

                "Dados extraídos":
                    formatar_dados_revisao(
                        dados
                    ),

                "Arquivo questão":
                    resultado.get(
                        "arquivo_questao",
                        ""
                    ),

                "Arquivo resposta":
                    resultado.get(
                        "arquivo_resposta",
                        ""
                    ),
            }
        )

    return linhas

# =========================================================
# PROCESSAMENTO DE UMA ATIVIDADE
# =========================================================

def processar_atividade(
    codigo_atividade,
    configuracao
):

    pasta_atividade = os.path.join(
        PASTA_ENTRADA,
        codigo_atividade
    )

    if not os.path.isdir(
        pasta_atividade
    ):

        print(
            f"\nPasta não encontrada: "
            f"{pasta_atividade}"
        )

        return []

    pasta_saida = os.path.join(
        PASTA_RESULTADOS,
        codigo_atividade
    )

    os.makedirs(
        pasta_saida,
        exist_ok=True
    )

    modo = configuracao[
        "modo_entrada"
    ]

    if modo == "unica_imagem":

        alunos = encontrar_imagens_unicas(
            pasta_atividade
        )

    elif modo == "questao_resposta":

        alunos = encontrar_pares(
            pasta_atividade
        )

    else:

        print(
            f"Modo desconhecido: {modo}"
        )

        return []

    resultados = []

    print()
    print("=" * 60)
    print(
        f"ATIVIDADE: "
        f"{configuracao['nome']}"
    )
    print("=" * 60)

    total = len(
        alunos
    )

    for indice, (
        aluno,
        arquivos
    ) in enumerate(
        sorted(
            alunos.items()
        ),
        start=1
    ):

        print()
        print(
            f"[{indice}/{total}] "
            f"Processando {aluno}..."
        )

        if "resposta" not in arquivos:

            print(
                "   ✗ resposta ausente"
            )

            continue

        if (
            modo == "questao_resposta"
            and "questao" not in arquivos
        ):

            print(
                "   ✗ imagem da questão ausente"
            )

            continue

        caminho_resposta = os.path.join(
            pasta_atividade,
            arquivos["resposta"]
        )

        caminhos = {
            "resposta": caminho_resposta
        }

        if "questao" in arquivos:

            caminhos[
                "questao"
            ] = os.path.join(
                pasta_atividade,
                arquivos["questao"]
            )

        hashes_atuais = {
            tipo: calcular_hash_arquivo(
                caminho
            )
            for tipo, caminho in caminhos.items()
        }

        caminho_json = os.path.join(
            pasta_saida,
            f"{aluno}.json"
        )

        resultado_existente = None

        if os.path.exists(
            caminho_json
        ):

            try:

                resultado_existente = carregar_json(
                    caminho_json
                )

            except Exception:

                resultado_existente = None

        # -------------------------------------------------
        # PODE REUTILIZAR JSON?
        # -------------------------------------------------

        if (
            resultado_existente
            and resultado_esta_atualizado(
                resultado_existente,
                hashes_atuais
            )
        ):

            print(
                "   → imagens não mudaram; "
                "usando JSON existente"
            )

            resultados.append(
                resultado_existente
            )

            continue

        # -------------------------------------------------
        # PRECISA PROCESSAR
        # -------------------------------------------------

        
        try:

            if resultado_existente:

                print(
                    "   → alteração detectada; "
                    "reprocessando"
                )

            else:

                print(
                    "   → novo registro"
                )

            # ---------------------------------------------
            # OCR
            # ---------------------------------------------

            print(
                "   → executando OCR..."
            )

            texto_ocr = executar_ocr(
                caminho_resposta
            )

            salvar_ocr(
                texto_ocr,
                pasta_saida,
                aluno
            )

            print(
                "   ✓ OCR concluído"
            )

            # ---------------------------------------------
            # GEMINI
            # ---------------------------------------------

            if modo == "unica_imagem":

                print(
                    "   → enviando ao Gemini..."
                )

                resultado = interpretar_imagem_unica(
                    caminho_resposta,
                    texto_ocr,
                    configuracao
                )

            else:

                print(
                    "   → enviando as duas imagens "
                    "ao Gemini..."
                )

                resultado = interpretar_par(
                    caminhos["questao"],
                    caminho_resposta,
                    texto_ocr,
                    configuracao
                )

            # ---------------------------------------------
            # NORMALIZAÇÃO
            # ---------------------------------------------

            resultado = normalizar_resultado(
                resultado
            )

            # ---------------------------------------------
            # METADADOS DO PROCESSAMENTO
            # ---------------------------------------------

            resultado = adicionar_metadados(
                resultado,
                codigo_atividade,
                aluno,
                arquivos,
                hashes_atuais
            )

            # ---------------------------------------------
            # SALVAR JSON
            # ---------------------------------------------

            salvar_json(
                resultado,
                pasta_saida,
                aluno
            )

            resultados.append(
                resultado
            )

            print(
                "   ✓ JSON atualizado"
            )

            time.sleep(1)

        except Exception as erro:

            print(
                f"   ✗ ERRO: {erro}"
            )

    return resultados


# =========================================================
# GERAR PLANILHA
# =========================================================

def gerar_planilha(
    resultados_por_atividade
):

    caminho_excel = os.path.join(
        PASTA_RESULTADOS,
        "resultado_turma.xlsx"
    )

    linhas_chaves = []
    linhas_agua = []
    linhas_revisao = []

    # -----------------------------------------------------
    # CHAVES DO COFRE
    # -----------------------------------------------------

    for resultado in resultados_por_atividade.get(
        "chaves_do_cofre",
        []
    ):

        linhas_chaves.append(
            montar_linha_chaves(
                resultado
            )
        )

        linhas_revisao.extend(
            gerar_linhas_revisao(
                resultado,
                "As chaves do cofre"
            )
        )

    # -----------------------------------------------------
    # ÁGUA PARA TODOS
    # -----------------------------------------------------

    for resultado in resultados_por_atividade.get(
        "agua_para_todos",
        []
    ):

        linhas_agua.append(
            montar_linha_agua(
                resultado
            )
        )

        linhas_revisao.extend(
            gerar_linhas_revisao(
                resultado,
                "Água para Todos"
            )
        )

    # -----------------------------------------------------
    # RECRIA COMPLETAMENTE O ARQUIVO
    # -----------------------------------------------------

    with pd.ExcelWriter(
        caminho_excel,
        engine="openpyxl",
        mode="w"
    ) as writer:

        df_chaves = pd.DataFrame(
            linhas_chaves
        )

        df_agua = pd.DataFrame(
            linhas_agua
        )

        df_revisao = pd.DataFrame(
            linhas_revisao,
            columns=[
                "Código",
                "Nome",
                "Atividade",
                "Questão",
                "Status",
                "Dados extraídos",
                "Arquivo questão",
                "Arquivo resposta"
            ]
        )

        df_chaves.to_excel(
            writer,
            sheet_name="Chaves do Cofre",
            index=False,
            freeze_panes=(1, 3)
        )

        df_agua.to_excel(
            writer,
            sheet_name="Água para Todos",
            index=False,
            freeze_panes=(1, 3)
        )

        df_revisao.to_excel(
            writer,
            sheet_name="Revisar",
            index=False,
            freeze_panes=(1, 0)
        )

    print()
    print(
        "✓ Planilha recriada:"
    )

    print(
        f"  {caminho_excel}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    os.makedirs(
        PASTA_ENTRADA,
        exist_ok=True
    )

    os.makedirs(
        PASTA_RESULTADOS,
        exist_ok=True
    )

    print()
    print(
        "=============================================="
    )
    print(
        "PROCESSAMENTO DAS ATIVIDADES BEBRAS"
    )
    print(
        "=============================================="
    )

    resultados_por_atividade = {}

    for (
        codigo_atividade,
        configuracao
    ) in CONFIGURACOES.items():

        resultados = processar_atividade(
            codigo_atividade,
            configuracao
        )

        resultados_por_atividade[
            codigo_atividade
        ] = resultados

    gerar_planilha(
        resultados_por_atividade
    )

    print()
    print(
        "=============================================="
    )
    print(
        "PROCESSAMENTO FINALIZADO"
    )
    print(
        "=============================================="
    )


if __name__ == "__main__":
    main()