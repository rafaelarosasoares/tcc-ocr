"""Instruções de extração; alterações aqui afetam a assinatura da interpretação."""


def montar_prompt_unico(texto_ocr, configuracao):

    return f"""
Você está analisando uma folha de registro de um estudante
na atividade Bebras:

"{configuracao["nome"]}"

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

Não extraia nem transcreva o nome, a identificação pessoal ou o ano escolar do estudante.
Use apenas os campos de atividade e questões definidos no schema.

Preserve o sentido original das respostas.
Corrija erros do OCR somente quando a imagem
permitir confirmar claramente o conteúdo.

Retorne somente JSON.
"""


def montar_prompt_par(texto_ocr, configuracao):

    return f"""
Você está analisando o registro de um estudante
na atividade Bebras:

"{configuracao["nome"]}"

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

Não extraia nem transcreva o nome, a identificação pessoal ou o ano escolar do estudante.
Use apenas os campos de atividade e questões definidos no schema.

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
