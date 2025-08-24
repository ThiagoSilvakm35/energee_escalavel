# 🌟 ENERGEE ESCALÁVEL - Sistema Django Ninja Multi-Tenant

## 📋 Visão Geral
Sistema Django Ninja assíncrono para gestão de faturas de energia elétrica de múltiplas organizações, desenvolvido com foco em escalabilidade, segurança e performance.

## 🏗️ Arquitetura Multi-Tenant
- **Isolamento por Distribuidora**: Cada tenant representa uma distribuidora de energia
- **Django Ninja**: APIs RESTful assíncronas com async/await nativo  
- **PostgreSQL**: Banco principal com otimizações para multi-tenancy
- **Redis**: Cache multi-camadas e sessões
- **Celery**: Processamento assíncrono de faturas e relatórios

## 🚀 Stack Tecnológica
- **Backend**: Django 4.2+, Django Ninja, Django Channels
- **Banco de Dados**: PostgreSQL 15+
- **Cache**: Redis 7+
- **Queue**: Celery com Redis broker
- **Container**: Docker Compose
- **Autenticação**: JWT + TOTP/SMS (2FA)

## 📊 Entidades Principais
- **Distribuidora**: Tenants principais do sistema
- **Organização**: Empresas clientes de cada distribuidora
- **Usinas**: Unidades geradoras de energia
- **Roles**: Sistema flexível de papéis (admin, cliente, parceiro, gerador, UC)
- **Clientes/Parceiros/UCs**: Perfis especializados por tipo de usuário

## 🔧 Configuração Rápida
```bash
# Clone e configure
git clone <repo>
cd energee_escalavel

# Inicie com Docker
docker-compose up -d

# Execute migrações
docker-compose exec web python manage.py migrate

# Crie superuser
docker-compose exec web python manage.py createsuperuser
```

## 📚 Documentação Técnica
- [Arquitetura Multi-Tenant](docs/architecture.md)
- [APIs e Schemas](docs/api.md)
- [Segurança e Compliance](docs/security.md)
- [Performance e Cache](docs/performance.md)

## 🏆 Metas de Performance
- **Latência**: < 200ms para 95% das requisições
- **Throughput**: 1000+ req/s por instância  
- **Cache Hit Rate**: > 80% para consultas frequentes
- **Uptime**: 99.9% disponibilidade

## 🔒 Segurança
- OWASP Top 10 2023 completamente endereçado
- Conformidade LGPD
- Auditoria em tempo real
- Rate limiting diferenciado
- Criptografia end-to-end para dados sensíveis