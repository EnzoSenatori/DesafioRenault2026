import json
from pathlib import Path

from conferir import conferir, main

RAIZ = Path(__file__).resolve().parent.parent
IMAGEM = RAIZ / "imagens" / "teste" / "Img 16.jpg"
OUTRA_IMAGEM = RAIZ / "imagens" / "teste" / "Img 15.jpg"
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


# Devolve uma chave ajustável e uma de grifo, como a Img 16 no modelo adotado.
class ClienteDuasChaves:
    # Responde igual para qualquer modelo; não há caixa aberta nessa resposta.
    def infer(self, imagem, model_id=None):
        return {"predictions": [
            {"x": 180, "y": 290, "width": 120, "height": 400, "confidence": 0.99, "class": "Adjustable Wrench"},
            {"x": 330, "y": 290, "width": 120, "height": 400, "confidence": 0.99, "class": "Pipe Wrench"},
        ]}


# Cliente que falha se for chamado: prova que a reprodução não usa a rede.
class ClienteProibido:
    # Qualquer chamada é um erro do teste.
    def infer(self, imagem, model_id=None):
        raise AssertionError("a reprodução não deveria chamar o Roboflow")


# Grava uma nota que pede uma chave ajustável.
def escrever_nota(pasta):
    caminho = pasta / "nota.json"
    caminho.write_text(json.dumps({"nota_id": "NF-R", "itens": [
        {"codigo": "FER-003", "descricao": "Chave inglesa ajustável", "quantidade": 1}
    ]}), encoding="utf-8")
    return caminho


# Uma execução grava as respostas e a reprodução chega ao mesmo resultado, sem rede e com aviso.
def test_grava_e_reproduz_sem_rede(tmp_path):
    nota = escrever_nota(tmp_path)
    original, pasta = conferir(IMAGEM, nota, pasta_saida=tmp_path / "gravada", config=CONFIG,
                               cliente=ClienteDuasChaves(), sem_caixas=True)
    gravado = json.loads((pasta / "respostas_brutas.json").read_text(encoding="utf-8"))
    assert [c["modelo_id"] for c in gravado["chamadas"]] == [CONFIG["model_id"]]

    reproduzido, pasta_nova = conferir(IMAGEM, nota, pasta_saida=tmp_path / "reproduzida", config=CONFIG,
                                       cliente=ClienteProibido(), sem_caixas=True, reproduzir=pasta)
    assert reproduzido["status"] == original["status"] == "divergente"
    assert reproduzido["linhas"] == original["linhas"]
    assert "Reprodução offline" in reproduzido["avisos"][-1]
    assert (pasta_nova / "imagem_anotada.jpg").exists()


# Reproduzir com opções ou imagem diferentes da gravação dá erro, nunca conforme.
def test_reproducao_incompativel_vira_erro(tmp_path):
    nota = escrever_nota(tmp_path)
    _, pasta = conferir(IMAGEM, nota, pasta_saida=tmp_path / "gravada", config=CONFIG,
                        cliente=ClienteDuasChaves(), sem_caixas=True)
    com_caixas, _ = conferir(IMAGEM, nota, pasta_saida=tmp_path / "r1", config=CONFIG, reproduzir=pasta)
    outra_imagem, _ = conferir(OUTRA_IMAGEM, nota, pasta_saida=tmp_path / "r2", config=CONFIG,
                               sem_caixas=True, reproduzir=pasta)
    assert com_caixas["status"] == outra_imagem["status"] == "erro"
    assert "não corresponde à gravação" in com_caixas["avisos"][0]


# Pasta sem gravação vira erro pela CLI, com código de saída 2.
def test_reproducao_sem_arquivo_vira_erro(tmp_path, capsys):
    nota = escrever_nota(tmp_path)
    codigo = main(["--imagem", str(IMAGEM), "--nota", str(nota), "--saida", str(tmp_path / "s"),
                   "--reproduzir", str(tmp_path / "vazia"), "--json"])
    assert codigo == 2
    assert "respostas_brutas.json" in capsys.readouterr().out
