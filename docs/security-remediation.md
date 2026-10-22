# Segurança: primeiro lote de correções

## Alterações

- Cadastro e hash não imprimem senha, payload ou resposta de autenticação.
  O dashboard também não imprime objetos Axios, que podem conter Authorization.
- O access log do Uvicorn omite a query inteira dos callbacks Google e Meta,
  inclusive quando há barra final. Método, caminho e status continuam visíveis.
- Erros OAuth retornam mensagens fixas, sem texto de exceção, URL de requisição
  ou corpo de erro do provedor. Novos erros Meta salvos em `sync_error` também
  são fixos. Erros de validação mantêm `loc`, `msg` e `type`, sem `input` ou `ctx`.
- O serviço Gemini legado não registra respostas brutas ou texto de exceções.
- `DEMO_AI_ENABLED` é falso por padrão. O backend rejeita `include_ai=true`
  no laboratório com 403 antes de chamar a IA. Os quatro relatórios estáticos,
  sua exportação e as análises reais por cliente continuam disponíveis.
  A tela usa o status retornado pelo servidor. Não é necessário editar `.env`.

Este lote não rotaciona chaves, não migra banco e não modifica dados históricos.
Logs antigos e `sync_error` anteriores podem continuar contendo dados sensíveis.
Restrinja seus leitores, revise retenção e rotacione credenciais comprovadamente
expostas. Não troque `SECRET_KEY` antes de planejar a migração dos tokens cifrados.
Logs de proxy, navegador, ferramentas de terceiros e configuração DEBUG de SDKs
não são controlados pelo filtro do Uvicorn.

## Testes isolados, sem dependências novas ou custo de API

Na raiz do projeto, com WSL **Ubuntu-22.04 x86_64** e GCC já instalados:

```powershell
.\scripts\security\run-isolated.ps1
```

O script não instala nada. Ele cria uma pasta exclusiva fora do repositório,
copia apenas arquivos de fonte permitidos e compila o launcher revisado. Não
copia `.env`, bancos, `.git`, ambientes virtuais ou dependências do projeto.
Não execute um launcher alterado por terceiros sem revisar seu conteúdo.

O processo dos testes usa namespaces de usuário, montagem, PID e rede,
`chroot`, ambiente criado do zero, fonte e toolchain somente leitura,
capabilities removidas e seccomp. Não monta `/proc`, `/mnt`, diretórios pessoais
ou a integração de host do WSL. Só `/scratch` é gravável, em tmpfs de 32 MiB.
Limites: 20 segundos de CPU, 45 segundos de parede (encerramento forçado após
2 segundos adicionais), 512 MiB por processo, um processo, 64 descritores,
8 MiB por arquivo e core dumps desativados. Fork/clone e criação de sockets
são negados pelo kernel. O entrypoint confirma os principais controles antes
de carregar as definições sob teste. Se algum controle falhar, a execução para.

`tests/test_security_contracts.py` verifica definições reais extraídas por AST,
com banco, usuários e provedores fictícios. Não executa imports do aplicativo,
decoradores FastAPI ou dependências padrão das rotas. Testa cadastro/hash sem
logs, erros e access logs OAuth, validação sem eco de credenciais, configuração
do laboratório, bloqueio antes da chamada paga, opt-in explícito com mock e
sintaxe Python da cópia aprovada. Inspeciona o frontend como texto, não renderiza
React. Nenhuma chamada Google, Meta, OpenAI ou Gemini é feita.

Os testes existentes de integração continuam em `tests/test_campaign_sync.py`,
`test_dynamic_reports.py`, `test_daily_analysis.py` e `test_reports_and_ai.py`.
Usam dois usuários fictícios, clientes separados e SQLite em memória. O caso de
IA demonstrativa foi atualizado para exigir opt-in do operador e ganhou o caso
403 sem chamada ao gerador. A suíte FastAPI completa e o build React não foram
executados neste lote: o Linux disponível não possui as dependências nativas
compatíveis, e a `.venv` Windows não é usada como fallback fora do sandbox.
Portanto, os contratos aprovados não equivalem a um teste ponta a ponta.

A cópia descartável fica no caminho informado ao final. Os sistemas de arquivos
tmpfs desaparecem com o namespace. Não são promovidos arquivos produzidos pelo
processo testado para os relatórios da auditoria.

## Próximo lote, ainda pendente

Vincular OAuth ao navegador/sessão e impedir reutilização de state. Depois,
separar chaves JWT/cifra com migração, revisar compose/rede do banco e atualizar
dependências com testes compatíveis. Nada disso é considerado corrigido por
este primeiro lote.
