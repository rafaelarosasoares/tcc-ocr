"""Clientes de OCR e Gemini criados apenas quando uma chamada é necessária."""

import ast
import inspect
import json
from pathlib import Path

from .normalizacao import TERMOS_INCERTEZA, contem_incerteza, normalizar_resultado
from .persistencia import assinatura
from .prompts import montar_prompt_par, montar_prompt_unico
from .validacao import sem_identificacao


def descobrir_mime_type(caminho):
    formatos = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    try:
        return formatos[Path(caminho).suffix.lower()]
    except KeyError as erro:
        raise ValueError(f"Formato não suportado: {Path(caminho).suffix}") from erro


def _codigo_semantico(funcao):
    """Comentários e formatação não invalidam o cache de respostas."""
    return ast.dump(ast.parse(inspect.getsource(funcao)), include_attributes=False)


class Extrator:
    def __init__(self, configuracao):
        self.config = configuracao
        self._document_ai_client = None
        self._gemini_client = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        gemini, self._gemini_client = self._gemini_client, None
        document_ai, self._document_ai_client = self._document_ai_client, None
        try:
            if gemini is not None:
                gemini.close()
        finally:
            if document_ai is not None:
                document_ai.transport.close()

    def _cliente_ocr(self):
        if self._document_ai_client is None:
            from google.api_core.client_options import ClientOptions
            from google.cloud import documentai_v1 as documentai

            self._document_ai_client = documentai.DocumentProcessorServiceClient(
                client_options=ClientOptions(
                    api_endpoint=f"{self.config.document_ai_location}-documentai.googleapis.com"
                )
            )
        return self._document_ai_client

    def _cliente_gemini(self):
        if self._gemini_client is None:
            from google import genai
            from google.genai.types import HttpOptions, HttpRetryOptions

            self._gemini_client = genai.Client(
                vertexai=True,
                project=self.config.project_id,
                location=self.config.vertex_location,
                http_options=HttpOptions(
                    api_version="v1",
                    timeout=self.config.timeout_segundos * 1000,
                    retry_options=HttpRetryOptions(attempts=1),
                ),
            )
        return self._gemini_client

    def config_ocr(self):
        return {
            "processador": self.config.processador,
            "qualidade_imagem": self.config.qualidade_imagem,
            "versao_ocr": 1,
        }

    def assinaturas_interpretacao(self, atividades):
        normalizacao = [
            _codigo_semantico(funcao)
            for funcao in (normalizar_resultado, contem_incerteza, sem_identificacao)
        ]
        return {
            atividade: assinatura(
                {
                    "modelo": self.config.modelo_gemini,
                    "versao": self.config.versao,
                    "schema": configuracao["schema"],
                    "temperature": 0,
                    "versao_extrator": 1,
                    "prompt": (
                        montar_prompt_unico
                        if configuracao["modo_entrada"] == "unica_imagem"
                        else montar_prompt_par
                    )("<<OCR>>", configuracao),
                    "normalizacao": normalizacao,
                    "termos": TERMOS_INCERTEZA,
                }
            )
            for atividade, configuracao in atividades.items()
        }

    def executar_ocr(self, caminho):
        from google.cloud import documentai_v1 as documentai

        request = documentai.ProcessRequest(
            name=self.config.processador,
            raw_document=documentai.RawDocument(
                content=Path(caminho).read_bytes(), mime_type=descobrir_mime_type(caminho)
            ),
        )
        if self.config.qualidade_imagem:
            request.process_options = documentai.ProcessOptions(
                ocr_config=documentai.OcrConfig(enable_image_quality_scores=True)
            )
        resposta = self._cliente_ocr().process_document(
            request=request, retry=None, timeout=self.config.timeout_segundos
        )
        paginas = []
        for pagina in resposta.document.pages:
            if pagina._pb.HasField("image_quality_scores"):
                qualidade = pagina.image_quality_scores
                paginas.append(
                    {
                        "pagina": pagina.page_number,
                        "qualidade": float(qualidade.quality_score),
                        "defeitos": [
                            {"tipo": defeito.type_, "confianca": float(defeito.confidence)}
                            for defeito in qualidade.detected_defects
                        ],
                    }
                )
        return {"texto": resposta.document.text, "paginas": paginas}

    def interpretar(self, registro, texto_ocr, configuracao):
        from google.genai.types import GenerateContentConfig, Part

        arquivos = registro["arquivos"]
        unica = configuracao["modo_entrada"] == "unica_imagem"
        partes = []
        tipos = ("resposta",) if unica else ("questao", "resposta")
        rotulos = {
            "questao": "IMAGEM 1 - QUESTÃO/MAPA COM ANOTAÇÕES:",
            "resposta": "IMAGEM 2 - FOLHA DE RESPOSTA:",
        }
        for tipo in tipos:
            if not unica:
                partes.append(rotulos[tipo])
            caminho = arquivos[tipo]
            partes.append(
                Part.from_bytes(
                    data=Path(caminho).read_bytes(), mime_type=descobrir_mime_type(caminho)
                )
            )
        partes.append(
            (montar_prompt_unico if unica else montar_prompt_par)(texto_ocr, configuracao)
        )
        resposta = self._cliente_gemini().models.generate_content(
            model=self.config.modelo_gemini,
            contents=partes,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=configuracao["schema"],
                temperature=0,
            ),
        )
        if not resposta.text:
            raise ValueError("O Gemini não retornou conteúdo.")
        return json.loads(resposta.text)
