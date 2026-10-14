# Guia de integração — conferência visual (etapa 3)

Este guia permite ao Enzo ligar a conferência visual às etapas 1 (leitura da nota) e 5 (estoque). O estado técnico e as limitações vigentes estão em [`../CONTINUIDADE.md`](../CONTINUIDADE.md); este arquivo descreve o contrato de integração e o trabalho restante. Rafael não poderá fazer novos testes de câmera agora. **A integração real ainda depende das sete decisões ao fim deste guia.** Não interpretar a reprodução offline como nova inferência ou como prova de acurácia.

## O que já pode ser consumido

O projeto aceita uma foto e uma nota JSON; devolve `relatorio.json`, `imagem_anotada.jpg` e, em execução com inferência, `respostas_brutas.json`. Quando o modelo de caixas está ativo, também pode gerar `analise_caixas.json` e `caixa_N_interior.jpg`. A saída estável para outros sistemas é **`relatorio.json`**. Os outros arquivos são evidências/diagnóstico e devem ser referenciados pelo caminho escolhido na integração. A câmera e a borda verde pertencem ao modo de captura local; um sistema externo pode entregar a imagem já capturada.

Há dois pontos de entrada existentes:

| Origem | Chamada | Retorno |
|---|---|---|
| Python, foto e nota em arquivos | `conferir(caminho_imagem, caminho_nota, pasta_saida=...)` em `src/conferir.py` | `(relatorio, pasta)`; grava os arquivos de saída |
| Qualquer linguagem, mesma máquina | `python src/conferir.py --imagem ... --nota ... --saida ... --json` | JSON em `stdout`, incluindo `pasta_saida`; saída do processo: `0` conforme, `1` divergente, `2` erro |

`conferir_quadro(quadro_bgr, nota_validada, config)` é a opção Python para uma imagem em memória. A nota deve antes passar por `validar_nota(dados, config["de_para"])`. O retorno é `(relatorio, evidencia_bgr)`; quem chama decide onde salvar a evidência. **Ainda não há API HTTP, fila, banco de dados ou leitor de NF-e neste projeto.** A forma definitiva será escolhida por Rafael e Enzo após responderem às perguntas abaixo.

## Contrato da nota de entrada

```json
{
  "nota_id": "NF-EXEMPLO-001",
  "fornecedor": "Fornecedor Exemplo",
  "itens": [
    {"codigo": "FER-004", "descricao": "Martelo", "quantidade": 1},
    {"codigo": "FER-002", "descricao": "Chave de fenda", "quantidade": 1}
  ]
}
```

`codigo` é tratado como texto; `quantidade` deve ser inteiro positivo. Códigos repetidos são somados. Os códigos atualmente reconhecidos estão no `de_para` de `config.json`: `FER-001` alicate, `FER-002` chave de fenda, `FER-003` chave inglesa ajustável, `FER-004` martelo e `FER-005` chave de grifo. São ferramentas de demonstração, não códigos reais de peças da Renault. Código desconhecido, quantidade inválida ou JSON malformado resultam em `erro`; o projeto não tenta adivinhar a correspondência.

Se a etapa 1 produzir XML de NF-e, nomes de produtos, códigos de outro catálogo ou um objeto de outra estrutura, **o sistema de integração precisará converter essa entrada** para o JSON acima e definir um mapeamento aprovado de código para classe. Não alterar silenciosamente `de_para` nem transformar marreta em martelo. Guardar a nota original e o identificador do recebimento no sistema de origem, conforme decisão da equipe.

## Contrato do resultado

Exemplo simplificado de divergência:

```json
{
  "nota_id": "NF-EXEMPLO-001",
  "imagem": "foto.jpg",
  "status": "divergente",
  "linhas": [
    {"codigo": "FER-004", "item": "Martelo", "classe": "Hammer", "esperado": 1, "detectado": 2, "delta": 1, "situacao": "excesso"}
  ],
  "descartadas": [],
  "avisos": [],
  "modelo_id": "tool-detection-4u0yd/15",
  "limiar_confianca": 0.6,
  "gerado_em": "2026-10-13T22:43:21-03:00"
}
```

Esse JSON **ilustra o formato**, não é uma nova execução. O exemplo real completo está em `docs/exemplo_relatorio.json`. `delta = detectado - esperado`; cada linha pode ter `situacao` `igual`, `falta`, `excesso` ou `nao_previsto`. `status=conforme` significa que as contagens da execução coincidiram, **não** que o recebimento foi aprovado sem revisão humana. `status=divergente` exige tratamento da divergência. `status=erro` indica falha técnica ou entrada inválida; verificar `avisos` e não tratar como conferência aprovada. O consumidor não deve inferir o status pelo código de saída sozinho nem interpretar `1` como falha do processo: `1` é uma divergência de negócio.

Não remover ou renomear campos do relatório nem mudar os três valores de `status` sem acordo explícito com Rafael. `descartadas` lista detecções abaixo do limiar; `avisos` inclui, entre outros, o aviso de reprodução offline. O caminho em `imagem` é o fornecido na chamada, e o nome do arquivo de evidência fica na pasta de saída.

## Exemplo de conexão local por comando

Na raiz do clone, com Python 3.10–3.13 e dependências instaladas:

```powershell
.venv\Scripts\python.exe src\conferir.py --imagem "C:\dados\recebimento\foto.jpg" --nota "C:\dados\recebimento\nota.json" --saida "C:\dados\recebimento\conferencia" --json
```

O sistema chamador deve analisar o JSON de `stdout`, ler o `relatorio.json` gravado em `--saida` e guardar uma referência à evidência se isso for decidido. Cada recebimento precisa de uma pasta de saída exclusiva. Não reutilizar uma pasta antiga: uma execução com falha antes de gerar todos os arquivos poderia deixar evidências anteriores misturadas. Para arquivo sem caixa na demonstração, `--sem-caixas` desliga apenas o modelo de caixas naquela chamada; o padrão continua com os dois modelos.

Para Python no mesmo processo:

```python
import sys
from pathlib import Path

raiz = Path(r"C:\caminho\DesafioRenault2026")
sys.path.insert(0, str(raiz / "src"))
from conferir import conferir

relatorio, pasta = conferir(
    raiz / "foto.jpg",
    raiz / "nota.json",
    pasta_saida=raiz / "saidas" / "recebimento_001",
)
print(relatorio["status"], pasta / "relatorio.json")
```

O exemplo pressupõe que a pasta e os arquivos indicados existam; adapte os caminhos ao ambiente aprovado. A chave do Roboflow fica apenas no `.env` local, ignorado pelo Git. Nunca a enviar na nota, nos logs, na evidência nem no repositório.

## Verificação sem câmera e sem internet

As respostas gravadas em `docs/reserva/` permitem testar a conexão sem webcam nem chamada ao Roboflow. A reprodução exige a **mesma imagem, byte a byte**, usada na gravação; trocar a imagem provoca `erro`.

```powershell
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 15.jpg" --nota notas/nota_conforme.json --sem-caixas --reproduzir docs/reserva/img15_conforme --saida saidas/integracao_conforme --json
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 16.jpg" --nota notas/nota_divergente.json --sem-caixas --reproduzir docs/reserva/img16_divergente --saida saidas/integracao_divergente --json
```

O primeiro comando deve retornar `conforme`/código `0`; o segundo, `divergente`/código `1`. Uma nota ausente ou inválida deve produzir `erro`/código `2`, sem consultar a rede. Esses casos verificam o **contrato de integração**, não a precisão dos modelos em imagens novas. Os testes automatizados verificam os três resultados da interface de comando.

## Decisões para fechar a integração

Rafael e Enzo devem preencher estas respostas antes de construir o adaptador definitivo:

1. **Ambiente:** em que linguagem e máquina roda o sistema que coordena as etapas?
2. **Imagem:** ela chega como caminho de arquivo, bytes, URL ou quadro de câmera? Quem a guarda e por quanto tempo?
3. **Nota:** chega como arquivo JSON, objeto em memória, XML de NF-e ou outro formato?
4. **Retorno:** o sistema precisa apenas do status, do relatório completo e/ou do arquivo de evidência?
5. **Execução:** a chamada será síncrona, por fila ou por pasta observada? Qual é o tempo máximo aceitável?
6. **Origem da nota:** qual sistema da etapa 1 a produz e qual é o seu formato concreto, incluindo um exemplo sem dados sensíveis?
7. **Destino:** o relatório deve ser salvo no banco do site de estoque (etapa 5)? Se sim, qual sistema fará a gravação e como relacionará o resultado ao recebimento?

Com essas respostas, escolher **uma** forma de integração e implementar apenas o conversor/adaptador necessário. Testar `conforme`, `divergente` e `erro` sem rede; depois testar ponta a ponta com os sistemas reais. A integração não deve marcar estoque como confirmado quando houver `divergente` ou `erro` sem uma regra explícita de negócio aprovada.

## Pendências de visão computacional, independentes da conexão

Ainda faltam capturas reais de caixa aberta com martelo visível dentro e chave de fenda fora, dois martelos separados e caixa vazia. A `Img 8.jpeg` tem um martelo contado duas vezes; outra captura mostrou o mesmo objeto como `Hammer` e `Mallet`; em algumas imagens a caixa ou a ferramenta ficou oculta/não reconhecida. Esses pontos afetam a confiança no resultado, mas **não impedem preparar o contrato de integração**. Não afirmar que a detecção em caixas foi validada. O modelo de ferramentas, o modelo de caixas, as classes e o limiar `0.6` permanecem como estão até decisão de Rafael.
