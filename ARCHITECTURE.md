# Arquitetura do Sistema

## Visão Geral

Este documento descreve a arquitetura do módulo de Gestão de Pedidos do ERP, detalhando os padrões adotados, fluxo de dados e decisões técnicas.

## Stack Tecnológica

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| Framework Web | Django | 5.x |
| API REST | Django REST Framework | 3.14+ |
| Banco de Dados | MySQL | 8.0 |
| Cache | Redis | 7.x |
| Containerização | Docker + Docker Compose | - |
| Testes | Pytest | 8.x |
| Documentação API | drf-spectacular (OpenAPI 3) | - |

## Estrutura de Pastas

```
src/
├── config/              # Configurações do Django (settings, urls, wsgi)
├── common/              # Código compartilhado entre apps
│   ├── models.py        # Mixins reutilizáveis (Timestamp, SoftDelete)
│   └── services.py      # Serviços base
├── clientes/            # App de gestão de clientes
├── produtos/            # App de gestão de produtos
├── pedidos/             # App de gestão de pedidos (core do sistema)
│   ├── models.py        # Entidades de domínio
│   ├── services.py      # Regras de negócio
│   ├── repositories.py  # Abstração de acesso a dados
│   ├── state_machine.py # Máquina de estados do pedido
│   ├── events.py        # Eventos de domínio
│   ├── views.py         # Controllers (endpoints)
│   └── serializers.py   # DTOs de entrada/saída
├── health/              # Health check endpoint
└── tests/               # Testes automatizados
    ├── unit/            # Testes unitários
    └── integration/     # Testes de integração
```

## Padrões Arquiteturais

### 1. Arquitetura em Camadas

O sistema segue uma arquitetura em camadas com separação clara de responsabilidades:

```
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Apresentação                   │
│                  (Views / Controllers)                      │
│         Responsável por HTTP request/response               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Aplicação                      │
│                      (Services)                             │
│         Orquestra casos de uso e regras de negócio          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Domínio                        │
│              (Models, State Machine, Events)                │
│         Entidades, regras de domínio e eventos              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Camada de Infraestrutura                    │
│                    (Repositories)                           │
│         Acesso a dados, cache, serviços externos            │
└─────────────────────────────────────────────────────────────┘
```

### 2. Repository Pattern

Os repositórios abstraem o acesso ao banco de dados, permitindo:

- **Testabilidade**: Fácil mock dos repositórios em testes
- **Desacoplamento**: Services não conhecem detalhes do ORM
- **Centralização**: Queries complexas em um único lugar

```python
# Exemplo de uso
class PedidoRepository:
    def obter_com_lock(self, pedido_id):
        """Obtém pedido com lock para evitar condição de corrida."""
        return Pedido.objects.select_for_update().get(id=pedido_id)
    
    def criar(self, cliente, status, chave_idempotencia, ...):
        return Pedido.objects.create(...)
```

### 3. Service Layer

Os services encapsulam a lógica de negócio e orquestram operações:

| Service | Responsabilidade |
|---------|------------------|
| `CriarPedidoService` | Criação de pedidos com validação e reserva de estoque |
| `AlterarStatusPedidoService` | Transições de status com validação |
| `CancelarPedidoService` | Cancelamento com devolução de estoque |

```python
# Exemplo: CriarPedidoService
class CriarPedidoService:
    def executar(self, cliente_id, itens, chave_idempotencia, ...):
        # 1. Verifica idempotência
        # 2. Valida cliente ativo
        # 3. Valida produtos e estoque
        # 4. Cria pedido atomicamente
        # 5. Reserva estoque
        # 6. Retorna pedido
```

### 4. State Machine Pattern

Gerencia as transições de status do pedido de forma controlada:

```
           ┌──────────────┐
           │   PENDENTE   │
           └──────┬───────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  CONFIRMADO  │    │  CANCELADO   │
└──────┬───────┘    └──────────────┘
       │
       ▼
┌──────────────────┐
│ EM_PROCESSAMENTO │────────┐
└──────┬───────────┘        │
       │                    ▼
       ▼             ┌──────────────┐
┌──────────────┐     │  CANCELADO   │
│   ENVIADO    │     └──────────────┘
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   ENTREGUE   │
└──────────────┘
```

**Benefícios:**
- Transições inválidas são rejeitadas automaticamente
- Fácil adicionar novos status ou regras
- Código autodocumentado

### 5. Domain Events

Eventos são emitidos em mudanças importantes do domínio:

| Evento | Quando Emitido |
|--------|----------------|
| `PEDIDO_CRIADO` | Novo pedido criado |
| `PEDIDO_CONFIRMADO` | Status alterado para confirmado |
| `PEDIDO_CANCELADO` | Pedido cancelado |
| ... | ... |

Atualmente os eventos são logados. Podem ser estendidos para:
- Notificações (email, push)
- Integração com sistemas externos
- Event sourcing completo

### 6. Soft Delete

Registros não são deletados fisicamente. O mixin `SoftDeleteMixin` adiciona:

```python
class SoftDeleteMixin(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    def delete(self):
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        self.deleted_at = None
        self.save()
```

O `SoftDeleteManager` filtra registros deletados automaticamente.

## Fluxo de Dados

### Criação de Pedido

```
1. Cliente envia POST /api/v1/orders/
   {cliente_id, itens[], idempotency_key}
                    │
                    ▼
2. PedidoViewSet.create()
   - Valida payload (CriarPedidoSerializer)
   - Chama CriarPedidoService
                    │
                    ▼
3. CriarPedidoService.executar()
   - Verifica idempotência (retorna pedido existente se já criado)
   - Valida cliente ativo
   - Inicia transação atômica
                    │
                    ▼
4. Dentro da transação (@transaction.atomic):
   - Obtém produtos com SELECT FOR UPDATE (lock)
   - Valida estoque para todos os itens
   - Cria Pedido
   - Cria ItemPedido para cada item
   - Decrementa estoque de cada produto
   - Atualiza valor total
                    │
                    ▼
5. Retorna Response
   - 201 CREATED (novo pedido)
   - 200 OK (pedido já existente - idempotente)
```

### Controle de Concorrência

```
Requisição A ──────────┐
                       │
Requisição B ──────────┼───► SELECT FOR UPDATE
                       │         │
                       │         ▼
                       │    [Lock adquirido por A]
                       │         │
                       │         ▼
                       │    A processa e faz UPDATE
                       │         │
                       │         ▼
                       │    [Lock liberado]
                       │         │
                       └────────►│
                                 ▼
                            [B adquire lock]
                                 │
                                 ▼
                            B verifica estoque
                            (já decrementado por A)
                                 │
                                 ▼
                            Erro: Estoque Insuficiente
```

## Decisões Técnicas e Trade-offs

### 1. Lock Pessimista vs Otimista

**Decisão:** Lock pessimista (`SELECT FOR UPDATE`)

**Motivo:** Operações de estoque são críticas e conflitos são esperados em ambiente de produção. O lock pessimista garante consistência mesmo sob alta concorrência.

**Trade-off:** Pode criar contenção em cenários de altíssimo volume. Para escala maior, considerar:
- Filas de processamento (Celery)
- Reserva temporária de estoque
- CQRS para separar leituras de escritas

### 2. Idempotência via Banco vs Redis

**Decisão:** Chave de idempotência armazenada no banco de dados

**Motivo:** 
- Simplicidade de implementação
- Consistência transacional com o pedido
- Persistência garantida

**Trade-off:** Para volume muito alto de requisições, Redis seria mais performático. Implementação futura poderia usar Redis com TTL + fallback para banco.

### 3. State Machine in-memory vs Persistida

**Decisão:** State machine in-memory com transições definidas em código

**Motivo:**
- Simplicidade e testabilidade
- Transições são estáveis e raramente mudam
- Histórico de transições salvo separadamente

**Trade-off:** Mudanças nas regras exigem deploy. Para workflows dinâmicos, considerar engine de workflow.

### 4. Monolito Modular vs Microserviços

**Decisão:** Monolito modular (Django apps separados)

**Motivo:**
- Escopo do projeto não justifica complexidade de microserviços
- Apps são independentes e podem ser extraídos futuramente
- Deploy e debugging simplificados

**Trade-off:** Escalabilidade limitada ao servidor. Para escala, considerar:
- Horizontal scaling com load balancer
- Extração de serviços específicos (ex: estoque)

### 5. DTOs via Serializers

**Decisão:** Usar serializers do DRF como DTOs

**Motivo:**
- Validação automática
- Serialização/deserialização
- Documentação automática via OpenAPI

**Trade-off:** Acoplamento com DRF. Para APIs não-REST, criar DTOs puros (dataclasses).

## Segurança

| Aspecto | Implementação |
|---------|---------------|
| Rate Limiting | Throttling via DRF (100/min anon, 200/min user) |
| Validação de Input | Serializers com validação |
| SQL Injection | ORM do Django (queries parametrizadas) |
| Soft Delete | Dados não são perdidos permanentemente |
| Secrets | Variáveis de ambiente (.env) |

## Observabilidade

| Aspecto | Implementação |
|---------|---------------|
| Health Check | `/health/` verifica DB e Redis |
| Logs | Logging estruturado (configurável) |
| Métricas | Extensível via middleware |

## Testes

| Tipo | Cobertura | Localização |
|------|-----------|-------------|
| Unitários | Services, State Machine | `tests/unit/` |
| Integração | API endpoints | `tests/integration/` |
| Cenários críticos | Concorrência, Idempotência, Atomicidade | `tests/unit/test_cenarios_obrigatorios.py` |

**Cobertura atual: ~90%**

## Extensibilidade

### Adicionar Nova Regra de Negócio
1. Criar/modificar Service em `services.py`
2. Adicionar testes em `tests/unit/`

### Adicionar Novo Status de Pedido
1. Adicionar em `StatusPedido` (models.py)
2. Definir transições em `TRANSICOES` (state_machine.py)
3. Criar migration para o banco

### Integrar Sistema Externo
1. Criar novo evento em `events.py`
2. Implementar handler/consumer
3. Emitir evento no service apropriado

## Referências

- [Django REST Framework](https://www.django-rest-framework.org/)
- [State Pattern](https://medium.com/@sa82912045/state-machines-in-python-the-hidden-superpower-behind-reliable-systems-4c7f0db4832d)
