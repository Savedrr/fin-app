<<<<<<< HEAD
# FinanceApp — Controle Financeiro Familiar 💰

Aplicativo web completo para controle financeiro de casais com chat inteligente via IA.

## ✨ Funcionalidades

- 🤖 **Chat com IA** — registre gastos em linguagem natural ("Gastei 50 reais no mercado")
- 📊 **Dashboard** — saldo, alertas inteligentes, gráficos e comparativos
- 📋 **Lançamentos** — histórico completo com categorias e filtros
- 🏠 **Contas Fixas** — aluguel, internet, luz, etc. com controle de pagamento
- 💰 **Receitas** — salários, renda extra, médias mensais
- 📈 **Relatórios** — análise IA, gráficos evolutivos, tabela comparativa
- 👫 **Multi-usuário** — cada um com login próprio, tudo compartilhado

## 🚀 Como rodar localmente

### 1. Instalar dependências
```bash
pip install Flask Werkzeug python-dotenv openpyxl
```

### 2. Configurar variáveis de ambiente
```bash
cp .env.example .env
# Edite o .env e coloque sua chave da Anthropic
```

Conteúdo do `.env`:
```
SECRET_KEY=uma-chave-secreta-aleatoria-aqui
ANTHROPIC_API_KEY=sk-ant-...  # Obtenha em https://console.anthropic.com
```

### 3. Rodar
```bash
python app.py
```

Acesse: **http://localhost:5000**

### Contas demo criadas automaticamente:
| Usuário | Email | Senha |
|---------|-------|-------|
| Você | voce@email.com | 123456 |
| Esposa | esposa@email.com | 123456 |

## 🔑 Chat IA — exemplos de frases

```
Gastei 35 reais no mercado
Paguei 120 de internet
Recebi 2500 de salário
Minha esposa gastou 80 com farmácia
Coloca 1200 de aluguel como conta fixa vence dia 5
Quanto gastamos este mês?
Onde podemos economizar?
```

> **Sem API Key:** o app funciona com interpretação básica de frases. Com a chave Anthropic, o chat fica muito mais inteligente e preciso.

## ☁️ Deploy no Render

### 1. Instale gunicorn
```bash
pip install gunicorn
```

### 2. Crie `Procfile` na raiz:
```
web: gunicorn app:app
```

### 3. No Render:
- Crie um novo **Web Service**
- Conecte seu repositório GitHub
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Adicione as variáveis de ambiente: `SECRET_KEY` e `ANTHROPIC_API_KEY`

> Para produção, migre para PostgreSQL substituindo `sqlite3` por `psycopg2` e ajustando as queries.

## 📁 Estrutura do projeto

```
financeapp/
├── app.py              # Backend Flask + SQLite + rotas API
├── financeapp.db       # Banco de dados (gerado automaticamente)
├── requirements.txt
├── .env.example
├── README.md
├── static/
│   ├── css/
│   │   └── main.css    # Design system completo (tema escuro)
│   └── js/
│       └── app.js      # Utilitários, sidebar, formatação
└── templates/
    ├── base.html        # Layout base com sidebar
    ├── login.html       # Tela de login/cadastro
    ├── dashboard.html   # Dashboard principal
    ├── chat.html        # Chat com IA
    ├── lancamentos.html # Lançamentos de gastos
    ├── fixas.html       # Contas fixas
    ├── receitas.html    # Receitas do mês
    └── relatorios.html  # Relatórios e análise
```

## 🛡️ Segurança

- Senhas armazenadas com SHA-256
- Sessões Flask com secret key
- Login obrigatório em todas as rotas
- Troque o `SECRET_KEY` antes de publicar!
=======
# fin-app
Aplicativo de finanças
>>>>>>> 370b3b96fbd429e1562de2b9914df6226b897afa
