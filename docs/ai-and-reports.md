# Cérebro IA e relatórios

- **Clientes → Conexão → Abrir Cérebro IA:** consultar histórico, gerar análise e salvar a análise selecionada como relatório.
- **Relatórios:** selecionar cliente, informar título e criar relatório de métricas; incluir uma nova análise IA é opcional.
- **Exportação:** HTML independente, sem recursos externos; “Imprimir / Salvar PDF” abre a impressão do navegador (escolher Salvar como PDF).

## Configuração

No ambiente do backend, configure `OPENAI_API_KEY`. O modelo vem de `OPENAI_MODEL` (padrão: `gpt-4o-mini`). Reinicie o backend após alterar o ambiente. Não coloque a chave no frontend.

A geração de IA envia nomes e métricas de campanhas à OpenAI e consome créditos da API. Relatórios apenas de métricas não fazem essa chamada. Reutilizar uma análise salva também não faz nova chamada.

Após atualizar o código:

```powershell
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

## Dados e limitações

Os relatórios exigem campanhas reais sincronizadas. A IA também exige métricas diferentes de zero. Sem conta de anúncios, é possível acessar as telas e seus estados vazios; dados de teste existem apenas nos testes automatizados.

O banco guarda a última janela de 30 dias por integração, não um histórico diário. Não há seleção arbitrária de datas. Cada campanha mostra quando foi sincronizada. A cópia dos dados de um relatório ou insight não muda após novas sincronizações.

Gastos são agrupados por conta porque a moeda ainda não é capturada. Conversões seguem a atribuição de cada plataforma (Meta: compras + leads). A IA não tem receita, metas ou benchmarks: orientações são hipóteses para revisão humana.

A análise detalhada considera até 100 campanhas, priorizadas por impressões, e informa essa limitação quando aplicável; o relatório preserva todas. Históricos de IA anteriores à captura de evidências são preservados no banco, mas ficam fora da interface atual.

## Verificação local, sem chamadas pagas

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
cd my-app
npm run build
```

Os testes usam SQLite em memória e respostas controladas para os provedores. Isso verifica integração, isolamento, falhas e exportação, mas não a qualidade de respostas reais da IA ou o acesso às APIs de anúncios.
