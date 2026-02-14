# ERP - Gestão de Pedidos

Backend para sistema de gestão de pedidos desenvolvido com Django + DRF.

## Stack

- **Django 5.2 + DRF** - Framework web e API REST
- **MySQL 8.0** - Banco de dados
- **Redis 7** - Cache
- **Docker + Docker Compose** - Containerização
- **Pytest** - Testes

## Estrutura do Projeto

```
src/
├── config/          # Configurações do Django
├── common/          # Código compartilhado (mixins, utils)
├── clientes/        # App de clientes
├── produtos/        # App de produtos
├── pedidos/         # App de pedidos (com state_machine e events)
└── health/          # Health check endpoint
```

## Como Executar

### Com Docker (recomendado)

```bash
# Copiar variáveis de ambiente
cp .env.example .env

# Subir os containers
docker compose up -d

# Aguardar o MySQL ficar saudável (cerca de 30s na primeira execução)
docker compose ps

# Executar migrations
docker compose exec web python manage.py migrate

# (Opcional) Criar superusuário para acessar o admin
docker compose exec web python manage.py createsuperuser
```

A API estará disponível em `http://localhost:8000`

### Localmente

```bash
# Criar virtualenv
python -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com configurações locais (MySQL e Redis devem estar rodando)

# Executar migrations
cd src
python manage.py migrate

# Executar servidor
python manage.py runserver
```

## Endpoints

### Health Check
| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/health/` | Health check da aplicação |

### Clientes
| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/v1/customers/` | Listar clientes |
| POST | `/api/v1/customers/` | Criar cliente |
| GET | `/api/v1/customers/{id}/` | Obter cliente |
| PUT | `/api/v1/customers/{id}/` | Atualizar cliente |
| DELETE | `/api/v1/customers/{id}/` | Remover cliente |

### Produtos
| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/v1/products/` | Listar produtos |
| POST | `/api/v1/products/` | Criar produto |
| GET | `/api/v1/products/{id}/` | Obter produto |
| PUT | `/api/v1/products/{id}/` | Atualizar produto |
| PATCH | `/api/v1/products/{id}/update_stock/` | Atualizar estoque |

### Pedidos
| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/v1/orders/` | Listar pedidos |
| POST | `/api/v1/orders/` | Criar pedido |
| GET | `/api/v1/orders/{id}/` | Obter pedido |
| PATCH | `/api/v1/orders/{id}/change_status/` | Alterar status |
| POST | `/api/v1/orders/{id}/cancel/` | Cancelar pedido |

### Documentação Interativa
| URL | Descrição |
|-----|-----------|
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI Schema |

## Testes

```bash
# Com Docker (recomendado - usa MySQL real)
docker compose exec web pytest

# Dar permissão para criar banco de testes (apenas primeira vez)
docker exec erp_mysql mysql -uroot -proot_password -e "GRANT ALL PRIVILEGES ON test_erp_pedidos.* TO 'erp_user'@'%'; GRANT CREATE ON *.* TO 'erp_user'@'%'; FLUSH PRIVILEGES;"

# Rodar testes
docker compose exec web pytest
```

### Cenários de Teste Obrigatórios

1. **Idempotência**: 3 requisições com mesma chave = apenas 1 pedido criado
2. **Atomicidade**: Falha em 1 item = rollback completo (nenhum estoque alterado)
3. **Concorrência**: 2 pedidos simultâneos disputando mesmo estoque = apenas 1 sucede

## Variáveis de Ambiente

Veja [.env.example](.env.example) para todas as variáveis disponíveis.
