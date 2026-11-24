## Validação antes da extração

Os exemplos abaixo usam o Python do ambiente virtual diretamente, inclusive no fish.

```sh
.venv/bin/python processar_turma.py --entrada entrada_drive/importacao-... --validar
```

O comando confere nomes, duplicatas por aluno e tipo de página, pares completos,
integridade e decodificação das imagens e correspondência entre formato e
extensão. Imagens pequenas geram avisos para conferir a legibilidade. Uma entrada
inválida bloqueia todo o lote antes das chamadas de Document AI/Gemini. A execução
normal também faz essa validação automaticamente. `--drive --validar` importa
primeiro do Drive e então valida, sem executar OCR/IA.

O diagnóstico separado fica em `resultados/validacao_entrada.json`; ele não
substitui o relatório usado para retomar uma execução.

## Processar e retomar falhas

```sh
.venv/bin/python processar_turma.py --drive
.venv/bin/python processar_turma.py --retomar
```

`relatorio_execucao.json` é atualizado de forma atômica antes e depois de cada
etapa. Informa a entrada utilizada, o estado de cada aluno, a etapa da falha,
as tentativas e os totais de processados, reaproveitados, inválidos e pendentes.
A retomada usa a entrada registrada e reaproveita os resultados e o OCR válidos;
as etapas que falharam são tentadas novamente. Preserve as pastas de importação
enquanto houver pendências. Para usar uma origem atualizada, combine `--retomar`
com `--drive` ou `--entrada outra-pasta`.

Falhas transitórias de rede, limite de requisições e indisponibilidade têm até
três tentativas com espera crescente; erros permanentes de permissão ou respostas
fora do schema não são repetidos automaticamente. Use `--tentativas 1` a `5` para
ajustar esse limite. As chamadas de OCR e Gemini têm timeout de 120 segundos.
Uma falha de autorização interrompe o restante do lote, deixando os demais
registros pendentes para retomar após corrigir as credenciais.

Uma execução parcial retorna código de saída `1` e sua planilha identifica o
estado na aba `Execução` e os registros não concluídos em `Erros`. Um resultado
antigo cujo reprocessamento falhou não é incluído como se estivesse atualizado.
Se nenhum registro terminar, o Excel anterior é preservado. O código `130`
indica interrupção pelo teclado. A publicação do Excel é atômica; se o arquivo
estiver bloqueado pelo Excel, feche-o e tente a exportação novamente.

## Caches por etapa

- **Drive:** `entrada_drive/.cache_drive/`, com checksum verificado antes do uso.
- **OCR:** `resultados/.cache_ocr/`, por SHA-256 da imagem e configuração do processador.
- **Interpretação:** JSON do aluno, com assinatura de imagens, modelo, prompt,
  schema, parâmetros, normalização e versão do processamento.

Uma mudança apenas no prompt ou modelo refaz a interpretação, mantendo o OCR
válido. O OCR das páginas de questão e resposta é guardado separadamente e
fornecido ao Gemini junto das imagens. `--forcar` ignora os caches de OCR e
interpretação, mas não obriga a baixar novamente uma imagem já verificada.

Resultados anteriores à versão 3.0 não têm as novas assinaturas. A primeira
extração com esta versão pode refazer chamadas às APIs. As operações offline
abaixo continuam usando os JSONs existentes sem reextrair as folhas.

## Planilha e revisão sem reextrair

Na exportação, registros com **duas ou mais questões marcadas como `revisar`**
ficam fora da planilha final, inclusive da aba `Revisar`. Registros com zero ou
uma questão nesse estado continuam. A contagem considera somente o status de
Q1 a Q8, por registro de atividade; `ilegivel` e avisos de qualidade de imagem
não são contados como `revisar` para esse critério.

O limite fica em `exportacao.max_revisar_por_registro`, no arquivo
`config/projeto.json`. O padrão é `1`. Os JSONs originais e a referência humana
são preservados. `relatorio_exportacao.json` registra os códigos e quantidades
excluídos, os totais por atividade e o hash da planilha publicada, permitindo
auditar a filtragem sem recolocar esses registros no Excel. Essa seleção reduz
pendências visíveis; não transforma respostas incertas em respostas corretas.

```sh
.venv/bin/python processar_turma.py --somente-planilha
```

Esse comando funciona sem autenticação nas APIs. Quando há relatório de execução,
exporta somente seus registros concluídos; sem relatório, usa os JSONs salvos nas
pastas das atividades. JSONs inválidos interrompem a exportação, preservando o
Excel anterior.

A aba `Revisar` traz o motivo da pendência e links para as imagens originais.
Novas extrações registram tanto a origem do Drive quanto o arquivo local.
Resultados antigos recebem links locais apenas se o hash da imagem encontrada
coincidir com o hash registrado na extração, evitando apontar para outra folha.

Quando o processador retorna métricas de qualidade, defeitos de imagem com
confiança de pelo menos `0.5` geram uma pendência de imagem. Esse limiar é uma
regra de triagem, não uma medida de acurácia da transcrição. As métricas não
substituem a conferência humana nem alteram automaticamente as respostas.
Se o seu processador não aceitar essa opção, use `--sem-qualidade-imagem`.
Detalhes das métricas na [documentação do Document AI](https://cloud.google.com/document-ai/docs/enterprise-document-ocr).

Nome, status do nome e ano escolar foram retirados dos prompts, schemas e novos
JSONs de extração. Não aparecem na planilha. Os arquivos de imagem, os caches de
OCR e JSONs históricos podem continuar contendo informação da folha original;
essa alteração não anonimiza o acervo histórico.

