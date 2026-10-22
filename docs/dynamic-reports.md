# Relatórios adaptativos e laboratório

Em **Relatórios > Laboratório de relatórios + Cérebro IA**, escolha leads,
vendas, dados parciais ou zero resultados. Não é necessário conectar anúncios.
O laboratório é autenticado, usa dados fictícios fixos, nunca grava clientes,
campanhas, relatórios ou insights no banco e marca a origem no HTML/PDF.

O botão gera métricas sem chamadas de IA. A IA do laboratório fica bloqueada no
backend por padrão, mesmo se uma requisição enviar `include_ai=true` e houver
chave OpenAI. A interface acompanha a configuração retornada pelo backend.
Sem IA, é possível visualizar e exportar os quatro cenários normalmente.

`DEMO_AI_ENABLED=false` é o padrão, não precisa alterar o `.env`.
Só o operador pode liberar com `DEMO_AI_ENABLED=true` e reiniciar o backend.
Esse opt-in consome créditos e ainda NÃO tem cota por usuário no laboratório.
Não o habilite para usuários externos antes de implantar essa cota e limites de
gasto. A cota diária por cliente dos relatórios reais permanece inalterada.

## Contrato comum

Relatórios reais, demonstração, exportação e Cérebro IA usam `metrics` como
fonte autoritativa. Chave ausente não é zero; dicionário vazio não tem métricas.
Zero é preservado. Razões só são calculadas com denominador positivo.
CPL exige leads; custo por compra exige compras; ROAS exige receita atribuída.
Totais por conta exigem cobertura completa e não misturam moedas/contas.
Indicadores ausentes ficam fora das tabelas e são explicitados nas limitações.

Desde a migration `d731ab950124`, a sincronização preserva a disponibilidade em
`campaigns.report_metrics`. A Meta separa leads/compras quando os eventos vêm
na resposta; ausência de evento não é inferida como zero. Google preserva as
conversões da plataforma sem chamá-las de leads. Re-sincronize dados antigos
para capturar essa informação. Resumos do dashboard não foram remodelados.

## Limites atuais

- A integração real continua com snapshots de 30 dias, sem histórico diário.
- Comparação só aparece quando o snapshot contém um período anterior com a
  mesma duração e campanha/conta/moeda compatíveis. Baseline zero não tem delta.
- Os cenários de leads/vendas demonstram dois períodos de 30 dias. Isso não
  implica que o conector real já forneça histórico.
- Receita/ROAS existem no cenário fictício de vendas. Os conectores atuais
  ainda não coletam receita nem moeda; não há substituição por valores fictícios.
- A IA recebe disponibilidade, fórmulas, origem e limitações; suas recomendações
  são sugestões, não decisões automáticas. Requer revisão humana.
- PDF continua sendo impressão do HTML pelo navegador. A prévia usa exatamente
  o mesmo HTML, isolado em iframe sem permissão de scripts.

## Verificação

`python -m unittest discover -s tests -q`

`python tests/render_report_samples.py <pasta-temporaria>` gera quatro HTMLs
offline para inspeção visual. Não acessa banco, contas ou APIs pagas.
