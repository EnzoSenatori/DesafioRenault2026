import json
import subprocess
import sys
from pathlib import Path

import pytest


RAIZ = Path(__file__).resolve().parent.parent


# Executa a mesma interface de comando que outro sistema usaria, sem rede.
def executar_cli(imagem, nota, saida, reserva=None):
    comando = [
        sys.executable, str(RAIZ / "src" / "conferir.py"),
        "--imagem", str(imagem), "--nota", str(nota),
        "--saida", str(saida), "--json",
    ]
    if reserva is not None:
        comando.extend(["--sem-caixas", "--reproduzir", str(reserva)])
    return subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")


# Confere JSON, código de saída e arquivos dos cenários gravados para integração.
@pytest.mark.parametrize("nome_imagem,nome_nota,nome_reserva,status,codigo", [
    ("Img 15.jpg", "nota_conforme.json", "img15_conforme", "conforme", 0),
    ("Img 16.jpg", "nota_divergente.json", "img16_divergente", "divergente", 1),
])
def test_cli_offline_para_consumidor_externo(tmp_path, nome_imagem, nome_nota,
                                            nome_reserva, status, codigo):
    imagem = RAIZ / "imagens" / "teste" / nome_imagem
    nota = RAIZ / "notas" / nome_nota
    reserva = RAIZ / "docs" / "reserva" / nome_reserva
    saida = tmp_path / "recebimento"

    processo = executar_cli(imagem, nota, saida, reserva)

    assert processo.returncode == codigo, processo.stderr
    resposta = json.loads(processo.stdout)
    relatorio = json.loads((saida / "relatorio.json").read_text(encoding="utf-8"))
    assert resposta["status"] == relatorio["status"] == status
    assert resposta["pasta_saida"] == str(saida)
    assert (saida / "imagem_anotada.jpg").stat().st_size > 0
    assert (saida / "respostas_brutas.json").exists()
    assert any("Reprodução offline" in aviso for aviso in relatorio["avisos"])


# Entrada inválida deve produzir erro estruturado, sem consultar o Roboflow.
def test_cli_nota_ausente_retorna_erro_estruturado(tmp_path):
    imagem = RAIZ / "imagens" / "teste" / "Img 15.jpg"
    saida = tmp_path / "recebimento_invalido"

    processo = executar_cli(imagem, tmp_path / "nota_inexistente.json", saida)

    assert processo.returncode == 2, processo.stderr
    resposta = json.loads(processo.stdout)
    relatorio = json.loads((saida / "relatorio.json").read_text(encoding="utf-8"))
    assert resposta["status"] == relatorio["status"] == "erro"
    assert relatorio["avisos"]
    assert (saida / "imagem_anotada.jpg").exists()
