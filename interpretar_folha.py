import json

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HttpOptions,
    Part,
)

PROJECT_ID = "project-5e3bf1fd-47b5-442e-90d"
LOCATION = "global"

IMAGE_PATH = "folha.jpg"
OCR_JSON_PATH = "resultado_document_ai.json"

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=HttpOptions(api_version="v1"),
)

# -----------------------------
# Lê o resultado do Document AI
# -----------------------------

with open(OCR_JSON_PATH, "r", encoding="utf-8") as arquivo:
    document_ai = json.load(arquivo)

texto_ocr = document_ai.get("text", "")

# -----------------------------
# Lê a imagem original
# -----------------------------

with open(IMAGE_PATH, "rb") as arquivo:
    imagem = arquivo.read()

# -----------------------------
# Prompt de interpretação
# -----------------------------

prompt = f"""
Você está analisando uma folha de registro de uma atividade educacional
do Bebras chamada "As chaves do cofre".

Sua função é TRANSCRITIVA E INTERPRETATIVA, não avaliativa.

Analise conjuntamente:
1. a imagem original da folha;
2. o texto extraído por OCR fornecido abaixo.

O OCR pode conter erros, palavras fora de ordem e interpretações incorretas
de desenhos, símbolos ou marcações manuscritas.

TEXTO OCR:

--- INÍCIO OCR ---
{texto_ocr}
--- FIM OCR ---

A folha possui as seguintes questões:

1. Qual alternativa você escolheu?
   Opções: A, B, C ou D.

2. Registre a sequência de objetos utilizada.
   A resposta pode ser composta principalmente por desenhos, símbolos
   e setas.

3. Explique como você encontrou esse caminho.
   A resposta pode ser texto, desenho, tabela, setas ou estar em branco.

4. Você testou algum caminho que não funcionou?
   Opções: Sim ou Não.
   Também pode existir uma representação desenhada do caminho tentado.

5. Como você verificou que esse era o menor número possível de gavetas?
   Transcreva a resposta manuscrita.

6. Qual foi a parte mais difícil da atividade?
   Transcreva a resposta manuscrita.

7. Depois de conversar com um colega, você mudou sua resposta ou estratégia?
   Opções: Sim ou Não.
   Também pode existir uma justificativa.

REGRAS IMPORTANTES:

- Observe a IMAGEM para interpretar X, círculos, marcações, desenhos,
  formas geométricas e setas.
- Use o OCR apenas como apoio.
- Não invente informações que não estejam visíveis.
- Não corrija pedagogicamente a resposta do estudante.
- Preserve o sentido original da escrita do estudante.
- Pode corrigir apenas erros óbvios do OCR quando a imagem deixar
  claramente visível o que foi escrito.
- Se uma informação não puder ser determinada com segurança, use null.
- Se uma questão estiver em branco, use null.
- Para desenhos, descreva apenas o que for visualmente identificável.
- Não tente "adivinhar" a solução correta da atividade.

Retorne somente um objeto JSON.
"""

# -----------------------------
# Estrutura esperada
# -----------------------------

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
                }
            },
            "required": ["alternativa"]
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
                }
            },
            "required": [
                "sequencia",
                "observacao"
            ]
        },

        "q3": {
            "type": "OBJECT",
            "properties": {
                "resposta": {
                    "type": "STRING",
                    "nullable": True
                }
            },
            "required": ["resposta"]
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
                }
            },
            "required": [
                "testou_caminho",
                "representacao"
            ]
        },

        "q5": {
            "type": "OBJECT",
            "properties": {
                "resposta": {
                    "type": "STRING",
                    "nullable": True
                }
            },
            "required": ["resposta"]
        },

        "q6": {
            "type": "OBJECT",
            "properties": {
                "resposta": {
                    "type": "STRING",
                    "nullable": True
                }
            },
            "required": ["resposta"]
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
                }
            },
            "required": [
                "mudou_resposta",
                "justificativa"
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

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        Part.from_bytes(
            data=imagem,
            mime_type="image/jpeg",
        ),
        prompt,
    ],
    config=GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0,
    ),
)

resultado = json.loads(response.text)

print("\n===== RESULTADO INTERPRETADO =====\n")
print(
    json.dumps(
        resultado,
        ensure_ascii=False,
        indent=2,
    )
)

with open(
    "resultado_interpretado.json",
    "w",
    encoding="utf-8",
) as arquivo:
    json.dump(
        resultado,
        arquivo,
        ensure_ascii=False,
        indent=2,
    )

print("\nSalvo em resultado_interpretado.json")