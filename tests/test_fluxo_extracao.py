import copy
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

from google.api_core.exceptions import PermissionDenied, TooManyRequests
from PIL import Image

import tcc_ocr.cli as app
import tcc_ocr.extracao as extracao
from tcc_ocr.atividades import CONFIGURACOES
from tcc_ocr.avaliacao import avaliar, preparar_avaliacao
from tcc_ocr.configuracoes import carregar_configuracao
from tcc_ocr.extracao import Extrator
from tcc_ocr.fluxo import (
    carregar,
    enriquecer_fontes,
    executar_lote,
    salvar_atomico,
    tentar,
    validar_entrada,
)
from tcc_ocr.normalizacao import normalizar_resultado
from tcc_ocr.planilha import gerar_linhas_revisao, gerar_planilha
from tcc_ocr.prompts import montar_prompt_unico
from tcc_ocr.validacao import validar_resultado

QUESTAO = {
    "type": "OBJECT",
    "properties": {
        "valor": {"type": "STRING", "nullable": True},
        "status": {"type": "STRING", "enum": ["ok", "revisar", "ilegivel"]},
    },
    "required": ["valor", "status"],
}
CONFIG = {
    "teste": {
        "nome": "Teste",
        "modo_entrada": "unica_imagem",
        "schema": {
            "type": "OBJECT",
            "properties": {
                "atividade": {"type": "STRING"},
                **{f"q{i}": copy.deepcopy(QUESTAO) for i in range(1, 8)},
            },
            "required": ["atividade"] + [f"q{i}" for i in range(1, 8)],
        },
    }
}
RESULTADO = {"atividade": "Teste", **{f"q{i}": {"valor": "A", "status": "ok"} for i in range(1, 8)}}


class FluxoTest(unittest.TestCase):
    def setUp(self):
        self.config = carregar_configuracao()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        self.entrada = self.raiz / "entrada"
        self.saida = self.raiz / "resultados"
        self.imagem()
        self.ocr = MagicMock(return_value={"texto": "Texto da resposta", "paginas": []})
        self.interpretar = MagicMock(side_effect=lambda *_: copy.deepcopy(RESULTADO))
        self.inicializar = MagicMock()
        self.stdout = redirect_stdout(io.StringIO())
        self.stdout.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)

    def imagem(self, nome="A001_resposta.jpg", cor="white"):
        pasta = self.entrada / "teste"
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / nome
        Image.new("RGB", (800, 1000), cor).save(caminho)
        return caminho

    def executar(self, **opcoes):
        argumentos = {
            "entrada": self.entrada,
            "pasta_resultados": self.saida,
            "configuracoes": CONFIG,
            "ocr": self.ocr,
            "interpretar": self.interpretar,
            "normalizar": normalizar_resultado,
            "assinatura_interpretacao": {"teste": "prompt1"},
            "config_ocr": {"processor": "1"},
            "modelo": "modelo",
            "versao": "3",
            "inicializar": self.inicializar,
        }
        argumentos.update(opcoes)
        return executar_lote(**argumentos)

    def test_atv3_e_atv4_aceitam_uma_imagem_de_resposta_por_producao(self):
        configuracoes = {
            atividade: CONFIGURACOES[atividade]
            for atividade in ("sinais_de_transito", "dinheiro_de_castor")
        }
        for atividade in configuracoes:
            pasta = self.entrada / atividade
            pasta.mkdir()
            Image.new("RGB", (800, 1000), "white").save(pasta / "A001_resposta.jpg")
        validacao = validar_entrada(self.entrada, configuracoes)
        registros = validacao["registros"]
        self.assertEqual(
            {(item["atividade"], item["codigo"], item["estado"]) for item in registros},
            {
                ("sinais_de_transito", "A001", "pendente"),
                ("dinheiro_de_castor", "A001", "pendente"),
            },
        )
        self.assertTrue(all(not item["erros_validacao"] for item in registros))

    def test_normalizacao_sinaliza_incerteza_em_q8(self):
        resultado = normalizar_resultado(
            {"q8": {"justificativa": "Parece que mudou", "status": "ok"}}
        )
        self.assertEqual(resultado["q8"]["status"], "revisar")
        self.assertIn("q8", resultado["_motivos_revisao"])

    def test_schemas_preservam_campos_em_branco_da_atv3_e_atv4(self):
        for atividade, configuracao in (
            ("sinais_de_transito", CONFIGURACOES["sinais_de_transito"]),
            ("dinheiro_de_castor", CONFIGURACOES["dinheiro_de_castor"]),
        ):
            resultado = {"atividade": configuracao["nome"]}
            for chave, questao in configuracao["schema"]["properties"].items():
                if not chave.startswith("q"):
                    continue
                resultado[chave] = {
                    campo: None for campo in questao["properties"] if campo != "status"
                }
                resultado[chave]["status"] = "ok"
            if atividade == "sinais_de_transito":
                resultado["q3"]["testou_significado"] = False
            else:
                resultado["q4"]["testou_combinacao"] = False
                resultado["q5"]["resposta"] = None
                resultado["q8"]["mudou_resposta_ou_estrategia"] = False
            validado = validar_resultado(resultado, configuracao)
            if atividade == "sinais_de_transito":
                self.assertFalse(validado["q3"]["testou_significado"])
            else:
                self.assertFalse(validado["q4"]["testou_combinacao"])
                self.assertIsNone(validado["q5"]["resposta"])
                self.assertFalse(validado["q8"]["mudou_resposta_ou_estrategia"])

    def test_validacao_detecta_duplicidade_pares_e_imagens_corrompidas(self):
        self.imagem("a001_RESPOSTA.png")
        config = copy.deepcopy(CONFIG)
        config["teste"]["modo_entrada"] = "questao_resposta"
        dados = validar_entrada(self.entrada, config)
        erros = dados["registros"][0]["erros_validacao"]
        self.assertTrue(any("Mais de uma" in erro for erro in erros))
        self.assertTrue(any("ausente" in erro for erro in erros))
        (self.entrada / "teste/A002_resposta.jpg").write_bytes(b"quebrada")
        relatorio, resultados = self.executar()
        self.assertEqual(relatorio["estado"], "entrada_invalida")
        self.assertIsNone(resultados)
        self.inicializar.assert_not_called()
        self.ocr.assert_not_called()

    def test_cache_independente_de_ocr_e_prompt(self):
        primeiro, resultados = self.executar()
        self.assertEqual(primeiro["estado"], "concluido")
        self.assertEqual(resultados["teste"][0]["q1"]["valor"], "A")
        self.ocr.reset_mock()
        self.interpretar.reset_mock()
        segundo, _ = self.executar()
        self.assertEqual(segundo["resumo"]["reaproveitado"], 1)
        self.ocr.assert_not_called()
        self.interpretar.assert_not_called()
        self.executar(assinatura_interpretacao={"teste": "prompt2"})
        self.ocr.assert_not_called()
        self.interpretar.assert_called_once()
        self.imagem(cor="black")
        self.executar(assinatura_interpretacao={"teste": "prompt2"})
        self.ocr.assert_called_once()
        self.assertEqual(self.interpretar.call_count, 2)

    def test_alterar_config_ocr_invalida_as_duas_etapas(self):
        self.executar()
        self.ocr.reset_mock()
        self.interpretar.reset_mock()
        self.executar(config_ocr={"processor": "2"})
        self.ocr.assert_called_once()
        self.interpretar.assert_called_once()

    def test_forcar_ignora_ambos_caches(self):
        self.executar()
        self.executar(forcar=True)
        self.assertEqual(self.ocr.call_count, 2)
        self.assertEqual(self.interpretar.call_count, 2)

    def test_retomada_preserva_sucessos_e_reusa_ocr_da_falha(self):
        self.imagem("A002_resposta.jpg", "black")
        self.interpretar.side_effect = [copy.deepcopy(RESULTADO), PermissionDenied("negado")]
        primeiro, resultados = self.executar()
        self.assertEqual(primeiro["estado"], "parcial")
        self.assertEqual(len(resultados["teste"]), 1)
        falha = next(item for item in primeiro["registros"] if item["estado"] == "erro")
        self.assertEqual(falha["etapa"], "interpretacao")
        self.ocr.reset_mock()
        self.interpretar.reset_mock(side_effect=True)
        self.interpretar.side_effect = lambda *_: copy.deepcopy(RESULTADO)
        segundo, resultados = self.executar(retomar=True)
        self.assertEqual(segundo["estado"], "concluido")
        self.assertEqual(segundo["resumo"]["reaproveitado"], 1)
        self.assertEqual(len(resultados["teste"]), 2)
        self.ocr.assert_not_called()
        self.interpretar.assert_called_once()

    def test_falha_de_autorizacao_interrompe_demais_chamadas_e_deixa_pendentes(self):
        self.imagem("A002_resposta.jpg", "black")
        self.imagem("A003_resposta.jpg", "red")
        self.interpretar.side_effect = PermissionDenied("negado")
        relatorio, _ = self.executar()
        self.assertEqual(relatorio["estado"], "parcial")
        self.assertEqual(relatorio["resumo"]["erro"], 1)
        self.assertEqual(relatorio["resumo"]["pendente"], 2)
        self.ocr.assert_called_once()
        self.interpretar.assert_called_once()

    def test_interrupcao_tem_checkpoint_e_pode_ser_retomada(self):
        self.interpretar.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.executar()
        anterior = carregar(self.saida / "relatorio_execucao.json")
        self.assertEqual(anterior["registros"][0]["estado"], "processando")
        self.ocr.reset_mock()
        self.interpretar.side_effect = lambda *_: copy.deepcopy(RESULTADO)
        atual, _ = self.executar(retomar=True)
        self.assertEqual(atual["estado"], "concluido")
        self.ocr.assert_not_called()

    def test_repeticao_apenas_para_falhas_transitorias(self):
        funcao = MagicMock(side_effect=[TooManyRequests("quota"), "ok"])
        espera = MagicMock()
        self.assertEqual(tentar(funcao, esperar=espera), "ok")
        espera.assert_called_once_with(1)
        permanente = MagicMock(side_effect=PermissionDenied("negado"))
        with self.assertRaises(PermissionDenied):
            tentar(permanente, esperar=espera)
        permanente.assert_called_once()

    def test_resposta_fora_schema_falha_sem_ser_salva(self):
        invalido = copy.deepcopy(RESULTADO)
        invalido["q1"]["valor"] = 10
        self.interpretar.side_effect = lambda *_: invalido
        relatorio, resultados = self.executar()
        self.assertEqual(relatorio["resumo"]["erro"], 1)
        self.assertEqual(resultados["teste"], [])
        self.assertFalse((self.saida / "teste/A001.json").exists())
        self.interpretar.assert_called_once()

    def test_falha_nova_nao_inclui_resultado_antigo_na_planilha_parcial(self):
        self.executar()
        self.interpretar.side_effect = PermissionDenied("negado")
        _, resultados = self.executar(assinatura_interpretacao={"teste": "mudou"})
        self.assertEqual(resultados["teste"], [])
        self.assertTrue((self.saida / "teste/A001.json").exists())

    def test_identificacao_removida_e_fontes_salvas(self):
        resultado = {**RESULTADO, "nome_estudante": "não salvar", "nome_status": "ok", "ano": "5"}
        self.interpretar.side_effect = lambda *_: copy.deepcopy(resultado)
        self.executar()
        salvo = carregar(self.saida / "teste/A001.json")
        self.assertFalse({"nome_estudante", "nome_status", "ano"}.intersection(salvo))
        self.assertEqual(
            salvo["_fontes"]["resposta"]["local"],
            str((self.entrada / "teste/A001_resposta.jpg").resolve()),
        )

    def test_ocr_das_duas_imagens_e_reutilizacao_por_conteudo(self):
        self.imagem("A001_questao.jpg", "black")
        config = copy.deepcopy(CONFIG)
        config["teste"]["modo_entrada"] = "questao_resposta"
        self.executar(configuracoes=config)
        self.assertEqual(self.ocr.call_count, 2)
        texto = self.interpretar.call_args.args[1]
        self.assertIn("OCR DA IMAGEM QUESTAO", texto)
        self.assertIn("OCR DA IMAGEM RESPOSTA", texto)

    def test_cache_corrompido_e_recalculado(self):
        self.executar()
        cache = next((self.saida / ".cache_ocr").glob("*.json"))
        cache.write_text("{invalido")
        self.ocr.reset_mock()
        self.executar(assinatura_interpretacao={"teste": "mudou"})
        self.ocr.assert_called_once()

    def test_assinatura_inclui_modelo_prompt_e_schema(self):
        primeira = Extrator(self.config).assinaturas_interpretacao(CONFIGURACOES)
        outra = replace(self.config, modelo_gemini="outro")
        self.assertNotEqual(primeira, Extrator(outra).assinaturas_interpretacao(CONFIGURACOES))
        with patch.object(extracao, "montar_prompt_unico", return_value="outro prompt"):
            self.assertNotEqual(
                primeira, Extrator(self.config).assinaturas_interpretacao(CONFIGURACOES)
            )
        configuracoes = copy.deepcopy(CONFIGURACOES)
        configuracoes["chaves_do_cofre"]["schema"]["properties"]["atividade"]["description"] = (
            "mudou"
        )
        self.assertNotEqual(
            primeira, Extrator(self.config).assinaturas_interpretacao(configuracoes)
        )

    def test_schema_e_prompts_nao_solicitam_nome_ou_ano(self):
        for config in CONFIGURACOES.values():
            self.assertFalse(
                {"nome_estudante", "nome_status", "ano"}.intersection(
                    config["schema"]["properties"]
                )
            )
            self.assertFalse(
                {"nome_estudante", "nome_status", "ano"}.intersection(config["schema"]["required"])
            )
        self.assertNotIn(
            "NOME DO ESTUDANTE:", montar_prompt_unico("", CONFIGURACOES["chaves_do_cofre"])
        )

    def test_revisao_tem_motivo_e_fontes_e_qualidade(self):
        resultado = copy.deepcopy(RESULTADO)
        resultado["q1"]["status"] = "revisar"
        resultado.update(
            {
                "codigo_aluno": "A001",
                "_fontes": {"resposta": {"local": str(self.imagem())}},
                "_qualidade_imagens": {
                    "resposta": [
                        {
                            "qualidade": 0.3,
                            "defeitos": [{"tipo": "quality/defect_blurry", "confianca": 0.9}],
                        }
                    ]
                },
            }
        )
        linhas = gerar_linhas_revisao(resultado, "Teste")
        self.assertEqual(len(linhas), 2)
        self.assertTrue(linhas[0]["Abrir resposta"].startswith("file:///"))
        self.assertTrue(linhas[0]["Motivo"])
        self.assertIn("blurry", linhas[1]["Motivo"])

    def test_gravacao_atomica_preserva_conteudo_anterior_quando_rename_falha(self):
        caminho = self.raiz / "arquivo.json"
        salvar_atomico(caminho, {"anterior": True})
        with patch("tcc_ocr.persistencia.os.replace", side_effect=PermissionError("bloqueado")):
            with self.assertRaises(PermissionError):
                salvar_atomico(caminho, {"novo": True})
        self.assertEqual(carregar(caminho), {"anterior": True})

    def test_amostra_reproduzivel_sem_referencias_inventadas(self):
        _, resultados = self.executar()
        a = preparar_avaliacao(resultados, CONFIG, self.raiz / "a.json", 1, 42)
        b = preparar_avaliacao(resultados, CONFIG, self.raiz / "b.json", 1, 42)
        self.assertEqual(a, b)
        self.assertTrue(all(not item["conferido"] for item in a["itens"]))
        self.assertTrue(
            all(valor is None for item in a["itens"] for valor in item["referencia"].values())
        )
        vazio = avaliar(self.raiz / "a.json", resultados, CONFIG, self.raiz / "metricas.json")
        self.assertIsNone(vazio["concordancia_exata"])
        with self.assertRaises(ValueError):
            preparar_avaliacao(resultados, CONFIG, self.raiz / "a.json")

    def test_amostra_manual_inclui_q8_da_atv4(self):
        configuracoes = {"dinheiro_de_castor": CONFIGURACOES["dinheiro_de_castor"]}
        registro = {
            "codigo_aluno": "A001",
            **{f"q{numero}": {"status": "ok"} for numero in range(1, 9)},
        }
        documento = preparar_avaliacao(
            {"dinheiro_de_castor": [registro]},
            configuracoes,
            self.raiz / "atv4.json",
            1,
        )
        self.assertIn(
            ("dinheiro_de_castor", "A001", "q8"),
            {(item["atividade"], item["codigo"], item["questao"]) for item in documento["itens"]},
        )

    def test_avaliacao_identifica_divergencias_inclusive_marcadas_ok(self):
        _, resultados = self.executar()
        caminho = self.raiz / "referencia.json"
        documento = preparar_avaliacao(resultados, CONFIG, caminho, 1)
        for i, item in enumerate(documento["itens"]):
            item["conferido"] = True
            item["referencia"]["valor"] = "B" if i == 0 else " A "
        salvar_atomico(caminho, documento)
        relatorio = avaliar(caminho, resultados, CONFIG, self.raiz / "metricas.json")
        self.assertEqual(relatorio["campos_conferidos"], 7)
        self.assertEqual(relatorio["campos_concordantes"], 6)
        self.assertEqual(relatorio["divergencias_marcadas_ok"], 1)
        resultados["teste"][0]["q1"]["valor"] = "C"
        with self.assertRaisesRegex(ValueError, "mudou"):
            avaliar(caminho, resultados, CONFIG, self.raiz / "metricas.json")

    def test_offline_e_validacao_nao_inicializam_clientes(self):
        with (
            patch("tcc_ocr.extracao.Extrator") as extrator,
            patch.object(app, "preparar_entrada", return_value=(str(self.entrada), False)),
            patch.object(app, "CONFIGURACOES", CONFIG),
        ):
            self.assertEqual(app.main(["--validar", "--resultados", str(self.saida)]), 0)
            self.executar()
            with patch("tcc_ocr.planilha.gerar_planilha") as planilha:
                self.assertEqual(
                    app.main(["--somente-planilha", "--resultados", str(self.saida)]), 0
                )
                planilha.assert_called_once()
            extrator.assert_not_called()

    def test_fontes_legadas_exigem_hash_correspondente(self):
        _, resultados = self.executar()
        registro = resultados["teste"][0]
        registro.pop("_fontes")
        enriquecer_fontes(resultados, self.raiz)
        self.assertIn("resposta", registro["_fontes"])
        registro.pop("_fontes")
        self.imagem(cor="black")
        enriquecer_fontes(resultados, self.raiz)
        self.assertEqual(registro["_fontes"], {})

    def test_ocr_pede_qualidade_e_preserva_metricas_sem_chamada_real(self):
        from google.cloud import documentai_v1 as documentai

        pagina = documentai.Document.Page(
            page_number=1,
            image_quality_scores=documentai.Document.Page.ImageQualityScores(
                quality_score=0.4,
                detected_defects=[{"type_": "quality/defect_blurry", "confidence": 0.9}],
            ),
        )
        cliente = MagicMock()
        cliente.process_document.return_value.document = documentai.Document(
            text="Texto", pages=[pagina]
        )
        with Extrator(self.config) as extrator:
            extrator._document_ai_client = cliente
            dados = extrator.executar_ocr(str(self.imagem()))
        self.assertEqual(dados["texto"], "Texto")
        self.assertAlmostEqual(dados["paginas"][0]["qualidade"], 0.4)
        pedido = cliente.process_document.call_args.kwargs["request"]
        self.assertTrue(pedido.process_options.ocr_config.enable_image_quality_scores)
        cliente.transport.close.assert_called_once()

    def test_excel_tem_links_pendencias_e_preserva_transcricao_literal(self):
        from openpyxl import load_workbook

        registro = {
            "codigo_aluno": "A001",
            "q1": {"status": "revisar", "alternativa": "A"},
            "q3": {"resposta": "=2+2", "status": "ok"},
            "_fontes": {"resposta": {"local": str(self.imagem())}},
        }
        gerar_planilha(
            {"chaves_do_cofre": [registro]},
            destino=self.saida,
            relatorio={
                "estado": "parcial",
                "resumo": {"processado": 1, "erro": 1},
                "registros": [
                    {
                        "atividade": "chaves_do_cofre",
                        "codigo": "A002",
                        "estado": "erro",
                        "etapa": "ocr",
                        "erro": {"tipo": "PermissionDenied"},
                    }
                ],
            },
        )
        workbook = load_workbook(self.saida / "resultado_turma.xlsx")
        self.addCleanup(workbook.close)
        self.assertIn("Execução", workbook.sheetnames)
        self.assertIn("Erros", workbook.sheetnames)
        valores = list(workbook["Revisar"].values)
        indice = valores[0].index("Abrir resposta") + 1
        self.assertTrue(workbook["Revisar"].cell(2, indice).hyperlink.target.startswith("file:///"))
        folha = workbook["Chaves do Cofre"]
        indice = list(next(folha.values)).index("Q3 - Resposta") + 1
        self.assertEqual(folha.cell(2, indice).value, "=2+2")
        self.assertEqual(folha.cell(2, indice).data_type, "s")
        self.assertFalse({"Nome", "Nome - Status", "Ano"}.intersection(next(folha.values)))

    def test_erro_de_exportacao_preserva_planilha_anterior(self):
        self.saida.mkdir()
        arquivo = self.saida / "resultado_turma.xlsx"
        arquivo.write_bytes(b"planilha anterior")
        with patch("tcc_ocr.planilha._escrever_planilha", side_effect=OSError("arquivo bloqueado")):
            with self.assertRaises(OSError):
                gerar_planilha({}, destino=self.saida)
        self.assertEqual(arquivo.read_bytes(), b"planilha anterior")


if __name__ == "__main__":
    unittest.main()
