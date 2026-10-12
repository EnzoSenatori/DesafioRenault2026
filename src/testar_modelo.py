import json
import sys
from collections import Counter
from pathlib import Path

from conferir import carregar_config
from detector import ErroDeteccao, converter_resposta, criar_cliente, ler_imagem
from visualizacao import desenhar_caixas, salvar_jpg

RAIZ = Path(__file__).resolve().parent.parent
PASTA_IMAGENS = RAIZ / "imagens" / "teste"
PASTA_SAIDA = RAIZ / "saidas" / "fumaca"
PASTA_FIXTURES = RAIZ / "fixtures"
EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


# Grava a resposta bruta do Roboflow em fixtures/
def salvar_fixture(nome_arquivo, resposta):
    PASTA_FIXTURES.mkdir(exist_ok=True)
    with open(PASTA_FIXTURES / nome_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(resposta, arquivo, indent=2, ensure_ascii=False)


# Ordena "Img 2" antes de "Img 10"
def chave_natural(caminho):
    digitos = "".join(c for c in caminho.stem if c.isdigit())
    return (int(digitos) if digitos else 0, caminho.stem)


# Roda o modelo em todas as imagens de teste, salva as anotadas e imprime o resumo
def main():
    config = carregar_config()
    if not PASTA_IMAGENS.is_dir():
        sys.exit(f"Pasta {PASTA_IMAGENS} não encontrada — coloque as imagens de teste nela")
    imagens = sorted((p for p in PASTA_IMAGENS.iterdir() if p.suffix.lower() in EXTENSOES), key=chave_natural)
    if not imagens:
        sys.exit(f"Nenhuma imagem em {PASTA_IMAGENS} — coloque as imagens de teste nela")

    try:
        cliente = criar_cliente(config)
    except ErroDeteccao as erro:
        sys.exit(str(erro))
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    limiar = config["limiar_confianca"]
    fixtures_existem = (PASTA_FIXTURES / "resposta_roboflow.json").exists()
    com_deteccao_salva = (PASTA_FIXTURES / "resposta_roboflow_com_deteccoes.json").exists()
    resumo = []

    for caminho in imagens:
        try:
            imagem = ler_imagem(caminho)
            resposta = cliente.infer(imagem, model_id=config["model_id"])
            deteccoes = converter_resposta(resposta)
        except Exception as erro:
            print(f"[{caminho.name}] ERRO: {erro}")
            resumo.append({"imagem": caminho.name, "erro": str(erro)})
            continue

        if not fixtures_existem:
            salvar_fixture("resposta_roboflow.json", resposta)
            fixtures_existem = True
        if deteccoes and not com_deteccao_salva:
            salvar_fixture("resposta_roboflow_com_deteccoes.json", resposta)
            com_deteccao_salva = True

        salvar_jpg(PASTA_SAIDA / f"{caminho.stem}.jpg", desenhar_caixas(imagem, deteccoes, config))

        aceitas = [d for d in deteccoes if d["confianca"] >= limiar]
        descartadas = [d for d in deteccoes if d["confianca"] < limiar]
        print(f"[{caminho.name}] {imagem.shape[1]}x{imagem.shape[0]}")
        for d in sorted(deteccoes, key=lambda d: -d["confianca"]):
            marca = "" if d["confianca"] >= limiar else "  (abaixo do limiar)"
            print(f"    {d['classe']:<12} {d['confianca']:.3f}{marca}")
        if not deteccoes:
            print("    nenhuma detecção")
        resumo.append({
            "imagem": caminho.name,
            "aceitas": [{"classe": d["classe"], "confianca": round(d["confianca"], 3)} for d in aceitas],
            "descartadas": [{"classe": d["classe"], "confianca": round(d["confianca"], 3)} for d in descartadas],
            "contagem": dict(Counter(d["classe"] for d in aceitas)),
        })

    with open(PASTA_SAIDA / "resumo.json", "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, indent=2, ensure_ascii=False)
    print(f"\nImagens anotadas e resumo.json em {PASTA_SAIDA}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
