"""Configuração explícita do projeto, sem iniciar clientes ou autenticação."""

import json
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_PADRAO = RAIZ_PROJETO / "config" / "projeto.json"


@dataclass(frozen=True)
class ConfiguracaoProjeto:
    project_id: str
    document_ai_location: str
    processor_id: str
    vertex_location: str
    modelo_gemini: str
    drive: dict = field(default_factory=dict)
    versao: str = "3.0"
    timeout_segundos: int = 120
    tentativas: int = 3
    qualidade_imagem: bool = True
    max_revisar_por_registro: int = 1
    raiz: Path = RAIZ_PROJETO

    @property
    def processador(self):
        return f"projects/{self.project_id}/locations/{self.document_ai_location}/processors/{self.processor_id}"


def carregar_configuracao(caminho=None):
    arquivo = Path(caminho or ARQUIVO_PADRAO).expanduser()
    with arquivo.open(encoding="utf-8") as entrada:
        dados = json.load(entrada)
    if not isinstance(dados, dict) or not isinstance(dados.get("google_cloud"), dict):
        raise ValueError("O arquivo de configuração deve conter o objeto google_cloud.")
    nuvem = dados["google_cloud"]
    processamento = dados.get("processamento", {})
    exportacao = dados.get("exportacao", {})
    if not isinstance(processamento, dict):
        raise ValueError("processamento deve ser um objeto JSON.")
    if not isinstance(exportacao, dict):
        raise ValueError("exportacao deve ser um objeto JSON.")
    for chave in (
        "project_id",
        "document_ai_location",
        "processor_id",
        "vertex_location",
        "modelo_gemini",
    ):
        if not isinstance(nuvem.get(chave), str) or not nuvem[chave].strip():
            raise ValueError(f"Configuração inválida em google_cloud.{chave}.")
    config = ConfiguracaoProjeto(
        **{
            chave: nuvem[chave]
            for chave in (
                "project_id",
                "document_ai_location",
                "processor_id",
                "vertex_location",
                "modelo_gemini",
            )
        },
        drive=dados.get("google_drive", {}),
        max_revisar_por_registro=exportacao.get("max_revisar_por_registro", 1),
        **{
            chave: processamento[chave]
            for chave in ("versao", "timeout_segundos", "tentativas", "qualidade_imagem")
            if chave in processamento
        },
    )
    if type(config.tentativas) is not int or not 1 <= config.tentativas <= 5:
        raise ValueError("processamento.tentativas deve estar entre 1 e 5.")
    if type(config.timeout_segundos) is not int or config.timeout_segundos <= 0:
        raise ValueError("processamento.timeout_segundos deve ser positivo.")
    if type(config.qualidade_imagem) is not bool:
        raise ValueError("processamento.qualidade_imagem deve ser true ou false.")
    if (
        type(config.max_revisar_por_registro) is not int
        or not 0 <= config.max_revisar_por_registro <= 8
    ):
        raise ValueError("exportacao.max_revisar_por_registro deve estar entre 0 e 8.")
    if not isinstance(config.versao, str) or not config.versao:
        raise ValueError("processamento.versao deve ser um texto não vazio.")
    if not isinstance(config.drive, dict) or any(
        not isinstance(config.drive.get(chave, {}), dict)
        for chave in ("pastas_atividades", "pastas_atividades_por_id")
    ):
        raise ValueError("google_drive deve conter um mapeamento válido de pastas_atividades.")
    if config.drive.get("pasta_id") is not None and not isinstance(config.drive["pasta_id"], str):
        raise ValueError("google_drive.pasta_id deve ser um texto.")
    if any(
        not isinstance(nome, str) or not isinstance(atividade, str)
        for nome, atividade in config.drive.get("pastas_atividades", {}).items()
    ):
        raise ValueError("O mapeamento pastas_atividades deve conter nomes de pastas e atividades.")
    if any(
        not isinstance(atividade, str) or not isinstance(pasta_id, str)
        for atividade, pasta_id in config.drive.get("pastas_atividades_por_id", {}).items()
    ):
        raise ValueError(
            "O mapeamento pastas_atividades_por_id deve conter atividades e IDs de pasta."
        )
    return config
