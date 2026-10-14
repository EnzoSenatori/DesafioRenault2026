import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from conferir import carregar_config
from detector import ErroDeteccao, converter_resposta, criar_cliente, ler_imagem
from testar_modelo import EXTENSOES, PASTA_IMAGENS, chave_natural

RAIZ = Path(__file__).resolve().parent.parent
PASTA_AVALIACAO = RAIZ / "saidas" / "avaliacao"
CLASSES = {"Pliers", "Screwdriver", "Wrench", "PipeWrench", "Hammer"}


# Valida o gabarito humano antes de qualquer chamada ao serviço.
def carregar_gabarito(caminho, imagens):
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise ValueError(f"Não foi possível ler o gabarito ({type(erro).__name__}) — confira o arquivo JSON") from erro
    if not isinstance(dados, dict):
        raise ValueError("O gabarito deve ser um objeto JSON com nomes de imagem")
    nomes = {imagem.name for imagem in imagens}
    extras = dados.keys() - nomes
    if not dados or extras:
        raise ValueError(f"Gabarito vazio ou com nomes incorretos — extras {sorted(extras)}")
    for nome, contagens in dados.items():
        if not isinstance(contagens, dict):
            raise ValueError(f"Gabarito de {nome} deve ser um objeto de contagens")
        for classe, quantidade in contagens.items():
            if classe not in CLASSES or type(quantidade) is not int or quantidade < 0:
                raise ValueError(f"Contagem inválida de {classe} em {nome} — use classe conhecida e inteiro não negativo")
    return dados


# Lê correspondências por modelo, sem aceitar mapeamentos para classes desconhecidas.
def carregar_mapeamentos(caminho):
    if caminho is None:
        return {}
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise ValueError(f"Não foi possível ler o mapeamento ({type(erro).__name__}) — confira o JSON") from erro
    if not isinstance(dados, dict) or any(not isinstance(v, dict) for v in dados.values()):
        raise ValueError("O mapeamento deve associar model_id a um objeto de classes")
    for modelo, mapa in dados.items():
        if any(not isinstance(origem, str) or destino not in CLASSES for origem, destino in mapa.items()):
            raise ValueError(f"Mapeamento inválido no modelo {modelo} — destinos permitidos: {sorted(CLASSES)}")
    return dados


# Converte nomes do detector apenas por igualdade exata ou de-para explícito.
def contar_deteccoes(deteccoes, mapa, limiar):
    contagens = Counter()
    desconhecidas = Counter()
    for deteccao in deteccoes:
        if deteccao["confianca"] < limiar:
            continue
        origem = deteccao["classe"]
        classe = mapa.get(origem, origem)
        if classe in CLASSES:
            contagens[classe] += 1
        else:
            desconhecidas[origem] += 1
    return contagens, desconhecidas


# Compara as contagens de uma imagem com o gabarito sem confundir ausência com acerto.
def avaliar_imagem(esperado, detectado):
    classes = sorted(set(esperado) | set(detectado))
    faltas = {classe: max(esperado.get(classe, 0) - detectado.get(classe, 0), 0) for classe in classes}
    excessos = {classe: max(detectado.get(classe, 0) - esperado.get(classe, 0), 0) for classe in classes}
    return {
        "contagem_exata": all(esperado.get(c, 0) == detectado.get(c, 0) for c in classes),
        "itens_corretos": sum(min(esperado.get(c, 0), detectado.get(c, 0)) for c in classes),
        "faltas": sum(faltas.values()),
        "excessos": sum(excessos.values()),
        "detalhe_faltas": {c: n for c, n in faltas.items() if n},
        "detalhe_excessos": {c: n for c, n in excessos.items() if n},
    }


# Mantém o nome do modelo em um caminho seguro para salvar o resultado.
def nome_arquivo_modelo(modelo):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", modelo) + ".json"


# Executa um modelo nas imagens gabaritadas e registra respostas e erros.
def avaliar_modelo(modelo, imagens, gabarito, mapa, config, cliente, pasta=PASTA_AVALIACAO):
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = []
    fixture_salva = False
    for imagem in imagens:
        try:
            resposta = cliente.infer(ler_imagem(imagem), model_id=modelo)
            deteccoes = converter_resposta(resposta)
        except Exception as erro:
            linhas.append({"imagem": imagem.name, "erro": type(erro).__name__})
            continue
        if not fixture_salva:
            caminho_fixture = pasta / f"resposta_{nome_arquivo_modelo(modelo)}"
            caminho_fixture.write_text(json.dumps(resposta, indent=2, ensure_ascii=False), encoding="utf-8")
            fixture_salva = True
        contagens, desconhecidas = contar_deteccoes(deteccoes, mapa, config["limiar_confianca"])
        medidas = avaliar_imagem(gabarito[imagem.name], contagens)
        if desconhecidas:
            medidas["contagem_exata"] = False
        linhas.append({"imagem": imagem.name, "esperado": gabarito[imagem.name],
                      "detectado": dict(contagens), "classes_nao_mapeadas": dict(desconhecidas), **medidas})
    validas = [linha for linha in linhas if "erro" not in linha]
    resumo = {
        "modelo_id": modelo,
        "limiar_confianca": config["limiar_confianca"],
        "imagens_total": len(imagens),
        "imagens_avaliadas": len(validas),
        "imagens_com_contagem_exata": sum(linha["contagem_exata"] for linha in validas),
        "itens_corretos": sum(linha["itens_corretos"] for linha in validas),
        "faltas": sum(linha["faltas"] for linha in validas),
        "excessos": sum(linha["excessos"] for linha in validas),
        "erros": len(linhas) - len(validas),
        "imagens": linhas,
    }
    (pasta / nome_arquivo_modelo(modelo)).write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    return resumo


# Prepara a avaliação, imprime uma linha por modelo e deixa a escolha com Rafael.
def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Compara modelos de detecção com contagens conferidas por pessoa.")
    parser.add_argument("--modelos", nargs="+", required=True, help="model_id de cada candidato")
    parser.add_argument("--gabarito", default=str(PASTA_IMAGENS / "gabarito.json"))
    parser.add_argument("--mapeamento", help="JSON opcional: model_id -> classe original -> classe canônica")
    args = parser.parse_args(argumentos)
    imagens = sorted((p for p in PASTA_IMAGENS.iterdir() if p.suffix.lower() in EXTENSOES), key=chave_natural)
    try:
        gabarito = carregar_gabarito(args.gabarito, imagens)
        imagens = [imagem for imagem in imagens if imagem.name in gabarito]
        mapeamentos = carregar_mapeamentos(args.mapeamento)
        config = carregar_config()
        cliente = criar_cliente(config)
    except (ValueError, ErroDeteccao) as erro:
        print(f"Preparação interrompida: {erro}", file=sys.stderr)
        return 2
    print("Modelo | Imagens exatas | Itens corretos | Faltas | Excessos | Erros")
    for modelo in dict.fromkeys(args.modelos):
        resumo = avaliar_modelo(modelo, imagens, gabarito, mapeamentos.get(modelo, {}), config, cliente)
        print(f"{modelo} | {resumo['imagens_com_contagem_exata']}/{resumo['imagens_avaliadas']} | "
              f"{resumo['itens_corretos']} | {resumo['faltas']} | {resumo['excessos']} | {resumo['erros']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
