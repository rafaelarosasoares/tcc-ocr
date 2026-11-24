# Estado dos resultados e evidências

Conferência realizada em 11/11/2026. Este documento distingue o comportamento
disponível no código dos procedimentos comprovados pelos arquivos atuais.

## Implementação disponível

A versão 3.0 oferece importação do Drive, validação prévia das imagens,
OCR das páginas de questão e resposta, interpretação estruturada, caches
independentes, indicadores de qualidade quando retornados pelo processador,
checkpoints e retomada. Os novos schemas não solicitam nome e ano escolar.

A existência desses recursos no código não demonstra que tenham sido utilizados
para produzir os JSONs históricos ou a planilha atual.

## Proveniência dos JSONs existentes

| Verificação | As chaves do cofre | Água para Todos |
| --- | ---: | ---: |
| JSONs disponíveis | 18 | 17 |
| Versão registrada em `_processamento.versao` | 2.1 | 2.1 |
| JSONs com o campo `nome_estudante` | 18 | 17 |
| JSONs com o campo `ano` | 18 | 17 |
| JSONs com a nova assinatura de processamento | 0 | 0 |
| JSONs com `_qualidade_imagens` | 0 | 0 |
| JSONs com `_fontes` | 0 | 0 |

Os resultados são históricos e foram preservados. Nome e ano não aparecem na
planilha, mas continuam nos JSONs existentes. A mudança dos schemas não executa
limpeza retroativa nem anonimiza imagens, OCR ou arquivos históricos.

## Operações verificadas com os dados atuais

A pré-validação conferiu 52 imagens associadas a 35 registros de atividades,
sem registros inválidos nessa conferência. Essa verificação de integridade
e organização das entradas não corresponde a uma nova extração.

A planilha foi recriada a partir dos JSONs salvos, aplicando a exclusão de
registros com mais de uma questão marcada como `revisar`:

| Atividade | Disponíveis | Excluídos | Exportados |
| --- | ---: | ---: | ---: |
| As chaves do cofre | 18 | 1 | 17 |
| Água para Todos | 17 | 2 | 15 |
| Total | 35 | 3 | 32 |

A aba `Revisar` contém 15 pendências. A redução de 21 para 15 decorre da
exclusão de registros da exportação, e não de uma correção das respostas ou
de um aumento de acurácia demonstrado. O critério altera o conjunto exportado
e deve constar na metodologia.

Evidências: [pré-validação](../resultados/validacao_entrada.json),
[exportação](../resultados/relatorio_exportacao.json) e
[planilha](../resultados/resultado_turma.xlsx).

## Testes de software

A suíte foi executada novamente e a saída foi salva em
[execucao_testes.txt](../resultados/relatorios/execucao_testes.txt).
O log registra o comando, o momento em UTC, a versão do Python, o código de saída
e o resultado individual dos testes. A existência dos testes no código, sem esse
resultado de execução, não demonstra aprovação.

Os testes usam imagens artificiais e clientes simulados. A aprovação verifica
comportamentos do software; não comprova acurácia da extração nos dados reais
nem que todos os recursos novos tenham sido executados com as APIs reais.

## Avaliação ainda pendente

Foi preparada uma amostra de 10 registros e 70 questões, mas nenhuma referência
humana foi conferida. O relatório registra zero campos conferidos e concordância
`null`. Portanto, ainda não há estimativa empírica de acurácia ou concordância
com referência humana.

Evidências: [amostra](../resultados/avaliacao_manual.json) e
[relatório de avaliação](../resultados/relatorio_avaliacao.json).

## Redação sugerida para o TCC

> A versão atual do sistema incorpora recursos de importação, validação,
> reaproveitamento de etapas e tratamento de falhas. O conjunto de resultados
> analisado, entretanto, é composto por 35 registros cuja versão de processamento
> registrada é 2.1. Esses resultados foram preservados e utilizados para gerar
> uma nova planilha, sem reexecutar a extração. Na exportação, aplicou-se o critério
> de exclusão de registros com mais de uma questão sinalizada como `revisar`,
> obtendo-se 32 registros e 15 pendências de revisão. A ausência de nome e ano
> na planilha não implica remoção desses campos dos JSONs históricos. A avaliação
> por referência humana permanece pendente. Os testes automatizados verificam
> o funcionamento do software e são apresentados com o respectivo log de execução.
