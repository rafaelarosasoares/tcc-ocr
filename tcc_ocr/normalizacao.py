"""Normalização das respostas e motivos determinísticos de revisão."""

from .validacao import sem_identificacao

TERMOS_INCERTEZA = [
    "possivelmente",
    "provavelmente",
    "parece",
    "parecendo",
    "aparenta",
    "aparentemente",
    "talvez",
    "incerto",
    "incerta",
    "não está claro",
    "não é claro",
    "não claramente",
    "não foi possível identificar",
    "difícil identificar",
]


def contem_incerteza(valor):

    if valor is None:
        return False

    if isinstance(valor, str):
        texto = valor.lower()

        return any(termo in texto for termo in TERMOS_INCERTEZA)

    if isinstance(valor, list):
        return any(contem_incerteza(item) for item in valor)

    if isinstance(valor, dict):
        return any(
            contem_incerteza(conteudo) for chave, conteudo in valor.items() if chave != "status"
        )

    return False


def normalizar_resultado(resultado):
    resultado = sem_identificacao(resultado)
    motivos = {}
    for numero in range(1, 9):
        chave = f"q{numero}"
        dados = resultado.get(chave)
        if not isinstance(dados, dict):
            continue
        if dados.get("status") == "ok" and contem_incerteza(dados):
            dados["status"] = "revisar"
            motivos[chave] = "A descrição contém linguagem de incerteza; confira com a imagem."
        elif dados.get("status") == "revisar":
            motivos[chave] = "O modelo sinalizou ambiguidade na extração; confira com a imagem."
        elif dados.get("status") == "ilegivel":
            motivos[chave] = (
                "Conteúdo sinalizado como ilegível; conferir a foto ou obter nova digitalização."
            )
    resultado["_motivos_revisao"] = motivos
    return resultado
