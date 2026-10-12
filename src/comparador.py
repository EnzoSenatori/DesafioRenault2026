from collections import Counter

AVISO_SEM_DETECCAO = "nenhuma ferramenta detectada — verifique a captura"


# Separa as detecções em aceitas e descartadas (abaixo do limiar); classes ignoradas saem das duas
def filtrar_deteccoes(deteccoes, limiar, classes_ignoradas):
    aceitas, descartadas = [], []
    for deteccao in deteccoes:
        if deteccao["classe"] in classes_ignoradas:
            continue
        if deteccao["confianca"] >= limiar:
            aceitas.append(deteccao)
        else:
            descartadas.append(deteccao)
    return aceitas, descartadas


# Classifica uma linha a partir do esperado e do detectado
def situacao_da_linha(esperado, detectado):
    delta = detectado - esperado
    if delta == 0:
        return "igual"
    if delta < 0:
        return "falta"
    if esperado > 0:
        return "excesso"
    return "nao_previsto"


# Compara a nota validada com as detecções e devolve linhas, descartadas, avisos e status global
def comparar(nota, deteccoes, config):
    aceitas, descartadas = filtrar_deteccoes(
        deteccoes, config["limiar_confianca"], set(config.get("classes_ignoradas", []))
    )
    detectados = Counter(d["classe"] for d in aceitas)
    nomes = config.get("nomes_exibicao", {})
    codigo_por_classe = {classe: codigo for codigo, classe in config["de_para"].items()}

    esperados = Counter()
    ordem = []
    for item in nota["itens"]:
        if item["classe"] not in esperados:
            ordem.append(item["classe"])
        esperados[item["classe"]] += item["quantidade"]
    ordem += sorted(classe for classe in detectados if classe not in esperados)

    linhas = []
    for classe in ordem:
        esperado, detectado = esperados[classe], detectados[classe]
        linhas.append({
            "codigo": codigo_por_classe.get(classe),
            "item": nomes.get(classe, classe),
            "classe": classe,
            "esperado": esperado,
            "detectado": detectado,
            "delta": detectado - esperado,
            "situacao": situacao_da_linha(esperado, detectado),
        })

    avisos = []
    if not aceitas and nota["itens"]:
        avisos.append(AVISO_SEM_DETECCAO)

    status = "conforme" if all(linha["situacao"] == "igual" for linha in linhas) else "divergente"
    return {
        "status": status,
        "linhas": linhas,
        "descartadas": [{"classe": d["classe"], "confianca": round(d["confianca"], 3)} for d in descartadas],
        "avisos": avisos,
    }


# Resultado de falha técnica: sempre "erro", nunca "conforme"
def resultado_erro(mensagem):
    return {"status": "erro", "linhas": [], "descartadas": [], "avisos": [mensagem]}
