# Segurança e preparação de publicação

Este guia descreve a preparação de produção e os procedimentos de manutenção.
A manutenção local de 22/10/2026 já migrou SQLite/tokens/JWT, aplicou Alembic e
atualizou dependências. Foram aprovados 92 testes e o build React isolados.
Veja [o registro de estabilização](security-stabilization.md) antes de executar
comandos: NÃO repita a migração concluída nem gere outra chave sem necessidade.
O app não foi publicado; as etapas de servidor, TLS e operação seguem pendentes.

## Atualizar sua instalação local com segurança

Pare TODOS os processos Uvicorn antes de mexer em banco ou chaves. Preserve o
repositório e use o Python 3.11 da venv. Não exiba nem cole `.env`/segredos.

1. Instale as versões novas: `python -m pip install --only-binary=:all: -r app/requirements.txt`.
2. Verifique as conexões sem alterá-las:

```powershell
python scripts/maintenance/migrate_token_encryption.py --env-file .env --key-file C:\DashPrivate\token_key --backup-dir C:\DashPrivate\migration-backups
```

3. Se a verificação terminar sem erro, aplique com backend parado:

```powershell
python scripts/maintenance/migrate_token_encryption.py --env-file .env --key-file C:\DashPrivate\token_key --backup-dir C:\DashPrivate\migration-backups --apply --backend-stopped --rotate-jwt
python -m alembic upgrade head
```

A pasta `C:\DashPrivate` deve ser privada para seu usuário. No Windows, confira
as ACLs: modos POSIX 0600/0700 não substituem permissões NTFS. O comando de
migração faz backup consistente e integrity_check de SQLite e preserva uma
cópia privada do `.env`. Para PostgreSQL, exige `--postgres-backup` apontando
para um dump recente cuja restauração tenha sido validada pelo operador.

`--rotate-jwt` é opcional: gera novo segredo forte e encerra sessões antigas, mas
não desconecta Google/Meta. Sem a opção, o JWT permanece igual. A nova chave de
cifra é independente. A migração monta primeiro um keyring de transição, troca
os tokens em transação e verifica todos antes de remover as chaves antigas.
Se houver falha, NÃO apague key-file/keyring nem altere SECRET_KEY. Retente com o
mesmo key-file após parar o backend. Não use uma chave aleatória nova a cada tentativa.

4. Atualize o frontend, com Node >=22.12: `npm ci` dentro de `my-app`.
5. Antes de uso real, execute a suíte completa em ambiente de testes isolado,
   compile o frontend e teste login, Google, Meta, seleção de contas e relatórios.
6. Reinicie o backend e o frontend. Fluxos OAuth iniciados antes da atualização
   devem ser reiniciados. Integrações salvas continuam válidas.

Não é preciso reexecutar OAuth para migrar os tokens. O fallback de cifra
derivada do JWT só permanece como compatibilidade temporária em desenvolvimento.
Produção recusa inicialização sem chave independente válida.

## OAuth

`oauth_attempts` guarda apenas hashes do state e do nonce do navegador, IDs do
proprietário/cliente/plataforma e validade de dez minutos. O callback exige o
cookie correto e uma atualização condicional consome a tentativa ANTES da troca
com o provedor. Outra aba/navegador, plataforma trocada, expiração e replay são
recusados. O cookie é HttpOnly, SameSite=Lax e, em produção, Secure com prefixo
`__Host-`, sem Domain e Path=/, evitando cookie de domínio pai.

Axios usa `withCredentials`. Desenvolvimento deve usar os mesmos nomes de host
configurados no callback. A configuração de produção pressupõe app/API no mesmo
domínio registrável, por exemplo app.seudominio.com e api.seudominio.com. Domínios
registráveis diferentes exigem outra análise de cookies/CSRF; não troque
SameSite=Lax para None às cegas. Iniciar duas conexões da mesma plataforma no
mesmo navegador substitui o cookie anterior; reinicie o fluxo mais antigo.

## Banco local e senha antiga

O compose local publica `127.0.0.1:5432`, não todas as interfaces. O password vem
de `.secrets/postgres_password` (ignorado pelo Git) ou do caminho indicado por
`POSTGRES_PASSWORD_FILE`. Nada foi aplicado ao container existente neste lote.

IMPORTANTE: `POSTGRES_PASSWORD_FILE` inicializa volumes NOVOS. Ele não altera a
senha de uma role em volume existente. Não gere outra senha e presuma que o
banco a adotou. Para o banco existente: backup/restauração testada, manutenção,
rotação segura da role pelo administrador, atualização do segredo e da URL do
app e verificação antes de reabrir tráfego. Não use `docker compose down -v`.
SQLite local não é migrado automaticamente para PostgreSQL.

## Base de produção, ainda sem deploy

Arquivos em `deploy` oferecem uma instalação NOVA, separada da atual:

- Caddy serve o frontend compilado, obtém/renova certificados e redireciona HTTP
  para HTTPS quando DNS e portas estiverem corretos. API e frontend têm hosts
  distintos do mesmo domínio registrável. Não exponha o Vite dev server.
- Só 80/443 ficam públicos. PostgreSQL não publica porta. API não publica 8000.
- Caddy tem IP fixo 172.30.0.2. Uvicorn confia em forwarded headers SOMENTE desse
  IP. Caddy substitui X-Forwarded-For/Proto recebidos. Se a rede conflitar, altere
  subnet, IP e allowlist juntos. Não use `forwarded-allow-ips=*`.
- API executa como usuário não-root, filesystem somente leitura, sem capabilities,
  tmpfs/limites de recursos e exatamente um worker. PostgreSQL usa uma role
  `dashflow_app` sem superuser para as tabelas da aplicação.
- Segredos da API são lidos via variáveis `*_FILE`. Arquivos não são criptografados
  magicamente pelo Compose: proteja o host e as permissões. Não copie segredos
  para imagens, repositório ou argumentos de build.
- Produção valida hosts/CORS/HTTPS/chaves/limites, desativa docs/OpenAPI públicos,
  adiciona headers de segurança e `no-store`, limita corpo a 256 KiB, auth a
  10/min por IP, geração a 5/min por IP e restante da API a 180/min por IP.
  Leitura de relatórios usa a cota comum, não a de geração. Retorna 413/429 e Retry-After.
- O limitador é limitado a 10.000 chaves ativas e recusa novas quando saturado.
  É POR PROCESSO. Antes de múltiplos workers/réplicas, adote um limitador
  compartilhado no gateway/Redis. A reserva diária de IA por cliente já é no banco.

Configuração inicial em um servidor Linux novo, após contratar/definir hospedagem:

1. DNS de app/API para o servidor, firewall e acesso SSH restrito, somente 80/443
   públicos. Não abrir 5432/8000. Se usar Cloudflare, Full (strict), não Flexible.
   No starter, o limite considera o IP que chega ao Caddy. Com CDN na frente,
   isso pode ser o IP da CDN. Só configure IP real após restringir a origem e
   validar a allowlist do proxy; não confie livremente em CF-Connecting-IP/XFF.
2. Checkout sem `.env` local. Copie `.env.production.example` para `.env.production`
   e substitua TODOS os hosts de exemplo. Complete credenciais OAuth no backend.
   Defina também `APP_DOMAIN`, `API_DOMAIN`, `ACME_EMAIL` nesse arquivo para o Compose.
3. `python scripts/maintenance/init_production_secrets.py --directory .secrets`
   somente para instalação NOVA. Esse comando não sobrescreve segredos existentes.
4. Ajuste permissões para os arquivos de API serem legíveis pelo UID 10001 do
   container, mas não por outros usuários. Os arquivos Postgres devem ser
   legíveis pelo entrypoint. Não aplique `chmod 644` indiscriminadamente.
5. `docker compose --env-file .env.production -f deploy/compose.production.yml config --quiet`
6. Construa imagens e valide Caddy/configuração em homologação, com segredos de
   teste. Fixe imagens por digest aprovadas antes do primeiro release.
7. Suba o db e execute o serviço migrate (profile maintenance), depois api/web.
   Não exponha o frontend antes de concluir migrations e ensaio de restauração.
8. Registre as URLs HTTPS de callback nos painéis Google/Meta e faça smoke test.

O starter cria um volume PostgreSQL novo. Não adota o banco atual nem transfere
seus clientes automaticamente. Sem DNS/servidor/credenciais de hospedagem, TLS
e publicação não podem ser considerados concluídos ou validados.

## Backups e restauração

`scripts/maintenance/database_backup.py` oferece snapshot consistente de SQLite
ou pg_dump custom do serviço Compose. Cifra com Fernet e verifica a leitura.
Limite atual: 128 MiB por dump. A chave de BACKUP é separada de JWT e tokens e
não pode ficar junto dos arquivos de backup. Intermediário plaintext existe
apenas em diretório temporário privado durante a operação. Proteja/cripte o disco.
Falhas não imprimem URLs, chaves nem tokens.

```powershell
python scripts/maintenance/database_backup.py --sqlite CAMINHO_DO_BANCO --key-file C:\DashPrivate\backup_key --output-dir C:\DashPrivate\encrypted-backups
python scripts/maintenance/database_backup.py --restore ARQUIVO.fernet --restore-to C:\DashPrivate\restore-test.sqlite --key-file C:\DashPrivate\backup_key
```

Restauração escreve SOMENTE arquivo novo. Para Postgres, o arquivo decifrado é
dump custom: use pg_restore em banco isolado e valide contagens/integridade.
Não execute contra produção como primeiro teste. `deploy/dash-backup.*` prepara
um timer diário Linux, ainda não instalado/ativado. Configure usuário, caminhos,
ACLs e chave externa. Acesso ao socket Docker equivale a privilégio administrativo
do host; não conceda esse acesso ao usuário do aplicativo.

Faltam configurar armazenamento externo e retenção no destino (por exemplo,
7 diários e 4 semanais, conforme RPO/RTO definidos). Não há remoção automática
de backups antigos neste lote. Um backup só é operacionalmente confiável após
ensaio periódico de restauração, não só por existir.

## Monitoramento

- `/health`: liveness sem dados internos. `/ready`: testa SELECT 1 no banco e
  devolve 503 genérico quando indisponível. Healthcheck Docker também testa
  socket local e banco, sem afrouxar TLS/hosts da API.
- `/ops/metrics`: somente com `Authorization: Bearer <OPS_METRICS_TOKEN>`. Sem
  token ou com token errado, 404. Contadores agregados por processo, sem clientes,
  contas, prompts ou segredos. A rota não substitui métricas persistentes.
- Logs JSON de request_id, categoria, método, status e duração. Não registram
  URL/query/headers/body/usuário. Caddy remove request e resp_headers dos logs.
  Logs dos containers têm rotação 10 MiB x 3.
- Configure um monitor externo para HTTPS `/ready`, validade TLS, 5xx/429,
  falha/atraso de backup, espaço em disco e orçamento da IA. Destino de alertas
  e ferramentas ainda dependem da hospedagem. Não foi conectado nenhum serviço
  externo nem enviada mensagem neste lote.

## Dependências e validação

As versões foram consultadas nos registros oficiais PyPI/npm. Foram atualizados
framework, parser multipart, validação, ferramentas, SDKs e utilitários com pins.
Vite passou de 4 para 7, com plugin React compatível; Axios e Router 6 receberam
patches. Mantido bcrypt 4.0.1/passlib para não reabrir a incompatibilidade anterior.
Removido eslint-config-react-app, que não tinha configuração/consumidor neste app Vite.

Na preparação inicial, o lock npm foi recalculado por metadados e o pip fez
dry-run. Na manutenção posterior, venv/node_modules foram atualizados e `pip
check` passou. A suíte completa de 92 testes e o build Vite passaram em Linux
isolado com as dependências novas. Isso não substitui validação visual, OAuth
real no browser, chamadas aos provedores ou validação da imagem Docker.

Consulta OSV posterior: 573 versões do lock npm e da resolução pip foram
consultadas, sem falhas de consulta, com 5 correspondências residuais. Isso não
representa 5 exploits. É o inventário histórico do lote de preparação, não uma
nova consulta sobre os transitivos instalados posteriormente:

- `python-jose 3.5.0`: alerta de confusão de algoritmo com chave pública DER.
  O app aceita somente HS256 com segredo privado, não chave pública, e limita
  bearer a 4096 caracteres. A combinação descrita não foi identificada no app.
- `ecdsa 0.19.2`: dependência indireta de jose, sem uso no fluxo HS256. Avaliar
  substituição futura da biblioteca JWT com regressão de sessões.
- `react-router 6.30.6`: dois avisos. Um exige SSR/hydration (o app usa roteamento
  declarativo). O outro envolve destino de navegação não confiável. Os caminhos
  atuais são internos. A atualização para 7.18+ deve ser validada com navegação
  completa, não forçada para fazer o contador desaparecer.
- `braces 3.0.3` e `postcss-selector-parser 6.1.5`: processamento de padrões/CSS
  não confiáveis. Aqui pertencem à cadeia de build de fontes do projeto, não a
  endpoint que recebe CSS do usuário. Não aceite código/CSS de clientes no build.

O resultado anterior (44 entre 836 versões instaladas/inventariadas) tem outro
universo e não deve ser comparado diretamente como percentual de correção.
Os registros originais foram preservados; não há promessa de zero vulnerabilidades.

Fontes técnicas: [proxy FastAPI](https://fastapi.tiangolo.com/advanced/behind-a-proxy/),
[Fernet/MultiFernet](https://cryptography.io/en/latest/fernet/),
[Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/),
[Postgres Docker](https://github.com/docker-library/docs/blob/master/postgres/README.md),
[Caddy HTTPS](https://caddyserver.com/docs/automatic-https),
[Caddy logs](https://caddyserver.com/docs/caddyfile/directives/log).
