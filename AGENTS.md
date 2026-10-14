# Orientações para continuar o Desafio Renault 2026

## Colaboração com Rafael

Rafael decide as questões importantes; o agente implementa e testa. Perguntar antes de trocar modelo ou limiar, ampliar escopo, criar serviços pagos, publicar, mudar contratos ou escolher a forma de integração. Preparação local, inspeção e testes podem avançar. Não exigir que Rafael escreva código.

## Contexto e contratos

Leia CONTINUIDADE.md, CLAUDE.md e README.md. CONTINUIDADE.md descreve o estado mais recente; instruções atuais de Rafael prevalecem. O MVP usa ferramentas como substitutas de peças automotivas. Não quebrar o relatório da seção 3.6: não remover/renomear campos nem mudar os status conforme, divergente e erro. Campos adicionais exigem avaliar consumidores/testes.

## Convenções

- Cada função Python tem comentário breve acima de def; não usar docstrings.
- Variáveis, funções e mensagens em português.
- Texto de imagens via Pillow com fonte TTF para suportar acentos.
- Erros devem explicar o problema e a ação necessária.
- Não inventar respostas de API, versões, métricas ou resultados. Distinguir simulação e execução real.
- Testes novos sem rede, usando clientes falsos.
- Não inventar gabarito: contagens de referência precisam de validação humana.
- Nunca imprimir, registrar, copiar para artefatos ou versionar ROBOFLOW_API_KEY. O usuário pode configurá-la no .env local ignorado; verificar presença sem mostrar valor.

## Escopo

Treino/ajuste fino, Streamlit, banco, OCR de nota, vídeo com contagem acumulada, catálogos com kits e schemas versionados estão fora do escopo acordado. API web depende de decisão de Rafael/equipe. Não executar os prompts futuros automaticamente só porque estão na documentação.

## Windows

- Python compatível: 3.10 a 3.13; usar .venv\Scripts\python.exe após criar o ambiente.
- Imagens: np.fromfile + cv2.imdecode e cv2.imencode + tofile para caminhos com acentos/espaços.
- load_dotenv recebe caminho explícito do .env.
- Não somar quadros da câmera; captura é uma conferência independente.
- Não suprimir avisos globalmente por padrão; tratar aviso conhecido apenas quando necessário.

## Comandos na raiz

```powershell
# Criação inicial com um executável Python compatível verificado
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 16.jpg" --nota notas/nota_divergente.json
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 16.jpg" --nota notas/nota_divergente.json --json
.venv\Scripts\python.exe src\testar_modelo.py
```

Inferência real requer chave e acesso ao Roboflow; testes automatizados usam clientes falsos. Saídas CLI: 0 conforme, 1 divergente, 2 erro. Preservar .env, .venv e saidas fora do versionamento. Esta pasta veio de ZIP e não possui histórico Git.
