import os
import json
import time
import pandas as pd

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HttpOptions,
    Part,
)

# =========================
# CONFIGURAÇÕES
# =========================

PROJECT_ID = "project-5e3bf1fd-47b5-442e-90d"
DOCUMENT_AI_LOCATION = "us"
PROCESSOR_ID = "15f792d10b41ff08"

VERTEX_LOCATION = "global"

PASTA_ENTRADA = "entrada"
PASTA_RESULTADOS = "resultados"

# =========================
# CLIENTE DOCUMENT AI
# =========================

document_ai_client = documentai.DocumentProcessorServiceClient(
    client_options=ClientOptions(
        api_endpoint=f"{DOCUMENT_AI_LOCATION}-documentai.googleapis.com"
    )
)

processor_name = document_ai_client.processor_path(
    PROJECT_ID,
    DOCUMENT_AI_LOCATION,
    PROCESSOR_ID
)

# =========================
# CLIENTE GEMINI
# =========================

gemini_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=VERTEX_LOCATION,
    http_options=HttpOptions(api_version="v1"),
)

# =========================
# SCHEMA DO RESULTADO
# =========================

schema = {
    "type": "OBJECT",
    "properties": {
        "atividade": {
            "type": "STRING"
        },

        "nome_estudante": {
            "type": "STRING",
            "nullable": True
        },

        "ano": {
            "type": "STRING",
            "nullable": True
        },

        "q1": {
            "type": "OBJECT",
            "properties": {
                "alternativa": {
                    "type": "STRING",
                    "enum": ["A", "B", "C", "D"],
                    "nullable": True
                },
                "status": {
                    "type": "STRING",
                    "enum": ["ok", "revisar", "ilegivel"]
                }
            },
            "required": ["alternativa", "status"]
        },

        "q2": {
            "type": "OBJECT",
            "properties": {
                "sequencia": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    },
                    "nullable": True
                },
                "observacao": {
                    "type": "STRING",
                    "nullable": True
                },
                "status": {
                    "type": "STRING",
                    "enum": ["ok", "revisar", "ilegivel"]
                }
            },
            "required": [
                "sequencia",
                "observacao",
                "status"
            ]
        },

        "q3": {
            "type": "OBJECT",
            "properties": {
                "resposta": {
                    "type": "STRING",
                    "nullable": True
                },
                "status": {
                    "type": "STRING",
                    "enum": ["ok", "revisar", "ilegivel"]
                }
            },
            "required": ["resposta", "status"]
        },

        "q4": {
            "type": "OBJECT",
            "properties": {
                "testou_caminho": {
                    "type": "BOOLEAN",
                    "nullable": True
                },
                "representacao": {
                    "type": "STRING",
                    "nullable": True
                },
                "status": {
                    "type": "STRING",
                    "enum": ["ok", "revisar", "ilegivel"]
                }
            },
            "required": [
                "testou_caminho",
                "representacao",
                "status"
            ]
        },

        "q5": {
            "type": "OBJECT",
            "properties": {
                "resposta": {
                    "type": "STRING",
                    "nullable": True
                },
                "status": {
                    "type": "STRING",
                    "enum": ["ok", "revisar", "ilegivel"]
                }
            },
            "required": ["resposta", "status"]
        },

        "q6": {
            "type": "OBJECT",
            "properties": {
                "resposta": {
                    "type": "STRING",
                    "nullable": True
                },
                "status": {
                    "type": "STRING",
                    "enum": ["ok", "revisar", "ilegivel"]
                }
            },
            "required": ["resposta", "status"]
        },

        "q7": {
            "type": "OBJECT",
            "properties": {
                "mudou_resposta": {
                    "type": "BOOLEAN",
                    "nullable": True
                },
                "justificativa": {
                    "type": "STRING",
                    "nullable": True
                },
                "status": {
                    "type": "STRING",
                    "enum": ["ok", "revisar", "ilegivel"]
                }
            },
            "required": [
                "mudou_resposta",
                "justificativa",
                "status"
            ]
        }
    },

    "required": [
        "atividade",
        "nome_estudante",
        "ano",
        "q1",
        "q2",
        "q3",
        "q4",
        "q5",
        "q6",
        "q7"
    ]
}

# =========================
# PROMPT
# =========================

def montar_prompt(texto_ocr):
    return f"""
Você está analisando uma folha de registro da atividade educacional
Bebras "As chaves do cofre".

Analise conjuntamente:
1. a imagem original;
2. o texto extraído pelo Document AI.

O OCR pode errar palavras, ordem das palavras, desenhos, marcações,
símbolos e alternativas assinaladas.

TEXTO OCR:

--- INÍCIO OCR ---
{texto_ocr}
--- FIM OCR ---

A folha possui:

1. Alternativa escolhida: A, B, C ou D.

2. Sequência de objetos utilizada.
A resposta pode conter desenhos, formas geométricas e setas.

3. Explicação de como o caminho foi encontrado.
Pode estar escrita, desenhada ou em branco.

4. Se o estudante testou algum caminho que não funcionou.
Opções: Sim ou Não.
Também pode haver um caminho desenhado.

5. Como verificou que era o menor número possível de gavetas.

6. Qual foi a parte mais difícil.

7. Se mudou sua resposta ou estratégia após conversar com um colega.
Opções: Sim ou Não.
Pode haver justificativa.

REGRAS:

- A imagem é a principal fonte para desenhos e marcações.
- O OCR é apenas apoio.
- Não invente informação.
- Não avalie se a resposta está correta.
- Preserve o sentido da resposta do estudante.
- Corrija erros óbvios do OCR somente quando a imagem confirmar claramente.
- Se estiver em branco, use null.
- Se não for possível determinar, use null.
- Não deduza a solução correta da atividade.

Para cada questão, informe também um status:

"ok":
a informação está claramente visível.

"revisar":
há uma interpretação provável, mas existe ambiguidade.

"ilegivel":
não é possível interpretar com segurança.

Uma questão em branco propositalmente pode ter resposta null e status "ok".

Retorne somente JSON.
"""


# =========================
# OCR
# =========================

def executar_ocr(caminho_imagem):

    extensao = os.path.splitext(caminho_imagem)[1].lower()

    if extensao in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif extensao == ".png":
        mime_type = "image/png"
    else:
        raise ValueError(
            f"Formato não suportado: {extensao}"
        )

    with open(caminho_imagem, "rb") as arquivo:
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

    return result.document.text, mime_type


# =========================
# GEMINI
# =========================

def interpretar_imagem(
    caminho_imagem,
    texto_ocr,
    mime_type
):

    with open(caminho_imagem, "rb") as arquivo:
        imagem = arquivo.read()

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",

        contents=[
            Part.from_bytes(
                data=imagem,
                mime_type=mime_type
            ),

            montar_prompt(texto_ocr)
        ],

        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0
        )
    )

    return json.loads(response.text)


# =========================
# TRANSFORMA JSON EM LINHA
# =========================

def transformar_em_linha(nome_arquivo, resultado):

    return {
        "arquivo": nome_arquivo,

        "nome_estudante":
            resultado.get("nome_estudante"),

        "ano":
            resultado.get("ano"),

        "q1_alternativa":
            resultado["q1"]["alternativa"],

        "q1_status":
            resultado["q1"]["status"],

        "q2_sequencia":
            " → ".join(
                resultado["q2"]["sequencia"]
            )
            if resultado["q2"]["sequencia"]
            else None,

        "q2_observacao":
            resultado["q2"]["observacao"],

        "q2_status":
            resultado["q2"]["status"],

        "q3_resposta":
            resultado["q3"]["resposta"],

        "q3_status":
            resultado["q3"]["status"],

        "q4_testou_caminho":
            resultado["q4"]["testou_caminho"],

        "q4_representacao":
            resultado["q4"]["representacao"],

        "q4_status":
            resultado["q4"]["status"],

        "q5_resposta":
            resultado["q5"]["resposta"],

        "q5_status":
            resultado["q5"]["status"],

        "q6_resposta":
            resultado["q6"]["resposta"],

        "q6_status":
            resultado["q6"]["status"],

        "q7_mudou_resposta":
            resultado["q7"]["mudou_resposta"],

        "q7_justificativa":
            resultado["q7"]["justificativa"],

        "q7_status":
            resultado["q7"]["status"]
    }


# =========================
# PROCESSAMENTO
# =========================

os.makedirs(PASTA_RESULTADOS, exist_ok=True)

arquivos = sorted(
    arquivo
    for arquivo in os.listdir(PASTA_ENTRADA)
    if arquivo.lower().endswith(
        (".jpg", ".jpeg", ".png")
    )
)

if not arquivos:
    print(
        "\nNenhuma imagem encontrada "
        "na pasta 'entrada'."
    )
    exit()

print(
    f"\n{len(arquivos)} arquivo(s) encontrado(s).\n"
)

linhas_planilha = []

for indice, nome_arquivo in enumerate(
    arquivos,
    start=1
):

    caminho = os.path.join(
        PASTA_ENTRADA,
        nome_arquivo
    )

    print(
        f"[{indice}/{len(arquivos)}] "
        f"Processando {nome_arquivo}..."
    )

    try:

        texto_ocr, mime_type = executar_ocr(
            caminho
        )

        resultado = interpretar_imagem(
            caminho,
            texto_ocr,
            mime_type
        )

        nome_base = os.path.splitext(
            nome_arquivo
        )[0]

        caminho_json = os.path.join(
            PASTA_RESULTADOS,
            f"{nome_base}.json"
        )

        with open(
            caminho_json,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                resultado,
                arquivo,
                ensure_ascii=False,
                indent=2
            )

        linhas_planilha.append(
            transformar_em_linha(
                nome_arquivo,
                resultado
            )
        )

        print("   ✓ concluído")

    except Exception as erro:

        print(
            f"   ✗ ERRO: {erro}"
        )

    # Evita disparar requisições uma atrás da outra
    time.sleep(1)


# =========================
# PLANILHA FINAL
# =========================

if linhas_planilha:

    df = pd.DataFrame(
        linhas_planilha
    )

    caminho_excel = os.path.join(
        PASTA_RESULTADOS,
        "resultado_turma.xlsx"
    )

    df.to_excel(
        caminho_excel,
        index=False
    )

    print(
        "\n=============================="
    )

    print(
        "PROCESSAMENTO FINALIZADO"
    )

    print(
        "=============================="
    )

    print(
        f"\nPlanilha: {caminho_excel}"
    )

    print(
        f"JSONs individuais: "
        f"{PASTA_RESULTADOS}/"
    )