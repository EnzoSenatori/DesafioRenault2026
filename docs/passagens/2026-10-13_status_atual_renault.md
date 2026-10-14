# Desafio Renault 2026 — estado atual

> **Registro datado de passagem**, recebido de Rafael em 13/10/2026 (arquivo original na raiz: `STATUS_ATUAL_RENAULT.md`). Foi movido para `docs/passagens/` na incorporação ao repositório e não é mais atualizado. O estado vigente está em `CONTINUIDADE.md`. Correções na incorporação: caminho local da máquina de Rafael removido; a pasta `validacao_modelo_escolhido`, que não existe, foi substituída por `docs/`; o comando de câmera passou de `nota_divergente.json` (que pede uma chave inglesa ajustável) para `nota_martelo_camera.json`.

Atualizado em 13/10/2026.

Rafael escolheu o modelo GantrySystem `tool-detection-4u0yd/15` porque distinguiu a chave inglesa ajustável da chave de grifo. O projeto local de Rafael foi atualizado com esse modelo, o mapeamento de classes, notas de exemplo e evidências reais. Em 13/10/2026 Rafael escolheu elevar o limiar de 0,5 para **0,6** após os testes de câmera.

Nas quatro imagens do gabarito confirmado por Rafael, a contagem ficou exata em três; 8 itens foram contados corretamente, sem faltas e com um excesso. A `Img 8.jpeg` continua sendo o caso problemático: um martelo gerou duas detecções. A `Img 15.jpg` com quatro chaves ajustáveis foi **conforme**. A `Img 16.jpg` com uma chave ajustável e uma chave de grifo foi **divergente** contra uma nota que pede só a ajustável. As imagens e o relatório atuais estão em `docs/` (`exemplo_conforme.jpg`, `exemplo_divergente.jpg` e `exemplo_relatorio.json`).

O próximo passo do guia, **modo câmera**, foi implementado em `src/camera.py`. A nota é validada antes da webcam; espaço captura e confere um quadro; Q encerra. Rafael abriu a câmera física e capturou vários quadros. Com a nota de um martelo, uma captura deu `conforme` (martelo 0,73); outras tiveram falsos positivos de chave de fenda 0,52 e trena 0,91 no entorno. Rafael escolheu o limiar 0,6: ele elimina a chave de fenda 0,52 e preserva o martelo 0,73, mas não resolve a falsa trena 0,91 nem a dupla contagem em outra foto. Em seguida, foi adicionada uma **área de leitura verde**: só o recorte interno é enviado ao modelo, enquanto a foto inteira e o recorte são salvos. Rafael testou a área verde em várias capturas reais com os dois modelos; **66 testes passaram** sem rede/webcam.

Para a próxima prova, use uma nota que corresponda à ferramenta mostrada. O comando de câmera, na raiz do projeto, é:

```powershell
.venv\Scripts\python.exe src\camera.py --nota notas/nota_martelo_camera.json --camera 0
```

Com uma nota de uma ferramenta, mostre apenas aquela ferramenta, pressione espaço e confira se o status é `conforme`. Pressione Q para sair. As notas de martelo e chave de fenda já estão prontas em `notas/`. Fotos da câmera variam em iluminação e posição; uma detecção incorreta deve ser registrada como resultado do modelo, sem alterar o gabarito.

Depois da prova da câmera, a etapa pendente é combinar com o colega a interface do orquestrador: linguagem e máquina, forma de enviar imagem, forma de enviar nota, retorno necessário e se a chamada será síncrona. Essas respostas determinam se a integração usa biblioteca Python, CLI/arquivos ou uma API. Rafael decide essa arquitetura antes da implementação.

Rafael também aprovou a estrutura com dois modelos: um para caixas abertas e outro para as ferramentas visíveis dentro ou fora delas, mantendo a área verde e o limiar 0,6. `src/caixas.py` salva `analise_caixas.json` sem alterar o formato de `relatorio.json`. Rafael aprovou o candidato público `open-closed-cardbox/2`, ativo em `modelo_caixas_id`. Nas primeiras capturas o modelo não aceitou a caixa; em sete fotos posteriores aceitou `Open Cardboard Box` com confiança 0,70–0,86. O rótulo azul ficava escondido junto à borda da imagem e foi corrigido. O martelo, parcialmente oculto pela parede da caixa, foi frequentemente chamado `Mallet`; a chave de fenda esperada não ficou visível no recorte. A correção mais recente envia também o interior de cada caixa aberta ao modelo de ferramentas e salva `caixa_N_interior.jpg` para inspeção. **66 testes automáticos** passaram, mas a acurácia dessa mudança ainda depende de nova captura real de Rafael; o ambiente do agente não completou a chamada ao Roboflow. A nota `notas/nota_caixa_aberta_demo.json` pede um martelo e uma chave de fenda para essa prova.
