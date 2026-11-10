# DASH — repaginação Glassy

Implementada no frontend React existente, em `my-app`, em 09/11/2026.

## Executar no Windows

Abra dois terminais PowerShell. O backend usa o `.env` já existente na raiz; não é necessário alterar credenciais para a repaginação.

Backend:

```powershell
Set-Location 'G:\Programação\dash'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
Set-Location 'G:\Programação\dash\my-app'
npm run dev
```

Abra http://localhost:3000 e entre com sua conta existente. A API padrão é http://localhost:8000; `VITE_API_BASE_URL` continua disponível para outra configuração. Node >=22.12 é exigido pelo projeto. Se as dependências ainda não estiverem instaladas, execute `npm ci` em `my-app` e instale `app/requirements.txt` no ambiente Python existente.

`FrontEnd` contém a interface Streamlit legada; esta repaginação foi realizada em `my-app`. A alteração pré-existente do usuário em `FrontEnd/home.py` foi preservada.

## Referências e adaptação

- Glassy Dashboard v5: analisados tokens, material de vidro, painel, navegação e HomeView em `G:\Glassy Dashboard v5\Glassy Dashboard v5`.
- O fundo `public/image.png` foi reutilizado como `my-app/public/glassy-workspace.png`, com sobreposição azul escura. Os padrões de preenchimento translúcido, reflexo interno, bordas e profundidade foram adaptados em `src/index.css`.
- O React 18, Tailwind, React Router, Radix e os fluxos do DASH foram mantidos. O template React 19 não substituiu o projeto. Nenhuma dependência foi adicionada.
- Briefing e cartões do manual em `C:\Users\duffess\Desktop\Dash Ideas`: azul #2563EB, índigo #4F46E5, base #0F172A, Astralys no logotipo e Poppins na interface, Unbounded nos títulos principais. Astralys permanece local; Poppins e Unbounded usam Google Fonts com fallback.

## Alterações

- Navegação flutuante no desktop e barra inferior no celular, links ativos, acesso ao perfil e logout existentes.
- Visão geral com resumo da agência, métricas da API, análises salvas e prévia das campanhas existentes. Valores formatados em pt-BR.
- Estados de carregamento, falha e ausência de campanhas separados; falha de API não se torna resultado zero. A evolução diária continua explicitamente indisponível.
- Clientes, conexões, campanhas, relatórios, configurações, login e cadastro compartilham cores, superfícies e controles.
- O laboratório de relatórios já existente fica recolhido e identificado como demonstração. Relatórios reais, exportação HTML e impressão continuam usando os serviços existentes. O HTML dos relatórios gerados e salvos não foi reescrito.
- Configurações exibe os dados de perfil em leitura, pois não havia persistência; removida a falsa confirmação de salvamento. Conexões encaminham à tela do cliente. A criação/detalhamento de campanhas ainda indisponíveis têm controles desabilitados e indicação de estado.
- Modais com Radix, foco visível, fechamento por Escape e retorno de foco; link para pular ao conteúdo; campos de busca identificados e autocomplete nos formulários de autenticação.
- `prefers-reduced-motion` no CSS e `MotionConfig reducedMotion="user"` na árvore React. Transparência limitada às superfícies externas; áreas internas não repetem blur.

## Validação realizada

- `npm run build --prefix my-app`: aprovado.
- ESLint com regras `no-undef` e `no-unreachable`: aprovado em todos os arquivos JS/JSX de `my-app/src`.
- `git diff --check`: aprovado.
- Navegação de visão geral, clientes, campanhas, relatórios e configurações em 390, 768 e 1440 px: sem transbordamento horizontal da página.
- Revisão visual do login, dashboard, clientes, conexões, configurações e modal de IA; valores preenchidos no dashboard revisados em celular, tablet e desktop.
- Login, cadastro de cliente, filtro de campanhas e criação/visualização de relatório sem IA pelo backend existente: aprovados em banco temporário.
- Fechamento do modal por Escape e retorno ao botão de abertura: confirmado no DOM.
- Falha de API: mensagem de erro, ação para repetir e quatro indicadores com “—”, sem zeros fictícios.
- Preferência de movimento reduzido verificada no código; a emulação dessa preferência não estava exposta no navegador de teste.

Os testes usaram uma instância local com SQLite separado em `%TEMP%\dash-glassy-validation`, sem chaves de provedores. As duas campanhas sintéticas são identificadas por “QA sintético” e nunca foram inseridas no banco do projeto. A instância temporária foi encerrada, e a sessão de QA desconectada.

Capturas deste ambiente isolado: [desktop](design-validation/dashboard-desktop.jpg) e [celular](design-validation/dashboard-mobile.jpg). Os valores nelas são exclusivamente fixtures de teste.

## Limites

- Não foram feitas chamadas reais de OAuth, sincronização de anúncios ou IA paga. Essas integrações e seus contratos permanecem existentes, sem alteração do backend.
- A seleção de contas depende de OAuth e não foi exercitada contra provedores reais; o modal reutiliza o Radix já instalado.
- A suíte de backend exige o executor Linux isolado do repositório; não foi executada no host Windows nesta alteração de frontend.
- O build informa um bundle JS acima de 500 kB (~614 kB antes de gzip). O console de desenvolvimento apresenta avisos das dependências existentes React Helmet/StrictMode e React Router v6. Não houve exceções de renderização na versão final.
- Nenhuma migração, alteração de autenticação, regra de negócio, exportador ou dado real foi feita.
