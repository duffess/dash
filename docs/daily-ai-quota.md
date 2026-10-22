# Cota diária de IA

- Uma geração bem-sucedida por cliente por dia civil de Brasília (UTC-3).
- Não há agendamento: a primeira solicitação do dia gera a análise.
- Cérebro e relatórios com IA compartilham a cota e o snapshot original.
- Falhas liberam a reserva para tentar novamente; isso não garante estorno de
  consumo que o provedor eventualmente tenha processado antes de um timeout.
- Chave primária composta no banco impede duas gerações simultâneas entre workers.
- Pedidos em andamento retornam 409; atualizar o histórico após a conclusão.
- Uma interrupção abrupta do processo pode deixar reserva pendente. Não expira
  automaticamente para evitar outra chamada potencialmente cobrada. Nesse caso,
  um operador deve confirmar que não há geração ativa antes de remover somente
  a reserva pendente daquele cliente/dia. No próximo dia há uma cota nova.
- O laboratório de demonstração continua separado, sem cota de cliente. Sua opção
  de IA real consome API a cada geração e não deve ser liberada sem limites em produção.
- Migração: `python -m alembic upgrade head`.
- Testes offline: `python -m unittest discover -s tests`.
