# Dash — acompanhamento de 16/11/2026

## Concluído nesta conversa

- Primeira versão do relatório adaptativo: pontos com escala automática e ponto parcial, métricas em destaque conforme disponibilidade, contas separadas e gráfico de investimento por campanha.
- 96 testes automatizados passaram, incluindo cobertura para escala, dados ausentes e zero.
- A versão está local, sem commit. A verificação visual completa de impressão e dos fluxos de ponta a ponta permanece pendente.

## Próximo grupo de cinco implementações

- [x] Campo opcional para a agência escrever sua análise e próximos passos, salvos no retrato do relatório. API testada, incluindo reabertura e proteção contra HTML injetado.
- [x] Textos adaptativos por métricas disponíveis, sem inferir qualidade ou vendas; cenários de dados ausentes e zero cobertos por testes.
- [x] Busca por nome e seleção/desmarcação de todas as campanhas. A seleção em massa inclui também as campanhas ocultas pelo filtro, conforme informado na interface. Build passou; fluxo visual completo ainda precisa ser validado.
- [ ] Impressão/PDF: regras de quebra e nomes longos ajustadas; ainda falta inspecionar PDFs impressos, curtos e longos, antes de dar por concluído.
- [x] Histórico com filtros por data de criação (UTC) e por cliente; reabertura e exportação já existiam. API de filtro testada; validação visual completa pendente.

O código ainda está local. As notas são opcionais, não usam IA e são salvas no retrato, sem migração de banco. Backend local reiniciado para carregar a versão nova.

Validação após as alterações: 98 testes automatizados passaram, incluindo persistência das notas, escape de HTML, filtros de data e compatibilidade com relatórios de IA existentes.

## Segundo grupo de cinco

- [x] Identidade do relatório: nome e logo da agência (PNG/JPEG até 128 KB), guardados no retrato de cada relatório. Campos opcionais e validação de formato no backend.
- [x] Resumo antes de gerar com cliente, campanhas, métricas, período, identidade e presença dos textos.
- [x] Usar relatório anterior como modelo: reutiliza título, identidade, campanhas e métricas; textos devem ser revistos e os dados são consultados novamente. Campanhas que não estiverem mais disponíveis são sinalizadas.
- [x] Visão de clientes com contagem de campanhas, último relatório e atalhos para listas filtradas. Endpoint de resumo filtrado pelo proprietário.
- [x] Estados de erro e vazio melhorados nas páginas de clientes e relatórios; falha ao buscar histórico não é exibida como histórico vazio.

Validação: 100 testes automatizados passaram; testes de API cobrem persistência e validação da logo e isolamento do resumo por usuário. O build do frontend passou. A validação visual final do fluxo, da duplicação e a impressão de PDFs curtos e longos continuam pendentes. O código está local e ainda não foi enviado ao GitHub.


## Terceiro grupo de cinco

- [x] Capa do relatório com logo do cliente e cor de destaque opcionais, salvas no retrato do relatório. Ao usar como modelo, as escolhas são recuperadas. A cor é validada no servidor e aplicada a um detalhe da capa.
- [x] Edição de clientes e aviso explícito antes da exclusão; campos opcionais podem ser limpos. O formulário recebeu rótulos, exemplos, contraste e foco mais legíveis.
- [x] Página do cliente mostra até três relatórios recentes e atalhos para campanhas e relatórios.
- [x] Indicadores com comparação disponível mostram os valores atual e anterior; valores anteriores iguais a zero são explicados sem inventar porcentagem. Histórico real continua pendente de integração.
- [x] Histórico de relatórios com busca por título e exclusão mediante confirmação; autorização é verificada no servidor.

Validação: 102 testes automatizados passaram, incluindo busca, validação da marca e isolamento na exclusão. Verificação visual com conta autenticada, testes manuais em celular e impressão dos PDFs ainda pendentes. Mudanças locais, sem envio ao GitHub ou publicação.

- Relatórios: adicionada explicação junto ao botão quando faltam dados e atalhos para conexões, nova tentativa e laboratório fictício. Sem campanhas sincronizadas, relatórios reais continuam indisponíveis.


## Quarto grupo de cinco

- Laboratório: personalização de cliente fictício, campanhas, métricas, textos, logos e cor; relatórios demonstrativos não são salvos no histórico.
- Prévia de relatório real antes de salvar, usando dados do cliente autorizado e sem gravar no banco.
- Duplicação dos dados básicos do cliente para formulário de cadastro; conexões e campanhas não são copiadas.
- Campanhas: explicação para métricas indisponíveis e orientação de sincronização.
- Ajustes de tamanho de campos e botões para celular; verificação manual em dispositivos ainda pendente.

Validação: build e 23 testes de relatórios passaram, incluindo prévia sem gravação, autorização e demonstração isolada. Ainda falta verificar visualmente as telas, imprimir PDFs curtos e longos e testar o fluxo completo no navegador. Mudanças locais, sem publicação.


## Testes de relatórios e PDF

- Gerados PDFs fictícios curto (1 campanha, 4 páginas) e longo (24 campanhas, 17 páginas) em A4, pelo motor de impressão do Edge.
- Inspecionadas a capa e algumas páginas internas. Corrigidos o plural na capa e a divisão dos blocos de campanha entre páginas; o ajuste pode deixar espaços vazios maiores.
- Os 104 testes automatizados passaram; duas simulações antigas foram atualizadas para o formato atual do laboratório.
- Pendências: inspeção visual de todas as páginas, fluxo de impressão pela interface, testes manuais completos de clientes/campanhas e revisão no celular.
