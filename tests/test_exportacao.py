import copy
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from tcc_ocr.persistencia import carregar, hash_arquivo
from tcc_ocr.planilha import filtrar_revisoes, gerar_planilha


class ExportacaoTest(unittest.TestCase):
    def test_limite_conta_apenas_status_das_questoes_sem_alterar_resultados(self):
        registros = [
            {"codigo_aluno": "A001", "q1": {"status": "ok"}},
            {
                "codigo_aluno": "A002",
                "q1": {"status": "revisar"},
                "q2": {"status": "ilegivel"},
                "_avisos_entrada": ["Conferir imagem"],
            },
            {"codigo_aluno": "A003", "q1": {"status": "revisar"}, "q2": {"status": "revisar"}},
        ]
        originais = {"chaves_do_cofre": registros}
        copia = copy.deepcopy(originais)
        filtrados, relatorio = filtrar_revisoes(originais)
        self.assertEqual(
            [item["codigo_aluno"] for item in filtrados["chaves_do_cofre"]], ["A001", "A002"]
        )
        self.assertEqual(relatorio["total_excluidos"], 1)
        self.assertEqual(relatorio["excluidos"][0]["questoes_revisar"], 2)
        self.assertEqual(originais, copia)

    def test_exclui_da_atividade_e_da_revisao_sem_excluir_outra_atividade_do_aluno(self):
        excluido = {
            "codigo_aluno": "A001",
            "q1": {"status": "revisar"},
            "q2": {"status": "revisar"},
        }
        mantido = {"codigo_aluno": "A001", "q1": {"status": "revisar"}}
        resultados = {"chaves_do_cofre": [excluido], "agua_para_todos": [mantido]}
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = gerar_planilha(resultados, destino=pasta)
            with_arquivo = load_workbook(arquivo)
            try:
                self.assertEqual(with_arquivo["Chaves do Cofre"].max_row, 1)
                self.assertEqual(with_arquivo["Água para Todos"].cell(2, 1).value, "A001")
                revisoes = list(with_arquivo["Revisar"].values)
                self.assertEqual(len(revisoes), 2)
                self.assertEqual(revisoes[1][1], "Água para Todos")
            finally:
                with_arquivo.close()
            relatorio = carregar(Path(pasta) / "relatorio_exportacao.json")
            self.assertEqual(relatorio["exportados"], 1)
            self.assertEqual(relatorio["total_excluidos"], 1)
            self.assertEqual(relatorio["sha256_planilha"], hash_arquivo(arquivo))

    def test_limite_zero_e_filtragem_total_mantem_planilha_valida(self):
        resultados = {"chaves_do_cofre": [{"codigo_aluno": "A001", "q1": {"status": "revisar"}}]}
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = gerar_planilha(resultados, destino=pasta, max_revisar=0)
            workbook = load_workbook(arquivo)
            try:
                self.assertEqual(workbook["Chaves do Cofre"].max_row, 1)
                self.assertEqual(workbook["Revisar"].max_row, 1)
            finally:
                workbook.close()
        for limite in (-1, 9, True):
            with self.subTest(limite=limite), self.assertRaises(ValueError):
                filtrar_revisoes(resultados, limite)

    def test_exporta_q8_e_mantem_revisao_da_atv4_na_planilha(self):
        resultado = {
            "codigo_aluno": "A001",
            "q8": {
                "mudou_resposta_ou_estrategia": True,
                "justificativa": "Conversei com um colega.",
                "status": "revisar",
            },
        }
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = gerar_planilha({"dinheiro_de_castor": [resultado]}, destino=pasta)
            workbook = load_workbook(arquivo)
            try:
                sheet = workbook["Dinheiro de Castor"]
                cabecalhos = [cell.value for cell in sheet[1]]
                self.assertIn("Q8 - Justificativa", cabecalhos)
                self.assertEqual(
                    sheet.cell(2, cabecalhos.index("Q8 - Mudou resposta/estratégia") + 1).value,
                    "Sim",
                )
                revisoes = list(workbook["Revisar"].values)
                self.assertEqual(revisoes[1][2], "Q8")
            finally:
                workbook.close()


if __name__ == "__main__":
    unittest.main()
