import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from comparador import comparar, resultado_erro
from caixas import desenhar_caixas_embalagem, detectar_caixas_e_produtos, salvar_recortes_internos
from detector import ErroDeteccao, detectar, ler_imagem
from nota import ErroEntrada, carregar_nota
from posprocessamento import consolidar_deteccoes
from reproducao import ClienteGravador, ClienteReproducao, carregar_respostas, hash_imagem, salvar_respostas
from visualizacao import desenhar_caixas, imagem_vazia, montar_evidencia, salvar_jpg

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SAIDAS = RAIZ / "saidas"

# Código de saída do processo para cada status (útil para quem orquestra)
CODIGOS_SAIDA = {"conforme": 0, "divergente": 1, "erro": 2}


# Lê o config.json da raiz do projeto
def carregar_config(caminho=RAIZ / "config.json"):
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (OSError, json.JSONDecodeError) as erro:
        raise ErroEntrada(f"Não foi possível ler {Path(caminho).name} ({type(erro).__name__}) — confira o arquivo de configuração")


# Cria uma pasta de execução única em saidas/, com data, hora e nome da imagem
def nova_pasta_execucao(caminho_imagem, base=PASTA_SAIDAS):
    nome = re.sub(r"[^\w-]+", "_", Path(caminho_imagem).stem).strip("_") or "imagem"
    pasta = base / f"{datetime.now():%Y%m%d_%H%M%S}_{nome}"
    sufixo = 1
    while pasta.exists():
        sufixo += 1
        pasta = base / f"{datetime.now():%Y%m%d_%H%M%S}_{nome}_{sufixo}"
    pasta.mkdir(parents=True)
    return pasta


# Roda a conferência e devolve também a análise por caixa quando há dois modelos configurados.
def analisar_quadro(imagem_bgr, nota, config, cliente=None, imagem_origem=None, aviso_execucao=None):
    if imagem_bgr is None or getattr(imagem_bgr, "ndim", 0) != 3:
        relatorio = montar_relatorio(
            resultado_erro("Quadro vazio ou inválido — confira a câmera ou a imagem enviada"),
            config, nota.get("nota_id"), imagem_origem,
        )
        return relatorio, montar_evidencia(imagem_vazia(), relatorio), None
    analise_caixas = None
    caixas = []
    suprimidas = []
    try:
        if config.get("modelo_caixas_id"):
            deteccoes, caixas, analise_caixas = detectar_caixas_e_produtos(
                imagem_bgr, config, cliente=cliente
            )
            suprimidas = analise_caixas["deteccoes_suprimidas"]
        else:
            brutas = detectar(imagem_bgr, config, cliente=cliente)
            deteccoes, suprimidas = consolidar_deteccoes(
                brutas, imagem_bgr, config["limiar_confianca"]
            )
        resultado = comparar(nota, deteccoes, config)
        if config.get("modelo_caixas_id") and not caixas:
            resultado["avisos"].append(
                "Nenhuma caixa aberta detectada — as ferramentas foram classificadas como fora da caixa"
            )
        if suprimidas:
            resultado["avisos"].append(
                f"{len(suprimidas)} detecção(ões) repetida(s) ou fragmentada(s) retirada(s) da contagem"
            )
    except ErroDeteccao as erro:
        deteccoes = []
        resultado = resultado_erro(str(erro))
    if aviso_execucao:
        resultado["avisos"].append(aviso_execucao)
    relatorio = montar_relatorio(resultado, config, nota.get("nota_id"), imagem_origem)
    base = desenhar_caixas_embalagem(imagem_bgr, analise_caixas["caixas"]) if analise_caixas else imagem_bgr
    evidencia = montar_evidencia(desenhar_caixas(base, deteccoes, config), relatorio)
    return relatorio, evidencia, analise_caixas


# Devolve uma cópia do config sem o modelo de caixas, para conferir só com o de ferramentas.
def config_sem_caixas(config):
    return {**config, "modelo_caixas_id": None}


# Preserva a interface antiga para quem usa só relatório e imagem anotada.
def conferir_quadro(imagem_bgr, nota, config, cliente=None, imagem_origem=None):
    relatorio, evidencia, _ = analisar_quadro(
        imagem_bgr, nota, config, cliente=cliente, imagem_origem=imagem_origem
    )
    return relatorio, evidencia


# Junta o resultado da comparação com os metadados do relatório
def montar_relatorio(resultado, config, nota_id, imagem_origem):
    return {
        "nota_id": nota_id,
        "imagem": imagem_origem,
        "status": resultado["status"],
        "linhas": resultado["linhas"],
        "descartadas": resultado["descartadas"],
        "avisos": resultado["avisos"],
        "modelo_id": config.get("model_id"),
        "limiar_confianca": config.get("limiar_confianca"),
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


# Conferência completa a partir de arquivos: grava relatorio.json, imagem_anotada.jpg e respostas_brutas.json e devolve (relatório, pasta)
def conferir(caminho_imagem, caminho_nota, pasta_saida=None, config=None, cliente=None, sem_caixas=False,
             reproduzir=None):
    imagem_origem = Path(caminho_imagem).as_posix()
    pasta = Path(pasta_saida) if pasta_saida else nova_pasta_execucao(caminho_imagem)
    pasta.mkdir(parents=True, exist_ok=True)

    imagem = None
    try:
        config = config or carregar_config()
        if sem_caixas:
            config = config_sem_caixas(config)
        imagem = ler_imagem(caminho_imagem)
        nota = carregar_nota(caminho_nota, config["de_para"])
        imagem_sha256 = hash_imagem(caminho_imagem)
        aviso_execucao = None
        if reproduzir:
            cliente = ClienteReproducao(
                carregar_respostas(reproduzir), Path(reproduzir).as_posix(), imagem_sha256
            )
            aviso_execucao = (f"Reprodução offline das respostas gravadas em {Path(reproduzir).as_posix()} "
                              "— não é uma nova inferência")
    except (ErroEntrada, ErroDeteccao) as erro:
        config = config or {}
        relatorio = montar_relatorio(resultado_erro(str(erro)), config, None, imagem_origem)
        base = imagem if imagem is not None else imagem_vazia()
        evidencia = montar_evidencia(desenhar_caixas(base, [], {"limiar_confianca": 1.0}), relatorio)
    else:
        gravador = ClienteGravador(config, cliente, imagem_sha256)
        relatorio, evidencia, analise_caixas = analisar_quadro(
            imagem, nota, config, cliente=gravador, imagem_origem=imagem_origem,
            aviso_execucao=aviso_execucao,
        )
        salvar_respostas(pasta, gravador)
        if analise_caixas is not None:
            (pasta / "analise_caixas.json").write_text(
                json.dumps(analise_caixas, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            salvar_recortes_internos(imagem, analise_caixas, pasta)

    with open(pasta / "relatorio.json", "w", encoding="utf-8") as arquivo:
        json.dump(relatorio, arquivo, indent=2, ensure_ascii=False)
    salvar_jpg(pasta / "imagem_anotada.jpg", evidencia)
    return relatorio, pasta


# Imprime um resumo legível do relatório no terminal
def imprimir_resumo(relatorio, pasta):
    print(f"Status: {relatorio['status'].upper()}  (nota {relatorio['nota_id'] or '—'})")
    for linha in relatorio["linhas"]:
        print(f"  {linha['item']:<16} esperado {linha['esperado']:>2}  detectado {linha['detectado']:>2}  {linha['situacao']}")
    for aviso in relatorio["avisos"]:
        print(f"  Aviso: {aviso}")
    if relatorio["descartadas"]:
        print(f"  Descartadas (abaixo do limiar): {len(relatorio['descartadas'])}")
    print(f"Saídas em {pasta}")


# Ponto de entrada da linha de comando
def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Confere as ferramentas de uma imagem contra uma nota fiscal simulada.")
    parser.add_argument("--imagem", required=True, help="caminho da foto das ferramentas recebidas")
    parser.add_argument("--nota", required=True, help="caminho do JSON da nota fiscal")
    parser.add_argument("--saida", help="pasta de saída (padrão: saidas/<data_hora>_<imagem>)")
    parser.add_argument("--json", action="store_true", help="imprime o relatório JSON completo em vez do resumo")
    parser.add_argument("--sem-caixas", action="store_true",
                        help="confere só com o modelo de ferramentas, ignorando modelo_caixas_id do config")
    parser.add_argument("--reproduzir", metavar="PASTA",
                        help="usa o respostas_brutas.json de uma execução anterior em vez de chamar o Roboflow")
    args = parser.parse_args(argumentos)

    relatorio, pasta = conferir(args.imagem, args.nota, pasta_saida=args.saida, sem_caixas=args.sem_caixas,
                                reproduzir=args.reproduzir)
    if args.json:
        print(json.dumps({**relatorio, "pasta_saida": str(pasta)}, indent=2, ensure_ascii=False))
    else:
        imprimir_resumo(relatorio, pasta)
    return CODIGOS_SAIDA[relatorio["status"]]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
