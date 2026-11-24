# Organização do projeto

O código fica em `tcc_ocr/`. Os arquivos `processar_turma.py` e
`interpretar_folha.py` são entradas de compatibilidade para a mesma interface;
também é possível executar `.venv/bin/python -m tcc_ocr`.

| Módulo | Responsabilidade |
| --- | --- |
| `cli.py` | Argumentos, escolha do modo de execução e códigos de saída. |
| `configuracoes.py` | Leitura e validação de `config/projeto.json`. |
| `atividades.py` | Descrições e schemas compartilhados das atividades. |
| `drive.py` | Listagem, download, checksum e origem dos arquivos. |
| `extracao.py` | Clientes independentes de Document AI e Gemini, criados sob demanda. |
| `prompts.py` | Instruções enviadas ao Gemini. |
| `normalizacao.py` | Normalização e motivos de revisão das respostas. |
| `validacao.py` | Conferência de imagens e validação dos JSONs. |
| `fluxo.py` | Execução, checkpoints, reaproveitamento e retomada. |
| `persistencia.py` | Hashes e publicação atômica de JSONs. |
| `planilha.py` | Exportação atômica do Excel e links de revisão. |
| `avaliacao.py` | Amostragem e comparação com a referência humana. |

Os clientes e o diretório de saída não são variáveis globais: cada execução
recebe sua própria configuração. Os clientes são encerrados ao terminar o lote.
A ajuda não importa as bibliotecas de nuvem, de planilha ou de imagens.

## Configuração

`config/projeto.json` contém os identificadores do projeto e processador,
o modelo, a pasta do Drive e os parâmetros de execução. Credenciais continuam
fora do repositório, conforme [autenticação](autenticacao.md).

Use `--config outro-projeto.json` para outra configuração. Os diretórios padrão
`entrada/`, `entrada_drive/` e `resultados/` são resolvidos a partir da raiz do
projeto, mesmo quando o script é chamado de outra pasta. Caminhos explicitamente
informados na linha de comando são relativos à pasta atual do terminal.

As atividades ficam em `atividades.py`. Os construtores `_campo`, `_questao` e
`_schema` evitam repetir a definição dos tipos, estados e campos obrigatórios.

## Dados

```text
entrada/                     # Imagens locais, separadas por atividade.
entrada_drive/               # Importações completas e cache de downloads.
resultados/
├── chaves_do_cofre/          # JSONs por aluno e OCR histórico.
├── agua_para_todos/         # JSONs por aluno e OCR histórico.
├── historico/               # Planilhas anteriores preservadas.
├── resultado_turma.xlsx     # Planilha atual.
├── avaliacao_manual.json    # Referência manual, editada pelo revisor.
├── relatorio_avaliacao.json # Métricas da referência conferida.
├── validacao_entrada.json   # Diagnóstico de pré-validação.
├── relatorio_execucao.json  # Estado da última extração, quando executada.
└── .cache_ocr/              # OCR por conteúdo e configuração.
```

Os caminhos das entradas e resultados atuais foram mantidos para preservar
links e referências existentes. A pasta do documento LaTeX foi removida.

## Caches e alterações de código

O cache de OCR depende da imagem, processador, opção de qualidade e
`versao_ocr`. A interpretação depende das imagens, modelo, prompt, schema,
normalização e versão do processamento. A assinatura da normalização considera
a estrutura do código, sem comentários ou formatação.

Ao alterar o comportamento das chamadas em `extracao.py`, incremente
`versao_ocr` ou `versao_extrator`, conforme a etapa afetada. Alterações no prompt,
schema, modelo ou normalização são detectadas automaticamente. A migração da
estrutura antiga de assinaturas pode invalidar caches existentes uma vez.

## Desenvolvimento

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

Os testes usam imagens artificiais e clientes simulados. Conferências com os
dados reais devem usar os modos offline ou `--validar` para evitar chamadas
desnecessárias às APIs. Os padrões de formatação estão em `pyproject.toml` e
`.editorconfig`.
