# TCC OCR

Extração de atividades Bebras com Google Document AI e Gemini, a partir de imagens
locais ou do Google Drive. O fluxo valida a entrada, reaproveita etapas concluídas
e gera uma planilha com as respostas e pendências de revisão.

Registros com mais de uma questão marcada como `revisar` são excluídos da
planilha final. Os JSONs completos são preservados, e a filtragem fica registrada
em `resultados/relatorio_exportacao.json`.

## Instalação

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Configure a autenticação seguindo [este guia](docs/autenticacao.md).

## Uso

No terminal, entre na pasta do projeto:

```sh
cd /Users/enzoveroneze/tcc-ocr
.venv/bin/python processar_turma.py --drive
```

A pasta do Drive já está definida em `config/projeto.json`. A raiz mapeia
`ATV1 → chaves_do_cofre` e `ATV2 → agua_para_todos`; as pastas independentes
`ATV3` e `ATV4` são configuradas por ID em `pastas_atividades_por_id`.
ATV1/ATV2 mantêm seus formatos atuais. ATV3 (Sinais de Trânsito) e ATV4
(Dinheiro de Castor) usam uma imagem de resposta por produção, como
`A001_resposta.jpg`, sem exigir imagem `_questao`. Imagens sem extensão recebem
uma extensão conforme o tipo do arquivo no Drive.

Para consultar as opções:

```sh
.venv/bin/python -m tcc_ocr --help
```

| Operação | Comando |
| --- | --- |
| Baixar e processar do Drive | `.venv/bin/python -m tcc_ocr --drive` |
| Apenas baixar | `.venv/bin/python -m tcc_ocr --drive --somente-baixar` |
| Validar uma entrada local | `.venv/bin/python -m tcc_ocr --entrada caminho --validar` |
| Retomar a última extração | `.venv/bin/python -m tcc_ocr --retomar` |
| Recriar somente o Excel | `.venv/bin/python -m tcc_ocr --somente-planilha` |
| Preparar a avaliação manual | `.venv/bin/python -m tcc_ocr --preparar-avaliacao` |
| Comparar a referência conferida | `.venv/bin/python -m tcc_ocr --avaliar resultados/avaliacao_manual.json` |

`processar_turma.py` e `interpretar_folha.py` continuam aceitando as mesmas opções.
Os comandos com o Python do ambiente virtual funcionam também no fish, sem ativação.

## Estrutura

```text
config/                 # Configuração do projeto Google e do processamento.
tcc_ocr/                # Código da aplicação, separado por responsabilidade.
tests/                  # Testes automatizados, sem chamadas reais às APIs.
docs/                   # Autenticação, fluxo, avaliação e arquitetura.
entrada/                # Imagens locais por atividade.
entrada_drive/          # Importações do Drive e cache de downloads.
resultados/             # JSONs, Excel, relatórios e referência manual.
resultados/historico/   # Planilhas anteriores.
```

O código cria os clientes de nuvem somente quando necessário. Os diretórios padrão
são relativos à raiz do projeto; configurações alternativas podem ser usadas com
`--config caminho.json`. Credenciais não devem ser colocadas no arquivo de configuração.

## Documentação

- [Autenticação e permissões](docs/autenticacao.md)
- [Validação, processamento, caches e retomada](docs/fluxo.md)
- [Conferência e avaliação manual](docs/avaliacao.md)
- [Arquitetura e desenvolvimento](docs/arquitetura.md)
- [Estado dos resultados e evidências para o TCC](docs/estado_dos_resultados.md)

## Desenvolvimento

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```
