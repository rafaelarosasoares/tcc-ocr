## Avaliação com referência humana

Crie uma amostra reproduzível de dez registros, distribuída por atividade e
presença de pendências:

```sh
.venv/bin/python processar_turma.py --preparar-avaliacao --amostra 10 --semente 42
```

O arquivo `resultados/avaliacao_manual.json` contém as fontes e uma referência
inicialmente vazia para cada questão. As respostas do modelo não são copiadas para
a referência: abra a imagem e faça a transcrição manual de forma independente.
Preencha todos os campos de `referencia` usando os tipos definidos no schema:
texto entre aspas, booleanos `true`/`false` e listas como `["A", "B"]`. Use `null`
para campo realmente vazio e só marque `conferido` como `true` após verificar.
Se não conseguir ler a resposta, deixe `conferido` como `false`.

Exemplo de item preenchido para a alternativa da primeira questão:

```json
{
  "atividade": "chaves_do_cofre",
  "codigo": "A001",
  "questao": "q1",
  "referencia": {"alternativa": "B"},
  "conferido": true
}
```

Edite somente `referencia` e `conferido` no arquivo gerado; preserve também os
outros campos de cada item, inclusive `assinatura_extracao` e `fontes`.

Depois compare com a extração:

```sh
.venv/bin/python processar_turma.py --avaliar resultados/avaliacao_manual.json
```

`relatorio_avaliacao.json` apresenta concordância por campo e atividade,
divergências inclusive em respostas marcadas `ok` e quantidade ainda não
conferida. Sem referências conferidas, a concordância é `null`, e não zero.
A comparação normaliza apenas Unicode e espaços; diferenças de redação podem
precisar de análise humana. Os percentuais descrevem a amostra conferida, sem
estimar automaticamente a acurácia da turma ou avaliar o estudante.

A assinatura impede comparar uma referência com uma extração que mudou depois
da amostragem. O comando de preparação não sobrescreve avaliações existentes;
para outra amostra, use `--arquivo-amostra resultados/outra_amostra.json`.

Todos esses comandos aceitam `--resultados outra-pasta`. `interpretar_folha.py`
é uma entrada compatível para a mesma implementação, evitando diferenças entre
os dois scripts.
