import hashlib
import importlib
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from requests import ConnectionError, HTTPError

from tcc_ocr.drive import PASTA_MIME, baixar_entrada, extrair_id_pasta, preparar_entrada


def resposta(dados=None, conteudo=b"imagem", erro=None):
    resultado = MagicMock()
    resultado.__enter__.return_value = resultado
    resultado.json.return_value = dados
    resultado.iter_content.return_value = [conteudo]
    resultado.raise_for_status.side_effect = erro
    return resultado


def pasta(nome="chaves_do_cofre", identificador="atividade"):
    return {"id": identificador, "name": nome, "mimeType": PASTA_MIME}


def imagem(nome="A001_resposta.jpg", identificador="imagem", conteudo=b"imagem"):
    return {
        "id": identificador,
        "name": nome,
        "mimeType": "image/jpeg",
        "md5Checksum": hashlib.md5(conteudo).hexdigest(),
    }


class EntradaDriveTest(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporario.cleanup)
        self.destino = Path(self.temporario.name) / "downloads"
        self.saida = io.StringIO()
        self.redirecionamento = redirect_stdout(self.saida)
        self.redirecionamento.__enter__()
        self.addCleanup(self.redirecionamento.__exit__, None, None, None)

    def sessao(self, pastas=None, imagens=None, download=None):
        sessao = MagicMock()
        sessao.get.side_effect = [
            resposta({"mimeType": PASTA_MIME}),
            resposta({"files": pastas if pastas is not None else [pasta()]}),
            resposta({"files": imagens if imagens is not None else [imagem()]}),
            download or resposta(),
        ]
        return sessao

    def baixar(self, sessao, mapa=None, atividades=None, pastas_ids=None):
        return Path(
            baixar_entrada(
                "raiz",
                self.destino,
                atividades or ["chaves_do_cofre"],
                sessao,
                pastas_atividades=mapa,
                pastas_atividades_por_id=pastas_ids,
            )
        )

    def test_aceita_id_e_links_incluindo_link_do_usuario(self):
        for valor in (
            "abc-123_",
            "https://drive.google.com/drive/folders/abc-123_?usp=sharing",
            "https://drive.google.com/drive/u/0/folders/abc-123_",
            "https://drive.google.com/open?id=abc-123_",
        ):
            with self.subTest(valor=valor):
                self.assertEqual(extrair_id_pasta(valor), "abc-123_")

    def test_rejeita_links_invalidos_e_injecao_na_consulta(self):
        for valor in ("", "../pasta", "id' or trashed = true", "https://outro.com/folders/id"):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                extrair_id_pasta(valor)

    def test_baixa_em_pasta_independente_sem_alterar_entrada_existente(self):
        self.destino.mkdir()
        (self.destino / "preservar.txt").write_text("local")
        raiz = self.baixar(self.sessao())
        self.assertEqual((raiz / "chaves_do_cofre/A001_resposta.jpg").read_bytes(), b"imagem")
        self.assertEqual((self.destino / "preservar.txt").read_text(), "local")
        self.assertFalse(list(self.destino.glob(".baixando-*")))

    def test_paginacao_inclui_paginas_vazias(self):
        sessao = self.sessao()
        sessao.get.side_effect = [
            resposta({"mimeType": PASTA_MIME}),
            resposta({"files": [], "nextPageToken": "proxima"}),
            resposta({"files": [pasta()]}),
            resposta({"files": [imagem()]}),
            resposta(),
        ]
        self.baixar(sessao)
        consulta = sessao.get.call_args_list[2]
        self.assertEqual(consulta.kwargs["params"]["pageToken"], "proxima")
        self.assertEqual(consulta.kwargs["params"]["supportsAllDrives"], "true")

    def test_mapeia_atv1_e_acrescenta_extensao_por_mime(self):
        sessao = self.sessao(pastas=[pasta("ATV1")], imagens=[imagem("A001_resposta")])
        raiz = self.baixar(sessao, {"ATV1": "chaves_do_cofre"})
        self.assertTrue((raiz / "chaves_do_cofre/A001_resposta.jpg").exists())

    def test_importa_atividade_de_pasta_drive_configurada_por_id(self):
        sessao = MagicMock()
        sessao.get.side_effect = [
            resposta({"mimeType": PASTA_MIME}),
            resposta({"files": []}),
            resposta({"mimeType": PASTA_MIME}),
            resposta({"files": [imagem()]}),
            resposta(),
        ]
        raiz = self.baixar(
            sessao,
            atividades=["sinais_de_transito"],
            pastas_ids={"sinais_de_transito": "pasta-direta"},
        )
        self.assertEqual(
            (raiz / "sinais_de_transito/A001_resposta.jpg").read_bytes(),
            b"imagem",
        )

    def test_ignora_scans_sem_identificacao_e_outros_formatos(self):
        sessao = self.sessao(
            imagens=[
                imagem("Digitalizado_123.jpg"),
                imagem("carta.pdf"),
                imagem(),
            ]
        )
        raiz = self.baixar(sessao)
        self.assertEqual(len(list(raiz.rglob("*.jpg"))), 1)
        self.assertIn("sem sufixo", self.saida.getvalue())

    def test_rejeita_duplicatas_apos_normalizar_extensao_e_maiusculas(self):
        for nomes in (
            ("A001_resposta", "A001_resposta.jpg"),
            ("A001_resposta.jpg", "a001_RESPOSTA.JPG"),
        ):
            with self.subTest(nomes=nomes), self.assertRaisesRegex(ValueError, "duplicados"):
                self.baixar(self.sessao(imagens=[imagem(nome) for nome in nomes]))
        self.assertFalse(self.destino.exists())

    def test_rejeita_duas_pastas_mapeadas_para_mesma_atividade(self):
        with self.assertRaisesRegex(ValueError, "duplicadas"):
            self.baixar(
                self.sessao(pastas=[pasta(), pasta("ATV1", "outra")]),
                {"ATV1": "chaves_do_cofre"},
            )

    def test_rejeita_path_traversal(self):
        with self.assertRaisesRegex(ValueError, "inválido"):
            self.baixar(self.sessao(imagens=[imagem("../../A001_resposta.jpg")]))
        self.assertFalse(self.destino.exists())

    def test_download_falho_descarta_importacao_incompleta(self):
        download = resposta()
        download.iter_content.side_effect = ConnectionError("interrompido")
        with self.assertRaises(ConnectionError):
            self.baixar(self.sessao(download=download))
        self.assertEqual(list(self.destino.iterdir()), [])

    def test_checksum_incorreto_descarta_importacao(self):
        with self.assertRaisesRegex(ValueError, "incompleto"):
            self.baixar(self.sessao(download=resposta(conteudo=b"corrompida")))
        self.assertEqual(list(self.destino.iterdir()), [])

    def test_importacao_seguinte_reusa_download_verificado_e_salva_origem(self):
        primeira = self.baixar(self.sessao())
        sessao = self.sessao()
        segunda = self.baixar(sessao)
        self.assertNotEqual(primeira, segunda)
        self.assertEqual(sessao.get.call_count, 3)
        self.assertEqual((segunda / "chaves_do_cofre/A001_resposta.jpg").read_bytes(), b"imagem")
        self.assertTrue((segunda / "_origem_drive.json").exists())

    def test_cache_drive_corrompido_e_baixado_novamente(self):
        self.baixar(self.sessao())
        cache = next((self.destino / ".cache_drive").iterdir())
        cache.write_bytes(b"alterado")
        sessao = self.sessao()
        self.baixar(sessao)
        self.assertEqual(sessao.get.call_count, 4)
        self.assertEqual(cache.read_bytes(), b"imagem")

    def test_origem_sem_imagens_nao_reaproveita_download_anterior(self):
        antiga = self.baixar(self.sessao())
        with self.assertRaisesRegex(ValueError, "Nenhuma imagem"):
            self.baixar(self.sessao(imagens=[]))
        self.assertTrue(antiga.exists())

    def test_rejeita_listagem_incompleta(self):
        sessao = self.sessao()
        sessao.get.side_effect = [
            resposta({"mimeType": PASTA_MIME}),
            resposta({"incompleteSearch": True}),
        ]
        with self.assertRaisesRegex(ValueError, "incompleta"):
            self.baixar(sessao)

    def test_entrada_local_nao_procura_credenciais(self):
        with patch.dict(os.environ, {}, clear=True), patch("google.auth.default") as auth:
            self.assertEqual(preparar_entrada({}, []), ("entrada", False))
            self.assertEqual(preparar_entrada({}, ["--entrada", "outra"]), ("outra", False))
            auth.assert_not_called()

    def test_drive_configurado_e_somente_baixar(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("google.auth.default", return_value=(MagicMock(), None)),
            patch("google.auth.transport.requests.AuthorizedSession"),
            patch("tcc_ocr.drive.baixar_entrada", return_value="importacao") as baixar,
        ):
            resultado = preparar_entrada(
                {"chaves_do_cofre": {}},
                ["--drive", "--somente-baixar"],
                {
                    "pasta_id": "configurada",
                    "pastas_atividades": {"ATV1": "chaves_do_cofre"},
                    "pastas_atividades_por_id": {"sinais_de_transito": "pasta-direta"},
                },
            )
            self.assertEqual(resultado, ("importacao", True))
            self.assertEqual(baixar.call_args.args[0], "configurada")
            self.assertEqual(
                baixar.call_args.kwargs["pastas_atividades_por_id"],
                {"sinais_de_transito": "pasta-direta"},
            )

    def test_url_explicita_tem_prioridade_sobre_configuracao(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("google.auth.default", return_value=(MagicMock(), None)),
            patch("google.auth.transport.requests.AuthorizedSession"),
            patch("tcc_ocr.drive.baixar_entrada", return_value="importacao") as baixar,
        ):
            preparar_entrada(
                {},
                ["--drive-folder", "outra"],
                {"pasta_id": "configurada"},
            )
            self.assertEqual(baixar.call_args.args[0], "outra")

    def test_exibe_diagnostico_real_de_escopo_insuficiente(self):
        http_resposta = MagicMock()
        http_resposta.json.return_value = {
            "error": {"message": "Request had insufficient authentication scopes."},
        }
        erro = HTTPError("403 Forbidden", response=http_resposta)
        saida = io.StringIO()
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("google.auth.default", return_value=(MagicMock(), None)),
            patch("google.auth.transport.requests.AuthorizedSession"),
            patch("tcc_ocr.drive.baixar_entrada", side_effect=erro),
            redirect_stderr(saida),
            self.assertRaises(SystemExit) as encerramento,
        ):
            preparar_entrada({}, ["--drive-folder", "raiz"])
        self.assertEqual(encerramento.exception.code, 1)
        self.assertIn("insufficient authentication scopes", saida.getvalue())

    def test_ambos_scripts_encerram_download_sem_inicializar_ocr(self):
        for nome in ("processar_turma", "interpretar_folha"):
            with self.subTest(script=nome):
                modulo = importlib.import_module(nome)
                with (
                    patch("tcc_ocr.cli.preparar_entrada", return_value=("baixada", True)),
                    patch("tcc_ocr.extracao.Extrator") as extrator,
                ):
                    self.assertEqual(modulo.main(["--drive", "--somente-baixar"]), 0)
                    extrator.assert_not_called()


if __name__ == "__main__":
    unittest.main()
