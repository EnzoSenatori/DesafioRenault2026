# Revisão técnica da base de 13/10 — Enzo para Rafael

> **Registro datado de passagem** (Enzo, com Claude Code, 13/10/2026). O estado vigente está em `CONTINUIDADE.md`; este arquivo guarda o raciocínio da revisão e as medições que a sustentam.

A revisão partiu da base de Rafael incorporada na branch `integracao-rafael-2026-10-13`. Cada ponto foi confirmado no código e nos testes. As correções propostas estão implementadas na branch `propostas-revisao-2026-10-13`, um commit por proposta, e **dependem da aprovação de Rafael**. Nenhuma muda modelo, limiar 0,6, classes do `de_para` nem o formato de `relatorio.json`.

## Pontos revisados

| # | Fato observado | Risco | Proposta (commit) |
|---|---|---|---|
| 1 | Com `modelo_caixas_id` ativo, `src/conferir.py` sempre usa o fluxo de dois modelos. Img 15 e Img 16 por arquivo fizeram 2 chamadas reais em vez de 1 e ganharam o aviso “Nenhuma caixa aberta detectada…”; o status não mudou. Os exemplos de `docs/` tinham sido gerados com 0,5 e um modelo. | Latência e um ponto de falha a mais na demonstração; exemplos não reproduzíveis como estavam. | `--sem-caixas` em `conferir.py` e `camera.py` (`da4a3ba`); exemplos regenerados com 0,6 (`ce57248`). |
| 2 | `avaliar_modelos.py` usa `converter_resposta` direto, sem `aliases_classes` nem `consolidar_deteccoes`. | A métrica não mede o fluxo que roda de fato. | `--fluxo-real` (`aa70b65`). Na execução real de 13/10 o resultado foi igual ao bruto: o filtro não retira o segundo martelo da `Img 8.jpeg` (caixas sem sobreposição nem alinhamento). |
| 3 | No recorte interno, `src/caixas.py` descartava as detecções abaixo do limiar; e as fracas do quadro geral dentro de uma caixa com recorte positivo também eram retiradas. Nenhuma das duas chegava a `descartadas`. Nenhum teste cobria isso. | Lacuna de auditoria (não afeta contagem). | Fracas do recorte vão para `descartadas` e para `recortes_internos[].abaixo_do_limiar` (`37572ae`). |
| 4 | `Mallet` e `Tape Measure` apareciam em inglês no painel e no campo `item` (fallback `nomes.get(classe, classe)`). | Apresentação confusa no pitch. | `Marreta` e `Trena` em `nomes_exibicao`, sem `de_para` e sem mapear para `Hammer` (`d979f06`). |
| 5 | `analise_caixas.json` não guarda as respostas brutas (faltam as abaixo do limiar e, nas capturas antigas, as suprimidas); só dá para reprocessar em parte. | Sem internet no dia, só restariam imagens estáticas. | `respostas_brutas.json` em toda execução e `conferir.py --reproduzir PASTA` (`791a652`); reservas em `docs/reserva/`. |
| 6 | Tempos reais (rede de Enzo, 13/10): chamadas aquecidas de 0,22 a 0,31 s; 2 chamadas em 0,5–0,7 s; 3 chamadas (captura `205725`, uma caixa aceita) em 0,78 s; **primeira** chamada ao modelo de caixas em 4,4 s. | Partida a frio no início da apresentação. | Fazer uma conferência de aquecimento antes do pitch; repetir a medição na rede do local. |

## Medições de 13/10 (execuções reais)

- `avaliar_modelos.py`, `tool-detection-4u0yd/15`, limiar 0,6, gabarito de 4 imagens: 3/4 exatas, 8 corretos, 0 faltas, 1 excesso — idêntico a 0,5. `--fluxo-real`: mesmo resultado.
- Nova inferência sobre os `quadro_analisado.jpg` salvos das capturas de Rafael (não são capturas novas). As respostas estão em `docs/reserva/reinferencia_<captura>/` e podem ser reproduzidas sem rede:
  - `202532`: de novo 3 `Hammer` + 3 `Screwdriver` brutos; o filtro resultou em 1+1 e `conforme` (4 suprimidas). Caixa aberta não aceita.
  - `205632`: `Open Cardboard Box` 0,36 (abaixo de 0,6); `Hammer` 0,62 e `Mallet` 0,61 quase na mesma posição, **os dois contados**; três detecções abaixo do limiar em `descartadas`.
  - `205725`: caixa aceita a 0,75; quadro geral `Mallet` 0,81 e recorte interno `Mallet` 0,89; nenhuma chave de fenda.
- Exemplos de `docs/` regenerados com 0,6 e `--sem-caixas`: Img 15 `conforme`, Img 16 `divergente` (grifo não previsto).

## Hipóteses (não verificadas)

- Os 4,4 s da primeira chamada são partida a frio do serviço serverless do Roboflow.
- Juntar classes parecidas sobrepostas (`Hammer`/`Mallet`) reduziria a dupla contagem entre classes, mas mexe na distinção entre ferramentas — decisão de Rafael. Não implementado.

## Lacunas menores registradas

- `modelos_avaliacao.json` não mapeia `Claw hammer` para `Hammer` no GantrySystem, embora o `config.json` faça isso. Se o modelo devolver esse nome, a avaliação bruta o conta como classe desconhecida; `--fluxo-real` aplica o alias.
- Os programas gravam JSON com `write_text` sem `newline`, o que gera CRLF no Windows; o `.gitattributes` normaliza no repositório.
- As fotos completas da webcam de Rafael ficam no `saidas/` da pasta antiga dele (ignorada pelo Git) e não estão no repositório.

## Validações pendentes

- Teste real do recorte interno e do filtro geométrico em capturas novas (roteiro no `CONTINUIDADE.md`).
- Medições com fotos da própria webcam rotuladas por pessoa.
- Tempos na rede do local do pitch.
