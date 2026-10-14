# Capturas diagnósticas selecionadas — Desafio Renault 2026

As três subpastas em `evidencias_capturas/` contêm somente `quadro_analisado.jpg`, `imagem_anotada.jpg`, `analise_caixas.json` e `relatorio.json`. São resultados reais da webcam de Rafael em 13/10/2026, **anteriores** à mudança que faz uma segunda inferência no interior da caixa. O quadro completo da webcam foi deixado de fora do pacote. As fotos mostram apenas uma pequena amostra; não são uma avaliação estatística de acurácia.

| Captura | O que a foto mostra | Resposta observada | O que investigar |
|---|---|---|---|
| `camera_20261013_202532` | Martelo na caixa branca e chave de fenda fora | O detector gerou três caixas de `Hammer` e três de `Screwdriver`; a caixa aberta não passou. | Fragmentação e dupla contagem. A correção geométrica posterior foi reproduzida só com as coordenadas salvas, sem nova inferência. |
| `camera_20261013_205632` | Caixa aberta vista lateralmente, martelo parcialmente coberto | `Open Cardboard Box` apareceu a 0,34, abaixo do limiar 0,6; `Hammer` a 0,63 e `Mallet` a 0,62. | Enquadramento e confusão aberta/fechada; conflito de classe da ferramenta. |
| `camera_20261013_205725` | Caixa aberta quase preenchendo o recorte, martelo com cabeça pouco visível | Caixa aceita a 0,75; ferramenta classificada como `Mallet` a 0,84; a nota pede também uma chave de fenda que não aparece no recorte analisado. | A caixa já era detectada. O rótulo azul antigo caía na borda e foi corrigido no código. O recorte interno não consegue revelar a parte escondida do martelo. |

O limiar vigente é **0,6**, decidido por Rafael. `Mallet` não foi mapeado para `Hammer`, pois o objetivo é distinguir ferramentas. A próxima validação deve usar foto com abertura vista ligeiramente de cima e ferramentas inteiras visíveis, comparar `caixa_1_interior.jpg` gerado pelo código novo com o relatório e confirmar manualmente as contagens. Não apresentar esses três casos antigos como evidência de que a nova inferência interna melhorou a precisão.
