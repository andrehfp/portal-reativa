# Portal Reativa

Portal web minimalista para busca de propriedades imobiliárias com processamento de linguagem natural.

## Características

- 🔍 **Busca em linguagem natural**: "casas de até 200k no jardim carvalho"
- ⚡ **Interface rápida**: HTMX para atualizações dinâmicas sem recarregar
- 🎨 **Design limpo**: Interface minimalista com Tailwind CSS
- 📱 **Responsivo**: Funciona perfeitamente em mobile e desktop
- 🏠 **Filtros inteligentes**: Preço, tipo, localização, quartos automaticamente

## Tecnologias

- **FastAPI** - Backend rápido e moderno
- **HTMX** - Interatividade sem JavaScript complexo
- **Tailwind CSS** - Estilização utilitária
- **SQLite** - Conexão direta com dados existentes
- **Jinja2** - Templates server-side

## Instalação

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Execute o servidor:
```bash
python main.py
```

3. Acesse: http://localhost:8000

## Exemplos de Busca

O portal entende linguagem natural em português:

- `casas de até 200k no jardim carvalho`
- `apartamentos 2 quartos para alugar`
- `terrenos acima de 300k`
- `casas para venda em curitiba`
- `aptos até 150 mil no centro`

## Estrutura do Projeto

```
portal-reativa/
├── main.py              # Aplicação FastAPI
├── requirements.txt     # Dependências Python
├── templates/
│   ├── base.html       # Template base
│   ├── index.html      # Página principal
│   └── components/
│       └── property_grid.html
└── static/             # Arquivos estáticos (futuro)
```

## Funcionalidades de Busca

### Filtros de Preço
- `até 200k`, `máximo 300k`
- `acima de 150k`, `mínimo 100k`

### Tipos de Propriedade
- `casa`, `casas`
- `apartamento`, `apto`, `aptos`
- `terreno`, `terrenos`
- `sala`, `loja`

### Localização
- `no centro`, `na vila madalena`
- `em curitiba`, `jardim carvalho`

### Características
- `2 quartos`, `3 dormitórios`
- `para venda`, `para alugar`

O sistema combina automaticamente múltiplos filtros numa única busca.