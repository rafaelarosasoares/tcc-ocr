CONFIGURACOES = {

    "chaves_do_cofre": {
        "nome": "As chaves do cofre",
        "modo_entrada": "unica_imagem",

        "descricao": """
1. Qual alternativa você escolheu?
Opções: A, B, C ou D.

2. Registre a sequência de objetos utilizada.
Pode conter desenhos, formas geométricas e setas.

3. Explique como você encontrou esse caminho.
Pode conter texto, desenhos, setas ou estar em branco.

4. Você testou algum caminho que não funcionou?
Opções: Sim ou Não.
Pode existir uma representação desenhada.

5. Como você verificou que esse era o menor número possível de gavetas?
Resposta aberta.

6. Qual foi a parte mais difícil da atividade?
Resposta aberta.

7. Depois de conversar com um colega, você mudou sua resposta ou estratégia?
Opções: Sim ou Não.
Pode conter justificativa.
""",

        "schema": {
            "type": "OBJECT",
            "properties": {

                "atividade": {
                    "type": "STRING"
                },

                "nome_estudante": {
                    "type": "STRING",
                    "nullable": True
                },

                "nome_status": {
                    "type": "STRING",
                    "enum": [
                        "ok",
                        "revisar",
                        "ilegivel",
                        "ausente"
                    ]
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
                "nome_status",
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
    },

    "agua_para_todos": {
        "nome": "Água para Todos",
        "modo_entrada": "questao_resposta",

        "descricao": """
1. Qual alternativa você escolheu?
Opções: A, B, C ou D.

2. Mostre como você analisou os caminhos do mapa para chegar à resposta.
Pode conter desenhos, marcações, setas, texto ou símbolos.

3. Quais pontos você chegou a considerar antes de escolher a resposta final?
Podem ser marcados os pontos 1, 2, 3 e 4.
Também pode ser marcada a opção indicando que apenas a resposta final foi considerada.

4. Você testou algum ponto que não funcionou?
Opções: Sim ou Não.
Pode haver explicação ou representação do ponto testado.

5. Como você verificou que, com o ponto escolhido, todas as vilas ficam
a no máximo duas estradas de um centro de distribuição?
Pode conter texto, desenhos ou marcações.

6. Qual foi a parte mais difícil da atividade?
Resposta aberta.

7. Depois de conversar com um colega, você mudou sua resposta ou estratégia?
Opções: Sim ou Não.
Pode conter justificativa.
""",

        "schema": {
            "type": "OBJECT",
            "properties": {

                "atividade": {
                    "type": "STRING"
                },

                "nome_estudante": {
                    "type": "STRING",
                    "nullable": True
                },

                "nome_status": {
                    "type": "STRING",
                    "enum": [
                        "ok",
                        "revisar",
                        "ilegivel",
                        "ausente"
                    ]
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
                        "representacao",
                        "status"
                    ]
                },

                "q3": {
                    "type": "OBJECT",
                    "properties": {

                        "pontos_considerados": {
                            "type": "ARRAY",
                            "items": {
                                "type": "INTEGER"
                            },
                            "nullable": True
                        },

                        "somente_resposta_final": {
                            "type": "BOOLEAN",
                            "nullable": True
                        },

                        "status": {
                            "type": "STRING",
                            "enum": ["ok", "revisar", "ilegivel"]
                        }
                    },

                    "required": [
                        "pontos_considerados",
                        "somente_resposta_final",
                        "status"
                    ]
                },

                "q4": {
                    "type": "OBJECT",
                    "properties": {

                        "testou_ponto": {
                            "type": "BOOLEAN",
                            "nullable": True
                        },

                        "explicacao": {
                            "type": "STRING",
                            "nullable": True
                        },

                        "status": {
                            "type": "STRING",
                            "enum": ["ok", "revisar", "ilegivel"]
                        }
                    },

                    "required": [
                        "testou_ponto",
                        "explicacao",
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
                    "required": [
                        "resposta",
                        "status"
                    ]
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
                    "required": [
                        "resposta",
                        "status"
                    ]
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
                "nome_status",
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
    }
}