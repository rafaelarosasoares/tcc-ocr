import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

from tcc_ocr.configuracoes import ARQUIVO_PADRAO, RAIZ_PROJETO, carregar_configuracao
from tcc_ocr.extracao import Extrator


class OrganizacaoTest(unittest.TestCase):
    def test_comandos_de_entrada_funcionam_fora_da_pasta_do_projeto(self):
        for comando in ("processar_turma.py", "interpretar_folha.py"):
            with self.subTest(comando=comando), tempfile.TemporaryDirectory() as fora:
                resultado = subprocess.run(
                    [sys.executable, "-B", str(RAIZ_PROJETO / comando), "--help"],
                    cwd=fora,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                self.assertEqual(resultado.returncode, 0, resultado.stderr)
                self.assertIn("--somente-planilha", resultado.stdout)
                self.assertIn("config/projeto.json", resultado.stdout)

    def test_ajuda_nao_carrega_sdks_de_nuvem_ou_bibliotecas_de_planilha(self):
        codigo = """
import sys
from tcc_ocr.cli import main
try:
    main(["--help"])
except SystemExit as resultado:
    assert resultado.code == 0
assert "google.genai" not in sys.modules
assert "google.cloud.documentai_v1" not in sys.modules
assert "pandas" not in sys.modules
assert "PIL" not in sys.modules
"""
        resultado = subprocess.run(
            [sys.executable, "-B", "-c", codigo],
            cwd=RAIZ_PROJETO,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_configuracao_tem_caminhos_ancorados_no_projeto(self):
        config = carregar_configuracao()
        self.assertEqual(config.raiz, RAIZ_PROJETO)
        self.assertEqual(config.drive["pastas_atividades"]["ATV1"], "chaves_do_cofre")
        self.assertIn("sinais_de_transito", config.drive["pastas_atividades_por_id"])
        self.assertIn("dinheiro_de_castor", config.drive["pastas_atividades_por_id"])
        self.assertIn(config.processor_id, config.processador)

    def test_configuracao_invalida_e_recusada_antes_de_criar_clientes(self):
        padrao = json.loads(ARQUIVO_PADRAO.read_text())
        invalidos = [
            [],
            {**padrao, "processamento": {"tentativas": 0}},
            {**padrao, "processamento": {"timeout_segundos": -1}},
            {**padrao, "processamento": {"qualidade_imagem": "sim"}},
        ]
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "projeto.json"
            for dados in invalidos:
                with self.subTest(dados=dados):
                    arquivo.write_text(json.dumps(dados))
                    with self.assertRaises(ValueError):
                        carregar_configuracao(arquivo)

    def test_extratores_tem_configuracoes_independentes(self):
        config = carregar_configuracao()
        primeiro = Extrator(config)
        segundo = Extrator(replace(config, qualidade_imagem=False, project_id="outro"))
        self.assertNotEqual(primeiro.config_ocr(), segundo.config_ocr())
        self.assertIsNone(primeiro._document_ai_client)
        self.assertIsNone(segundo._gemini_client)

    def test_encerramento_libera_ambos_clientes_mesmo_com_erro(self):
        extrator = Extrator(carregar_configuracao())
        gemini, document_ai = MagicMock(), MagicMock()
        gemini.close.side_effect = RuntimeError("falha ao fechar")
        extrator._gemini_client, extrator._document_ai_client = gemini, document_ai
        with self.assertRaises(RuntimeError):
            extrator.close()
        document_ai.transport.close.assert_called_once()
        extrator.close()
        gemini.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
