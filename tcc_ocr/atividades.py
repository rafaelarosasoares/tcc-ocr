"""Atividades e contratos de extração com definições compartilhadas de campos."""


def _campo(tipo, **opcoes):
    return {"type": tipo, "nullable": True, **opcoes}


def _questao(**campos):
    propriedades = {**campos, "status": {"type": "STRING", "enum": ["ok", "revisar", "ilegivel"]}}
    return {"type": "OBJECT", "properties": propriedades, "required": list(propriedades)}


def _schema(**questoes):
    propriedades = {"atividade": {"type": "STRING"}, **questoes}
    return {"type": "OBJECT", "properties": propriedades, "required": list(propriedades)}


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
        "schema": _schema(
            q1=_questao(
                alternativa=_campo("STRING", enum=["A", "B", "C", "D"]),
            ),
            q2=_questao(
                sequencia=_campo("ARRAY", items={"type": "STRING"}),
                observacao=_campo("STRING"),
            ),
            q3=_questao(
                resposta=_campo("STRING"),
            ),
            q4=_questao(
                testou_caminho=_campo("BOOLEAN"),
                representacao=_campo("STRING"),
            ),
            q5=_questao(
                resposta=_campo("STRING"),
            ),
            q6=_questao(
                resposta=_campo("STRING"),
            ),
            q7=_questao(
                mudou_resposta=_campo("BOOLEAN"),
                justificativa=_campo("STRING"),
            ),
        ),
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
        "schema": _schema(
            q1=_questao(
                alternativa=_campo("STRING", enum=["A", "B", "C", "D"]),
            ),
            q2=_questao(
                representacao=_campo("STRING"),
            ),
            q3=_questao(
                pontos_considerados=_campo("ARRAY", items={"type": "INTEGER"}),
                somente_resposta_final=_campo("BOOLEAN"),
            ),
            q4=_questao(
                testou_ponto=_campo("BOOLEAN"),
                explicacao=_campo("STRING"),
            ),
            q5=_questao(
                resposta=_campo("STRING"),
            ),
            q6=_questao(
                resposta=_campo("STRING"),
            ),
            q7=_questao(
                mudou_resposta=_campo("BOOLEAN"),
                justificativa=_campo("STRING"),
            ),
        ),
    },
    "sinais_de_transito": {
        "nome": "Sinais de Trânsito",
        "modo_entrada": "unica_imagem",
        "descricao": """
Folha de registro preenchida. Cada produção é identificada pelo código do
arquivo, que não identifica nem vincula estudantes a outras atividades.

1. Qual sinal tentou descobrir primeiro e por quê? Registre o símbolo, mesmo
se desenhado, e a justificativa.
2. Como acompanhou um dos percursos? Transcreva o texto e descreva o desenho,
preservando formas, ordem, setas e mudanças de direção visíveis.
3. Testou um significado que depois percebeu estar errado? Registre Sim/Não,
a hipótese descartada e o que permitiu perceber o erro. Se marcou Não, deixe
a hipótese e a explicação em branco.
4. Como usou o segundo percurso para confirmar ou corrigir a primeira ideia?
5. Como verificou que os quatro significados funcionavam nos dois percursos?
6. Qual foi a parte mais difícil?

Descreva somente o que está registrado. Não deduza o significado dos sinais,
não corrija as respostas e não atribua habilidades.
""",
        "schema": _schema(
            q1=_questao(
                simbolo=_campo("STRING"),
                justificativa=_campo("STRING"),
            ),
            q2=_questao(
                texto=_campo("STRING"),
                desenho=_campo("STRING"),
            ),
            q3=_questao(
                testou_significado=_campo("BOOLEAN"),
                hipotese_descartada=_campo("STRING"),
                como_percebeu=_campo("STRING"),
            ),
            q4=_questao(resposta=_campo("STRING")),
            q5=_questao(resposta=_campo("STRING")),
            q6=_questao(resposta=_campo("STRING")),
        ),
    },
    "dinheiro_de_castor": {
        "nome": "Dinheiro de Castor",
        "modo_entrada": "unica_imagem",
        "descricao": """
Folha de registro preenchida. Cada produção é identificada pelo código do
arquivo, que não identifica nem vincula estudantes a outras atividades.

1. Registre a alternativa assinalada: A, B, C ou D.
2. Registre as combinações de quadradinhos que o estudante diz ter testado.
3. Descreva como comparou as quatro cédulas, preservando números, texto,
desenhos e marcações. Não substitua esta resposta pelas combinações de Q2,
mesmo que sejam diferentes.
4. Testou alguma combinação que não funcionou? Registre Sim/Não e a combinação
ou explicação, se houver.
5. Por que essa combinação não diferenciava todas as cédulas? Se Q4 for Não e
Q5 estiver em branco, preserve o campo vazio sem tratá-lo como ilegível.
6. Como verificou que os dois quadradinhos escolhidos eram suficientes?
7. Qual foi a parte mais difícil?
8. Mudou a resposta ou a estratégia após conversar com um colega? Registre a
opção marcada e a justificativa. Na folha, as opções estão na ordem NÃO / SIM;
identifique a resposta pelo rótulo marcado, não pela posição.

Preserve as respostas como foram registradas. Não complete justificativas,
não avalie o acerto e não classifique habilidades.
""",
        "schema": _schema(
            q1=_questao(
                alternativa=_campo("STRING", enum=["A", "B", "C", "D"]),
            ),
            q2=_questao(
                combinacoes_testadas=_campo("ARRAY", items={"type": "STRING"}),
            ),
            q3=_questao(
                comparacao=_campo("STRING"),
            ),
            q4=_questao(
                testou_combinacao=_campo("BOOLEAN"),
                combinacao_ou_explicacao=_campo("STRING"),
            ),
            q5=_questao(resposta=_campo("STRING")),
            q6=_questao(resposta=_campo("STRING")),
            q7=_questao(resposta=_campo("STRING")),
            q8=_questao(
                mudou_resposta_ou_estrategia=_campo("BOOLEAN"),
                justificativa=_campo("STRING"),
            ),
        ),
    },
}
