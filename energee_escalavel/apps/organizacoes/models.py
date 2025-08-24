"""
Modelos para Organizações - Empresas clientes das distribuidoras
"""
from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from apps.core.models import TenantModel


class Organizacao(TenantModel):
    """
    Organizações - Empresas clientes das distribuidoras
    """
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('suspenso', 'Suspenso'),
        ('inadimplente', 'Inadimplente'),
    ]
    
    # Dados principais
    nome = models.CharField('Nome', max_length=200)
    razao_social = models.CharField('Razão Social', max_length=200)
    nome_fantasia = models.CharField('Nome Fantasia', max_length=200, blank=True)
    
    # Documentos
    cnpj = models.CharField(
        'CNPJ',
        max_length=18,
        validators=[RegexValidator(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$')]
    )
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=20, blank=True)
    inscricao_municipal = models.CharField('Inscrição Municipal', max_length=20, blank=True)
    
    # Endereço
    endereco = models.CharField('Endereço', max_length=300)
    numero = models.CharField('Número', max_length=10)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100)
    cidade = models.CharField('Cidade', max_length=100)
    estado = models.CharField('Estado', max_length=2)
    cep = models.CharField(
        'CEP',
        max_length=10,
        validators=[RegexValidator(r'^\d{5}-?\d{3}$')]
    )
    
    # Contato
    telefone = models.CharField(
        'Telefone',
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    email = models.EmailField('Email', validators=[EmailValidator()])
    website = models.URLField('Website', blank=True)
    
    # Status e configurações
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='ativo')
    logo = models.ImageField('Logo', upload_to='organizacoes/logos/', blank=True, null=True)
    configuracoes = models.JSONField('Configurações', default=dict, blank=True)
    
    # Dados comerciais
    limite_credito = models.DecimalField('Limite de Crédito', max_digits=15, decimal_places=2, default=0)
    desconto_percentual = models.DecimalField('Desconto (%)', max_digits=5, decimal_places=2, default=0)
    dia_vencimento = models.PositiveIntegerField('Dia de Vencimento', default=10)
    
    # Auditoria e controle
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_ultima_fatura = models.DateTimeField('Data da Última Fatura', null=True, blank=True)
    valor_total_faturas = models.DecimalField('Valor Total de Faturas', max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = 'Organização'
        verbose_name_plural = 'Organizações'
        ordering = ['nome']
        unique_together = ['distribuidora', 'cnpj']
    
    def __str__(self):
        return self.nome
    
    @property
    def endereco_completo(self):
        """Retorna endereço formatado"""
        endereco = f"{self.endereco}, {self.numero}"
        if self.complemento:
            endereco += f", {self.complemento}"
        endereco += f" - {self.bairro}, {self.cidade}/{self.estado} - CEP: {self.cep}"
        return endereco
    
    @property
    def is_active(self):
        """Verifica se a organização está ativa"""
        return self.status == 'ativo'
    
    @property
    def saldo_credito_disponivel(self):
        """Calcula saldo de crédito disponível"""
        # Aqui seria calculado com base nas faturas pendentes
        return self.limite_credito - self.valor_total_faturas


class Cliente(TenantModel):
    """
    Perfil de Cliente - associado a uma organização
    """
    TIPO_CHOICES = [
        ('pessoa_fisica', 'Pessoa Física'),
        ('pessoa_juridica', 'Pessoa Jurídica'),
        ('poder_publico', 'Poder Público'),
        ('industria', 'Indústria'),
        ('comercio', 'Comércio'),
        ('rural', 'Rural'),
    ]
    
    # Relacionamento com user role
    user_role = models.OneToOneField(
        'authentication.UserRole',
        on_delete=models.CASCADE,
        limit_choices_to={'role__name': 'cliente'}
    )
    
    # Organização associada
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.CASCADE,
        related_name='clientes',
        verbose_name='Organização'
    )
    
    # Dados específicos do cliente
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    codigo_cliente = models.CharField('Código do Cliente', max_length=20, unique=True)
    
    # Configurações do cliente
    receber_notificacoes = models.BooleanField('Receber Notificações', default=True)
    formato_preferido_relatorio = models.CharField(
        'Formato Preferido Relatório',
        max_length=10,
        choices=[
            ('pdf', 'PDF'),
            ('xlsx', 'Excel'),
            ('csv', 'CSV'),
        ],
        default='pdf'
    )
    
    # Informações de consumo
    consumo_medio_mensal = models.DecimalField(
        'Consumo Médio Mensal (kWh)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    demanda_contratada = models.DecimalField(
        'Demanda Contratada (kW)',
        max_digits=8,
        decimal_places=2,
        default=0
    )
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        unique_together = ['distribuidora', 'codigo_cliente']
    
    def __str__(self):
        return f"{self.organizacao.nome} - {self.get_tipo_display()}"


class Parceiro(TenantModel):
    """
    Perfil de Parceiro - intermediário comercial
    """
    # Relacionamento com user role
    user_role = models.OneToOneField(
        'authentication.UserRole',
        on_delete=models.CASCADE,
        limit_choices_to={'role__name': 'parceiro'}
    )
    
    # Cliente associado
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='parceiros',
        verbose_name='Cliente'
    )
    
    # Configurações comerciais
    percentual_comissao = models.DecimalField(
        'Percentual de Comissão (%)',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    ativo = models.BooleanField('Ativo', default=True)
    
    # Dados do parceiro
    codigo_parceiro = models.CharField('Código do Parceiro', max_length=20, unique=True)
    area_atuacao = models.TextField('Área de Atuação', blank=True)
    
    # Métricas
    total_vendas = models.DecimalField('Total de Vendas', max_digits=15, decimal_places=2, default=0)
    total_comissoes = models.DecimalField('Total de Comissões', max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = 'Parceiro'
        verbose_name_plural = 'Parceiros'
        unique_together = ['distribuidora', 'codigo_parceiro']
    
    def __str__(self):
        return f"Parceiro: {self.user_role.user.get_full_name()}"


class UnidadeConsumidora(TenantModel):
    """
    Unidade Consumidora - ponto de consumo de energia
    """
    CLASSE_CHOICES = [
        ('residencial', 'Residencial'),
        ('comercial', 'Comercial'),
        ('industrial', 'Industrial'),
        ('rural', 'Rural'),
        ('poder_publico', 'Poder Público'),
        ('iluminacao_publica', 'Iluminação Pública'),
        ('servico_publico', 'Serviço Público'),
    ]
    
    SUBGRUPO_CHOICES = [
        ('B1', 'B1 - Residencial'),
        ('B2', 'B2 - Rural'),
        ('B3', 'B3 - Demais Classes'),
        ('B4', 'B4 - Iluminação Pública'),
        ('A1', 'A1 - 230kV ou mais'),
        ('A2', 'A2 - 88kV a 138kV'),
        ('A3', 'A3 - 69kV'),
        ('A3a', 'A3a - 30kV a 44kV'),
        ('A4', 'A4 - 2,3kV a 25kV'),
        ('AS', 'AS - Sistema Subterrâneo'),
    ]
    
    # Relacionamento com user role
    user_role = models.OneToOneField(
        'authentication.UserRole',
        on_delete=models.CASCADE,
        limit_choices_to={'role__name': 'unidade_consumidora'}
    )
    
    # Relacionamentos
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='unidades_consumidoras'
    )
    parceiro = models.ForeignKey(
        Parceiro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unidades_consumidoras'
    )
    
    # Dados da UC
    numero_uc = models.CharField('Número da UC', max_length=20, unique=True)
    nome_unidade = models.CharField('Nome da Unidade', max_length=200)
    classe = models.CharField('Classe', max_length=20, choices=CLASSE_CHOICES)
    subgrupo = models.CharField('Subgrupo', max_length=5, choices=SUBGRUPO_CHOICES)
    
    # Endereço da UC
    endereco = models.CharField('Endereço', max_length=300)
    numero = models.CharField('Número', max_length=10)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100)
    cidade = models.CharField('Cidade', max_length=100)
    estado = models.CharField('Estado', max_length=2)
    cep = models.CharField(
        'CEP',
        max_length=10,
        validators=[RegexValidator(r'^\d{5}-?\d{3}$')]
    )
    
    # Dados técnicos
    consumo_medio = models.DecimalField(
        'Consumo Médio (kWh)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    demanda_contratada = models.DecimalField(
        'Demanda Contratada (kW)',
        max_digits=8,
        decimal_places=2,
        default=0
    )
    
    # Usina associada
    usina = models.ForeignKey(
        'usinas.Usinas',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unidades_consumidoras'
    )
    
    # Desconto aplicado
    percentual_desconto = models.DecimalField(
        'Percentual de Desconto (%)',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Status
    ativa = models.BooleanField('Ativa', default=True)
    data_ligacao = models.DateField('Data de Ligação', null=True, blank=True)
    data_desligamento = models.DateField('Data de Desligamento', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Unidade Consumidora'
        verbose_name_plural = 'Unidades Consumidoras'
        unique_together = ['distribuidora', 'numero_uc']
    
    def __str__(self):
        return f"UC {self.numero_uc} - {self.nome_unidade}"
    
    @property
    def endereco_completo(self):
        """Retorna endereço formatado"""
        endereco = f"{self.endereco}, {self.numero}"
        if self.complemento:
            endereco += f", {self.complemento}"
        endereco += f" - {self.bairro}, {self.cidade}/{self.estado} - CEP: {self.cep}"
        return endereco
    
    @property
    def tem_geracao_associada(self):
        """Verifica se tem usina associada"""
        return self.usina is not None