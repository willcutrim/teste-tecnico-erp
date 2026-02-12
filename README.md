# ERP - Gestão de Pedidos

Backend para sistema de gestão de pedidos desenvolvido com Django + DRF.

## Stack

- **Django + DRF** - Framework web e API REST
- **MySQL** - Banco de dados
- **Redis** - Cache
- **Docker + Docker Compose** - Containerização
- **Pytest** - Testes

## Estrutura do Projeto

```
src/
├── config/          # Configurações do Django
├── common/          # Código compartilhado (mixins, utils)
├── customers/       # App de clientes
├── products/        # App de produtos
├── orders/          # App de pedidos (com state_machine e events)
└── health/          # Health check endpoint
```

## Como Executar

### Com Docker (recomendado)

```bash
# Copiar variáveis de ambiente
cp .env.example .env

# Subir os containers
docker-compose up -d

# Executar migrations
docker-compose exec web python manage.py migrate

# Criar superusuário
docker-compose exec web python manage.py createsuperuser
```

### Localmente

```bash
# Criar virtualenv
python -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com configurações locais

# Executar migrations
cd src
python manage.py migrate

# Executar servidor
python manage.py runserver
```

## Endpoints

| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/health/` | Health check da aplicação |

## Testes

```bash
# Com Docker
docker-compose exec web pytest

# Localmente
cd src
pytest
```

## Variáveis de Ambiente

Veja [.env.example](.env.example) para todas as variáveis disponíveis.
