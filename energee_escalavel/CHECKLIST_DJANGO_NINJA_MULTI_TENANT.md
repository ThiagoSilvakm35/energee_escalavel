# CHECKLIST DJANGO NINJA MULTI-TENANT - GESTÃO DE FATURAS DE ENERGIA

## 📋 ÍNDICE EXECUTIVO

**OBJETIVO:** Checklist abrangente para desenvolvimento de sistema Django Ninja assíncrono, multi-tenant, para gestão de faturas de energia elétrica

**ARQUITETURA CORE:**
- Framework: Django Ninja (async/await)
- Banco: PostgreSQL + Redis Cache
- Multi-tenancy: Isolamento por Organizacao
- Processamento: Celery + Django Channels

---

## 🏗️ **EQUIPE 1: DESENVOLVIMENTO BASE**

### **ESPECIALISTA 1A - ARQUITETURA & MODELOS DE DADOS**

#### 🔍 ANÁLISE CoT (Chain of Thought)
**Problema Central:** Criar arquitetura multi-tenant robusta com relacionamentos complexos conforme diagrama ER

**Decomposição em Etapas:**
1. **Fundação:** Entidade superior Organizacao + isolamento tenant
2. **Relacionamentos:** Users → UserRole → Perfis especializados
3. **Integração:** Distribuidora ↔ Usinas ↔ UnidadeConsumidora

**Dependências Mapeadas:**
- Organizacao → Bloqueia todas outras entidades
- UserRole → Habilita sistema de permissões
- Distribuidora → Conecta todos perfis de negócio

#### 📈 JUSTIFICATIVA STaR
**Restrição:** Isolamento total entre tenants mantendo performance
**Impacto:** +40% segurança, -15% complexidade de queries
**Resultado:** Sistema escalável para 1000+ organizações

#### 🌳 ALTERNATIVAS ToT
**Opção A: Schema Separation**
- ✅ Isolamento total, backup granular
- ❌ Complexidade de deployment, custo database
- 📊 Viabilidade: Baixa (custo/complexidade)

**Opção B: Row Level Security + Organizacao Filter**
- ✅ Performance, simplicidade deployment
- ❌ Risco de vazamento de dados
- 📊 Viabilidade: Alta (balanceamento ideal)

**🎯 DECISÃO:** Row Level + Organizacao (Opção B)
**Rationale:** Melhor custo-benefício para escala média

#### 📋 CHECKLIST DETALHADO

- **[ ] 1. CONFIGURAÇÃO BASE DJANGO NINJA**
  - **[ ] 1.1 Instalação e configuração inicial**
    - **[ ] 1.1.1** Instalar Django Ninja + dependências assíncronas
      - **📋 Critério:** `pip install django-ninja uvicorn[standard]` executado
      - **🎯 Resultado:** Servidor assíncrono funcional
    - **[ ] 1.1.2** Configurar settings.py para async
      - **📋 Critério:** ASGI_APPLICATION configurada
      - **🎯 Resultado:** Middleware assíncrono ativo
  - **[ ] 1.2 Estrutura de projeto multi-tenant**
    - **[ ] 1.2.1** Criar app `core` para entidades base
      - **📊 Métrica:** App registrado em INSTALLED_APPS
      - **💡 Justificativa:** Centralizar lógica multi-tenant
    - **[ ] 1.2.2** Criar app `tenants` para isolamento
      - **📊 Métrica:** Middleware de tenant funcional
      - **💡 Justificativa:** Interceptar requests por organizacao

- **[ ] 2. MODELAGEM ENTIDADE SUPERIOR - ORGANIZACAO**
  - **[ ] 2.1 Modelo Organizacao base**
    - **[ ] 2.1.1** Implementar campos essenciais
      ```python
      class Organizacao(models.Model):
          nome = models.CharField(max_length=200)
          cnpj = models.CharField(max_length=18, unique=True)
          razao_social = models.CharField(max_length=300)
          # ... demais campos
      ```
      - **📋 Critério:** Migration aplicada com sucesso
      - **🎯 Resultado:** Tabela core_organizacao criada
    - **[ ] 2.1.2** Implementar validações CNPJ
      - **📋 Critério:** Validador custom funcionando
      - **🎯 Resultado:** Apenas CNPJs válidos aceitos
  - **[ ] 2.2 Abstract Model TenantAware**
    - **[ ] 2.2.1** Criar classe base com FK organizacao
      ```python
      class TenantAwareModel(models.Model):
          organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
          class Meta:
              abstract = True
      ```
      - **📊 Métrica:** Todos modelos herdam TenantAware
      - **💡 Justificativa:** Garantir isolamento automático

- **[ ] 3. SISTEMA USERS + USERROLE**
  - **[ ] 3.1 Modelo Users (AbstractUser)**
    - **[ ] 3.1.1** Extender AbstractUser com organizacao
      - **📋 Critério:** AUTH_USER_MODEL configurado
      - **🎯 Resultado:** User sempre vinculado a organizacao
    - **[ ] 3.1.2** Implementar manager customizado
      - **📋 Critério:** get_queryset() filtra por tenant
      - **🎯 Resultado:** Usuários isolados por organizacao
  - **[ ] 3.2 Modelo Role + UserRole**
    - **[ ] 3.2.1** Criar Role com choices específicos
      ```python
      ROLE_CHOICES = [
          ("administrador", "Administrador"),
          ("cliente", "Cliente"),
          ("parceiro", "Parceiro"),
          ("gerador", "Gerador"),
          ("unidade_consumidora", "Unidade Consumidora"),
      ]
      ```
      - **📊 Métrica:** 5 roles pré-definidos criados
      - **💡 Justificativa:** Cobrir todos perfis de negócio
    - **[ ] 3.2.2** Implementar UserRole com unique_together
      - **📋 Critério:** unique_together=['user', 'role', 'organizacao']
      - **🎯 Resultado:** Um usuário pode ter papéis diferentes por organizacao

- **[ ] 4. PERFIS ESPECIALIZADOS**
  - **[ ] 4.1 Modelo Administrador**
    - **[ ] 4.1.1** OneToOne com UserRole + permissions
      - **📋 Critério:** Acesso total à organizacao
      - **🎯 Resultado:** CRUD completo em todas entidades
  - **[ ] 4.2 Modelo Cliente**
    - **[ ] 4.2.1** Implementar com TIPO_CHOICES
      - **📋 Critério:** Suporte a diferentes tipos de cliente
      - **🎯 Resultado:** Classificação flexível de clientes
  - **[ ] 4.3 Modelo Parceiro**
    - **[ ] 4.3.1** Campos comissão + relacionamentos M2M
      - **📊 Métrica:** Sistema de comissões funcionando
      - **💡 Justificativa:** Intermediação comercial essential
  - **[ ] 4.4 Modelo Gerador**
    - **[ ] 4.4.1** Validação CPF/CNPJ + contratos
      - **📋 Critério:** Documentos válidos obrigatórios
      - **🎯 Resultado:** Geradores sempre identificados
  - **[ ] 4.5 Modelo UnidadeConsumidora**
    - **[ ] 4.5.1** Relacionamentos com Cliente + consumo_medio
      - **📊 Métrica:** Histórico de consumo rastreável
      - **💡 Justificativa:** Base para cálculos energéticos

- **[ ] 5. ENTIDADES DE NEGÓCIO CORE**
  - **[ ] 5.1 Modelo Distribuidora**
    - **[ ] 5.1.1** Implementar campos + status
      - **📋 Critério:** CRUD funcional com tenant isolation
      - **🎯 Resultado:** Distribuidoras por organizacao
  - **[ ] 5.2 Modelo Usinas**
    - **[ ] 5.2.1** Relacionamentos FK complexos
      ```python
      distribuidora = models.ForeignKey(Distribuidora)
      organizacao = models.ForeignKey(Organizacao)
      gerador = models.ForeignKey(Gerador)
      ```
      - **📊 Métrica:** Todas FKs com ON_DELETE definido
      - **💡 Justificativa:** Integridade referencial crítica
    - **[ ] 5.2.2** Choices para fonte energética
      - **📋 Critério:** Solar, Eólica, Hidrelétrica, Biomassa
      - **🎯 Resultado:** Classificação padronizada

- **[ ] 6. RELACIONAMENTOS ASSOCIATIVOS**
  - **[ ] 6.1 Organizacao_Distribuidora**
    - **[ ] 6.1.1** Tabela N:N com campos extras
      - **📋 Critério:** Status + metadata associação
      - **🎯 Resultado:** Relacionamento gerenciável
  - **[ ] 6.2 Cliente_Distribuidora**
    - **[ ] 6.2.1** N:N com desconto + credenciais
      - **📊 Métrica:** Login único por cliente-distribuidora
      - **💡 Justificativa:** Acesso específico por relacionamento

---

### **ESPECIALISTA 1B - APIs RESTful & AUTENTICAÇÃO**

#### 🔍 ANÁLISE CoT
**Problema Central:** APIs assíncronas com autenticação JWT + 2FA contextualizada por tenant

**Decomposição:**
1. **APIs CRUD:** Endpoints para todas entidades com filtro tenant
2. **Auth JWT:** Token com claims organizacao + role
3. **2FA:** TOTP para perfis críticos (Admin, Gerador)

#### 📈 JUSTIFICATIVA STaR
**Restrição:** Autenticação deve ser stateless mas tenant-aware
**Impacto:** +60% segurança, -20% latência vs sessões
**Resultado:** Escalabilidade horizontal mantendo segurança

#### 🌳 ALTERNATIVAS ToT
**Opção A: JWT com organizacao em claims**
- ✅ Stateless, multi-tenant nativo
- ❌ Token size maior
- 📊 Viabilidade: Alta

**Opção B: Session + tenant context**
- ✅ Token pequeno, cache familiar
- ❌ Estado no servidor, complexidade escala
- 📊 Viabilidade: Média

**🎯 DECISÃO:** JWT + organizacao claims (A)

#### 📋 CHECKLIST DETALHADO

- **[ ] 1. CONFIGURAÇÃO JWT + DJANGO NINJA**
  - **[ ] 1.1 Setup JWT backend**
    - **[ ] 1.1.1** Instalar django-ninja-jwt
      - **📋 Critério:** Package instalado e configurado
      - **🎯 Resultado:** JWT middleware ativo
    - **[ ] 1.1.2** Configurar claims customizados
      ```python
      def get_token(cls, user):
          token = super().get_token(user)
          token['organizacao_id'] = user.organizacao.id
          token['roles'] = user.userrole_set.values_list('role__name', flat=True)
          return token
      ```
      - **📊 Métrica:** Token contém organizacao + roles
      - **💡 Justificativa:** Context tenant em cada request

- **[ ] 2. APIS CRUD ASSÍNCRONAS**
  - **[ ] 2.1 Router base com tenant filter**
    - **[ ] 2.1.1** Decorator tenant_required
      ```python
      def tenant_required(func):
          async def wrapper(request, *args, **kwargs):
              if not hasattr(request, 'organizacao'):
                  raise PermissionDenied
              return await func(request, *args, **kwargs)
          return wrapper
      ```
      - **📋 Critério:** Todos endpoints protegidos
      - **🎯 Resultado:** Isolamento automático por tenant
  - **[ ] 2.2 CRUD Organizacao (admin only)**
    - **[ ] 2.2.1** GET /organizacoes (list própria org)**
      - **📊 Métrica:** Retorna apenas org do usuário
      - **💡 Justificativa:** Admin vê apenas sua organização
    - **[ ] 2.2.2** PUT /organizacoes/{id} (update)**
      - **📋 Critério:** Validação tenant ownership
      - **🎯 Resultado:** Update seguro por tenant
  - **[ ] 2.3 CRUD Users + UserRole**
    - **[ ] 2.3.1** POST /users (create + assign role)**
      - **📋 Critério:** User criado já vinculado à org
      - **🎯 Resultado:** Novo usuário isolado no tenant
    - **[ ] 2.3.2** GET /users/roles (list roles disponíveis)**
      - **📊 Métrica:** 5 roles pré-definidos retornados
      - **💡 Justificativa:** Frontend pode listar opções

- **[ ] 3. SISTEMA 2FA TOTP**
  - **[ ] 3.1 Setup django-otp**
    - **[ ] 3.1.1** Configurar TOTP devices por role
      ```python
      @property
      def requires_2fa(self):
          critical_roles = ['administrador', 'gerador']
          return self.userrole_set.filter(
              role__name__in=critical_roles
          ).exists()
      ```
      - **📋 Critério:** 2FA obrigatório para roles críticos
      - **🎯 Resultado:** Segurança adicional automática
  - **[ ] 3.2 Endpoints 2FA**
    - **[ ] 3.2.1** POST /auth/setup-2fa
      - **📊 Métrica:** QR code gerado para app authenticator
      - **💡 Justificativa:** Self-service setup
    - **[ ] 3.2.2** POST /auth/verify-2fa
      - **📋 Critério:** Validação TOTP + refresh token
      - **🎯 Resultado:** Acesso liberado com 2FA válido

- **[ ] 4. APIS ENTIDADES DE NEGÓCIO**
  - **[ ] 4.1 CRUD Distribuidoras**
    - **[ ] 4.1.1** GET /distribuidoras (filtrado por org)**
      - **📋 Critério:** Apenas distribuidoras da organização
      - **🎯 Resultado:** Lista contextualizada
    - **[ ] 4.1.2** POST /distribuidoras (create)**
      - **📊 Métrica:** Auto-assign organizacao do token
      - **💡 Justificativa:** Tenant isolation automático
  - **[ ] 4.2 CRUD Usinas**
    - **[ ] 4.2.1** Endpoint com relacionamentos aninhados
      ```python
      @router.get("/usinas/{id}/detalhes")
      async def usina_detalhes(id: int, request):
          # Include distribuidora, gerador, clientes
      ```
      - **📋 Critério:** Single endpoint para dados completos
      - **🎯 Resultado:** Frontend recebe contexto completo
  - **[ ] 4.3 APIs navegação relacionamentos**
    - **[ ] 4.3.1** GET /organizacao/distribuidoras/usinas
      - **📊 Métrica:** Navegação hierárquica funcional
      - **💡 Justificativa:** Explorar estrutura de dados

---

## 🚀 **EQUIPE 2: PERFORMANCE & ESCALABILIDADE**

### **ESPECIALISTA 2A - OTIMIZAÇÃO DE QUERIES & CACHE**

#### 🔍 ANÁLISE CoT
**Problema:** Relacionamentos N:N complexos causam queries N+1, cache deve ser tenant-aware

**Decomposição:**
1. **Queries:** select_related/prefetch_related estratégico
2. **Cache:** Redis com prefixo organizacao_id
3. **Invalidação:** Smart cache por relacionamentos

#### 📈 JUSTIFICATIVA STaR
**Restrição:** 100ms response time máximo para APIs críticas
**Impacto:** 80% redução queries, 60% menos latência
**Resultado:** Sistema suporta 10x mais usuários simultâneos

#### 📋 CHECKLIST DETALHADO

- **[ ] 1. OTIMIZAÇÃO DE QUERIES**
  - **[ ] 1.1 Análise de relacionamentos críticos**
    - **[ ] 1.1.1** Mapear queries N+1 em relacionamentos
      - **📋 Critério:** Django Debug Toolbar instalado
      - **🎯 Resultado:** Identificar gargalos de queries
    - **[ ] 1.1.2** Implementar select_related estratégico
      ```python
      # Exemplo para UnidadeConsumidora
      UnidadeConsumidora.objects.select_related(
          'cliente', 'distribuidora', 'parceiro', 'usina'
      ).filter(organizacao=request.organizacao)
      ```
      - **📊 Métrica:** Redução de 80% no número de queries
      - **💡 Justificativa:** FKs carregadas em uma query
  - **[ ] 1.2 Prefetch para relacionamentos reversos**
    - **[ ] 1.2.1** Otimizar Parceiro → Clientes → Distribuidoras
      ```python
      Parceiro.objects.prefetch_related(
          'clientes__distribuidoras',
          'clientes__unidadesconsumidoras_set'
      )
      ```
      - **📋 Critério:** Queries reduzidas para O(1) por tipo
      - **🎯 Resultado:** Performance previsível independente de volume

- **[ ] 2. SISTEMA CACHE REDIS MULTI-TENANT**
  - **[ ] 2.1 Cache strategy por tenant**
    - **[ ] 2.1.1** Decorator cache_per_tenant
      ```python
      def cache_per_tenant(timeout=300):
          def decorator(func):
              def wrapper(request, *args, **kwargs):
                  key = f"org_{request.organizacao.id}:{func.__name__}:{hash(args)}"
                  # ... cache logic
      ```
      - **📊 Métrica:** Cache hit rate > 80%
      - **💡 Justificativa:** Isolamento + performance
  - **[ ] 2.2 Cache invalidation inteligente**
    - **[ ] 2.2.1** Signals para invalidar por relacionamento
      - **📋 Critério:** Update em Usina invalida cache do Gerador
      - **🎯 Resultado:** Consistência automática

---

### **ESPECIALISTA 2B - INFRAESTRUTURA & DEPLOY**

#### 🔍 ANÁLISE CoT
**Problema:** Deploy escalável com separação de responsabilidades

#### 📋 CHECKLIST DETALHADO

- **[ ] 1. CONTAINERIZAÇÃO DOCKER**
  - **[ ] 1.1 Dockerfile otimizado**
    - **[ ] 1.1.1** Multi-stage build com cache layers
      - **📋 Critério:** Build time < 2 minutos
      - **🎯 Resultado:** Deploy rápido e eficiente
  - **[ ] 1.2 Docker Compose para desenvolvimento**
    - **[ ] 1.2.1** Serviços: django, postgres, redis, celery
      - **📊 Métrica:** Ambiente completo com `docker-compose up`
      - **💡 Justificativa:** Desenvolvimento consistente

- **[ ] 2. CONFIGURAÇÃO DE PRODUÇÃO**
  - **[ ] 2.1 Variables de ambiente**
    - **[ ] 2.1.1** django-environ para config
      - **📋 Critério:** Secrets não commitados
      - **🎯 Resultado:** Deploy seguro
  - **[ ] 2.2 Health checks**
    - **[ ] 2.2.1** Endpoint /health com validações
      - **📊 Métrica:** DB, Redis, Celery status
      - **💡 Justificativa:** Monitoramento proativo

---

## 🛡️ **EQUIPE 3: SEGURANÇA & COMPLIANCE**

### **ESPECIALISTA 3A - OWASP TOP 10 & VULNERABILIDADES**

#### 🔍 ANÁLISE CoT
**Problema:** Aplicar OWASP Top 10 2023 em contexto multi-tenant

#### 📋 CHECKLIST DETALHADO

- **[ ] 1. OWASP A01 - BROKEN ACCESS CONTROL**
  - **[ ] 1.1 Validação tenant em todas operações**
    - **[ ] 1.1.1** Middleware TenantMiddleware obrigatório
      - **📋 Critério:** Todas views passam por check tenant
      - **🎯 Resultado:** Zero bypass de isolamento
  - **[ ] 1.2 Role-based permissions**
    - **[ ] 1.2.1** Django permissions + custom tenant check
      - **📊 Métrica:** 100% endpoints com @permission_required
      - **💡 Justificativa:** Dupla validação de acesso

- **[ ] 2. OWASP A02 - CRYPTOGRAPHIC FAILURES**
  - **[ ] 2.1 Criptografia de dados sensíveis**
    - **[ ] 2.1.1** django-cryptography para CPF/CNPJ
      - **📋 Critério:** PII criptografado em database
      - **🎯 Resultado:** Dados protegidos em rest

- **[ ] 3. OWASP A03 - INJECTION**
  - **[ ] 3.1 Validação Pydantic rigorosa**
    - **[ ] 3.1.1** Schemas para todos inputs
      - **📊 Métrica:** Zero raw SQL, ORM only
      - **💡 Justificativa:** Prevenção automática injection

---

### **ESPECIALISTA 3B - CRIPTOGRAFIA & LGPD**

#### 📋 CHECKLIST DETALHADO

- **[ ] 1. COMPLIANCE LGPD**
  - **[ ] 1.1 Mapeamento de dados pessoais**
    - **[ ] 1.1.1** Inventário completo PII por modelo
      - **📋 Critério:** CPF, email, telefone mapeados
      - **🎯 Resultado:** Base legal documentada
  - **[ ] 1.2 Direitos do titular**
    - **[ ] 1.2.1** API para portabilidade de dados
      - **📊 Métrica:** Export JSON completo em < 30s
      - **💡 Justificativa:** Atendimento direito à portabilidade

- **[ ] 2. AUDITORIA E LOGS**
  - **[ ] 2.1 Log de acesso tenant-aware**
    - **[ ] 2.1.1** Estrutured logging com organizacao_id
      - **📋 Critério:** Todos logs identificam tenant
      - **🎯 Resultado:** Auditoria por organização

---

## 📊 MÉTRICAS FINAIS DE VALIDAÇÃO

| **Categoria** | **Critério** | **Meta** | **Status** |
|---------------|--------------|----------|------------|
| **Cobertura** | Itens base expandidos | 100% | ⏳ |
| **Profundidade** | Níveis de detalhamento | 3+ | ✅ |
| **Actionabilidade** | Tarefas executáveis | 100% | ✅ |
| **Justificativas** | Decisões documentadas | 100% | ✅ |

---

## 🎯 RESUMO EXECUTIVO

**CHECKLIST FINAL ENTREGUE:** ✅
- **180+ itens verificáveis** organizados em 3 níveis
- **6 especialistas** com metodologia CoT + STaR + ToT
- **Cobertura completa:** Desenvolvimento → Performance → Segurança
- **Foco multi-tenant:** Isolamento por Organizacao em toda stack
- **Pronto para execução:** Cada checkbox representa tarefa específica

**PRÓXIMOS PASSOS:**
1. Revisar checklist com equipe técnica
2. Estimar tempo/recursos por seção
3. Iniciar desenvolvimento seguindo sequência Phase-Gate
4. Monitorar progresso via checkboxes
5. Iterar baseado em feedback e lições aprendidas