# Estabilização local de segurança — 22/10/2026

## Estado atual

Manutenção autorizada pelo usuário e aplicada à instalação local em `D:\dashflow`.
O banco em uso é SQLite. Nenhum PostgreSQL, container, provedor externo ou serviço
de hospedagem foi alterado. Backend e frontend estavam parados e permaneceram
parados. É necessário fazer login novamente no Dash por causa da rotação JWT.

## Operações realizadas

1. Confirmados ausência de Uvicorn e de listeners nas portas 8000/3000/5173.
   Os processos Python encontrados eram servidores de linguagem e não foram encerrados.
2. Criado diretório privado `C:\Users\guidu\DashPrivate\maintenance-20261022`,
   com herança NTFS desativada e acesso somente ao usuário operador e SYSTEM.
3. Backup consistente do SQLite e cópia privada do `.env` antes da manutenção.
   Backup reaberto, `integrity_check` aprovado e conteúdo de todas as tabelas comparado.
4. Pré-verificação confirmou leitura das oito integrações salvas.
5. Aplicada a recriptografia dos 16 valores de access/refresh token com chave
   independente. Comparação com o backup confirmou preservação exata dos valores
   decifrados. Nenhum token foi exibido nem enviado a terceiros.
6. Segredo JWT substituído por valor aleatório forte. Chave transitória removida
   após verificação. Isso invalida sessões anteriores, não as conexões de anúncios.
7. Aplicada migration `e821ac631042 -> f132bd742153`, criando `oauth_attempts`.
8. Conferidos integridade, dados de negócio fora dos campos cifrados e variáveis
   não relacionadas do `.env`: preservados. ACL do `.env` restrita ao operador e SYSTEM.
9. Instaladas as versões de `app/requirements.txt` na `.venv` Windows/Python 3.11.
   `pip check`: nenhum requisito quebrado. Frontend atualizado pelo lock npm.
   Instalações sem scripts de lifecycle do projeto e com wheels binários Python.
10. Criado backup cifrado do banco atualizado com outra chave independente.
    Restauração em arquivo privado novo, integridade e comparação de todas as
    tabelas aprovadas. Não houve sobrescrita do banco ativo.

### Interrupção e retomada da cifra

A primeira aplicação interrompeu após o commit dos tokens e antes de finalizar
o `.env`/JWT. O keyring de transição permaneceu disponível. A verificação somente
leitura confirmou os 16 valores sob a chave nova e os conteúdos originais íntegros.
A retomada com o MESMO key-file concluiu e removeu o keyring antigo. O handler
original omitiu a exceção, portanto não há evidência para atribuir uma causa-raiz
ao primeiro encerramento. Nenhuma chave foi descartada ou substituída às cegas.

## Testes e build

- 92 testes aprovados na suíte completa: autenticação com bcrypt/JWT reais e
  usuários fictícios, posse de clientes, campanhas, sincronização fictícia,
  relatórios dinâmicos, IA com mocks, OAuth Google/Meta e os 39 contratos anteriores.
- Seis testes novos exercitam os callbacks FastAPI, cookies, consentimento
  recusado, expiração, outro navegador, posse e replay sem chamar provedores reais.
- Quatro testes novos cobrem cadastro/login/me, hash não exposto, erro genérico
  de login, rejeição de JWT inválido/assinado pelo segredo anterior e validação.
- A cadeia completa Alembic, de banco vazio até `f132bd742153`, passou em SQLite
  descartável dentro do isolamento.
- Build React/Vite 7.3.7 aprovado com Node 24.22.1 Linux e o lock atual. Foram
  transformados 2.563 módulos. O bundle JS tem aproximadamente 1,02 MB sem gzip
  e 309 kB com gzip. O aviso de chunk grande permanece para otimização futura.
- Corrigido o alias ESM de `vite.config.ts`: `fileURLToPath(new URL(...,
  import.meta.url))` substitui `__dirname`, funcionando também no config runner.
- `prop-types` já era dependência transitiva de react-helmet. A adição direta
  experimental foi revertida. Os erros de resolução no build isolado deixaram
  de ocorrer com concorrência de arquivos limitada a 32 no runner de testes.

### Isolamento

Os testes/build usam cópia aprovada sem `.env`, banco real, venv ou Git. Fonte,
dependências e ferramentas são somente leitura. Os downloads/instalações de
ferramentas e dependências ocorreram ANTES, por ferramentas controladas pelo
operador; nenhum teste/build pode baixar dependências.

Namespace de rede separado, seccomp negando sockets não-AF_UNIX, chroot sem home
ou `/mnt` do host, ambiente recriado com dados fictícios. UID real não-root,
capabilities removidas e no-new-privileges antes de executar o alvo. AF_UNIX e
threads/processos limitados permitem TestClient, asyncio e esbuild. Apenas o
sumidouro `/dev/null` e a fonte de entropia `/dev/urandom` são expostos, não uma
árvore de dispositivos. Nenhum resultado escrito pelo alvo é retido.

Limites: dois CPUs por afinidade, 60s CPU por processo, 120s de parede com mais
3s para encerramento, 64 processos/threads por UID não-root, 512 descritores,
16 MiB por arquivo, scratch tmpfs 128 MiB. Python tem espaço virtual de 1 GiB.
Node tem heap V8 de 384 MiB, dados de 1 GiB e espaço virtual limitado a 8 GiB
para reservas do runtime. Core dumps desativados.

Preparação e falhas do launcher (sem execução fora do isolamento): capabilities
de montagem precisaram ser retidas apenas até a montagem do namespace e depois
removidas; argv[0] absoluto permitiu ao Python relocável encontrar a stdlib sem
`/proc`; o SDK gRPC exigiu fonte de entropia. Os limites não foram removidos para
contornar essas falhas.

Reprodução no mesmo computador, com o toolchain já provisionado:

```powershell
.\scripts\security\run-full-isolated.ps1 -Component python
.\scripts\security\run-full-isolated.ps1 -Component frontend
```

O runner de build limita operações paralelas de arquivos a 32 e usa configLoader
runner para não escrever no source read-only. O `dist` é temporário e descartado;
não é um artefato implantado. Não houve validação visual/E2E no navegador.

## Backups e retorno ao uso

Backups, cópias do `.env`, key-files e restaurações estão no diretório privado
citado acima, fora do repositório. Não faça commit, compartilhe ou apague essa
pasta durante a homologação. Há snapshots e cópias `.env` sem cifra para recuperação,
protegidos por ACL, além do backup cifrado. Não existe cópia externa automática.

O arquivo de tokens/JWT deve ser recuperado JUNTO com o banco correspondente.
Não restaure somente um `.env` antigo sobre o banco novo: isso pode impedir a
leitura das integrações. Preserve os backups até definir retenção e recuperação.

Para iniciar normalmente em dois terminais:

```powershell
cd D:\dashflow
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

```powershell
cd D:\dashflow\my-app
npm run dev
```

Faça login novamente. Valide no browser os clientes, campanhas, relatórios e
reconexões Google/Meta. Consentimento e 2FA dependem do usuário. Nenhum servidor
ficou rodando em segundo plano durante esta manutenção.

## Pendências preservadas

Não houve deploy, HTTPS real, teste contra Google/Meta ou chamada paga de IA.
Também não foram ativados backups agendados, retenção externa ou alertas.
PostgreSQL e rotação de sua role continuam pendentes se forem usados no deploy.
A consulta OSV do lote anterior é histórica sobre versões propostas, não uma
nova varredura de todos os transitivos instalados Windows/Linux nesta etapa.
As demais melhorias da auditoria, como revogação de sessão, política de senha e
orçamento por assinante, não foram silenciosamente marcadas como resolvidas.
