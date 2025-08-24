"""
Modelos para Usinas - Unidades geradoras de energia
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TenantModel


class Usinas(TenantModel):
    """
    Usinas - Unidades geradoras de energia
    """
    FONTE_CHOICES = [
        ('solar', 'Solar Fotovoltaica'),
        ('eolica', 'Eólica'),
        ('hidrica', 'Hídrica'),
        ('termica', 'Térmica'),
        ('biomassa', 'Biomassa'),
        ('nuclear', 'Nuclear'),
        ('hibrida', 'Híbrida'),
    ]
    
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('manutencao', 'Em Manutenção'),
        ('suspenso', 'Suspenso'),
        ('descomissionado', 'Descomissionado'),
    ]
    
    # Dados principais
    nome = models.CharField('Nome da Usina', max_length=200)
    uc = models.CharField('Unidade Consumidora', max_length=20, unique=True)
    
    # Características técnicas
    fonte = models.CharField('Fonte de Energia', max_length=20, choices=FONTE_CHOICES)
    potencia = models.DecimalField(
        'Potência Instalada (kW)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    geracao_media = models.DecimalField(
        'Geração Média Mensal (kWh)',
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Relacionamentos
    cliente = models.ForeignKey(
        'organizacoes.Cliente',
        on_delete=models.CASCADE,
        related_name='usinas_cliente',
        verbose_name='Cliente Proprietário'
    )
    gerador = models.ForeignKey(
        'authentication.UserRole',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role__name': 'gerador'},
        related_name='usinas_gerador',
        verbose_name='Gerador Responsável'
    )
    organizacao = models.ForeignKey(
        'organizacoes.Organizacao',
        on_delete=models.CASCADE,
        related_name='usinas',
        verbose_name='Organização'
    )
    
    # Dados contratuais
    data_contrato = models.DateField('Data do Contrato')
    vencimento_contrato = models.DateField('Vencimento do Contrato')
    
    # Configurações financeiras
    imposto = models.DecimalField(
        'Percentual de Imposto (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    desconto_gestao = models.DecimalField(
        'Desconto de Gestão (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Modalidade tarifária
    ponta = models.BooleanField(
        'Horário de Ponta',
        default=False,
        help_text='Indica se a usina opera em horário de ponta'
    )
    
    # Status e controle
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='ativo')
    
    # Consumidores exclusivos
    consumidores_exclusivos = models.ManyToManyField(
        'organizacoes.UnidadeConsumidora',
        blank=True,
        related_name='usinas_exclusivas',
        verbose_name='Consumidores Exclusivos',
        help_text='Unidades consumidoras que têm acesso exclusivo a esta usina'
    )
    
    # Dados de localização
    endereco = models.CharField('Endereço', max_length=300, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    estado = models.CharField('Estado', max_length=2, blank=True)
    coordenadas_latitude = models.DecimalField(
        'Latitude',
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True
    )
    coordenadas_longitude = models.DecimalField(
        'Longitude',
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True
    )
    
    # Dados de produção
    producao_total_kwh = models.DecimalField(
        'Produção Total (kWh)',
        max_digits=15,
        decimal_places=2,
        default=0
    )
    ultima_medicao = models.DateTimeField('Última Medição', null=True, blank=True)
    fator_capacidade = models.DecimalField(
        'Fator de Capacidade (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Configurações adicionais
    configuracoes = models.JSONField('Configurações Técnicas', default=dict, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    
    class Meta:
        verbose_name = 'Usina'
        verbose_name_plural = 'Usinas'
        ordering = ['nome']
        unique_together = ['distribuidora', 'uc']
    
    def __str__(self):
        return f"{self.nome} ({self.uc})"
    
    @property
    def is_active(self):
        """Verifica se a usina está ativa"""
        return self.status == 'ativo'
    
    @property
    def endereco_completo(self):
        """Retorna endereço formatado"""
        if self.endereco and self.cidade and self.estado:
            return f"{self.endereco}, {self.cidade}/{self.estado}"
        return ""
    
    @property
    def contrato_vencido(self):
        """Verifica se o contrato está vencido"""
        from django.utils import timezone
        return self.vencimento_contrato < timezone.now().date()
    
    @property
    def dias_para_vencimento(self):
        """Calcula dias para vencimento do contrato"""
        from django.utils import timezone
        delta = self.vencimento_contrato - timezone.now().date()
        return delta.days
    
    def calcular_geracao_estimada(self, mes, ano):
        """
        Calcula geração estimada para um mês específico
        """
        # Aqui seria implementada a lógica de cálculo baseada em:
        # - Histórico de geração
        # - Dados meteorológicos
        # - Sazonalidade
        return self.geracao_media
    
    def get_unidades_consumidoras_atendidas(self):
        """
        Retorna todas as unidades consumidoras atendidas por esta usina
        """
        from apps.organizacoes.models import UnidadeConsumidora
        
        # UCs exclusivas
        exclusivas = self.consumidores_exclusivos.all()
        
        # UCs que têm esta usina associada
        associadas = UnidadeConsumidora.objects.filter(
            distribuidora=self.distribuidora,
            usina=self
        ).exclude(
            id__in=exclusivas.values_list('id', flat=True)
        )
        
        return {
            'exclusivas': exclusivas,
            'associadas': associadas,
            'total_count': exclusivas.count() + associadas.count()
        }
    
    def calcular_excedente_disponivel(self):
        """
        Calcula energia excedente disponível para compensação
        """
        ucs_atendidas = self.get_unidades_consumidoras_atendidas()
        total_consumo_ucs = sum([
            uc.consumo_medio for uc in 
            list(ucs_atendidas['exclusivas']) + list(ucs_atendidas['associadas'])
        ])
        
        excedente = self.geracao_media - total_consumo_ucs
        return max(0, excedente)  # Não pode ser negativo


class HistoricoGeracao(TenantModel):
    """
    Histórico de geração das usinas
    """
    usina = models.ForeignKey(
        Usinas,
        on_delete=models.CASCADE,
        related_name='historico_geracao'
    )
    
    # Período da medição
    ano = models.PositiveIntegerField('Ano')
    mes = models.PositiveIntegerField('Mês', validators=[MinValueValidator(1), MaxValueValidator(12)])
    
    # Dados de geração
    energia_gerada_kwh = models.DecimalField(
        'Energia Gerada (kWh)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    energia_consumida_kwh = models.DecimalField(
        'Energia Consumida (kWh)',
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    energia_injetada_kwh = models.DecimalField(
        'Energia Injetada na Rede (kWh)',
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Dados meteorológicos (opcional)
    irradiacao_media = models.DecimalField(
        'Irradiação Média (kWh/m²)',
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True
    )
    temperatura_media = models.DecimalField(
        'Temperatura Média (°C)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Performance
    fator_capacidade_realizado = models.DecimalField(
        'Fator de Capacidade Realizado (%)',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Auditoria
    data_medicao = models.DateTimeField('Data da Medição', auto_now_add=True)
    fonte_dados = models.CharField(
        'Fonte dos Dados',
        max_length=50,
        choices=[
            ('manual', 'Manual'),
            ('automatico', 'Automático'),
            ('estimado', 'Estimado'),
        ],
        default='manual'
    )
    
    class Meta:
        verbose_name = 'Histórico de Geração'
        verbose_name_plural = 'Históricos de Geração'
        unique_together = ['distribuidora', 'usina', 'ano', 'mes']
        ordering = ['-ano', '-mes']
    
    def __str__(self):
        return f"{self.usina.nome} - {self.mes:02d}/{self.ano}"
    
    @property
    def energia_liquida_kwh(self):
        """Calcula energia líquida (gerada - consumida)"""
        return self.energia_gerada_kwh - self.energia_consumida_kwh
    
    @property
    def performance_vs_estimado(self):
        """Calcula performance vs geração estimada"""
        if self.usina.geracao_media > 0:
            return (self.energia_gerada_kwh / self.usina.geracao_media) * 100
        return 0


class ManutencaoUsina(TenantModel):
    """
    Registro de manutenções das usinas
    """
    TIPO_CHOICES = [
        ('preventiva', 'Preventiva'),
        ('corretiva', 'Corretiva'),
        ('preditiva', 'Preditiva'),
        ('emergencial', 'Emergencial'),
    ]
    
    STATUS_CHOICES = [
        ('agendada', 'Agendada'),
        ('em_andamento', 'Em Andamento'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]
    
    usina = models.ForeignKey(
        Usinas,
        on_delete=models.CASCADE,
        related_name='manutencoes'
    )
    
    # Dados da manutenção
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='agendada')
    descricao = models.TextField('Descrição')
    
    # Datas
    data_agendada = models.DateTimeField('Data Agendada')
    data_inicio = models.DateTimeField('Data de Início', null=True, blank=True)
    data_conclusao = models.DateTimeField('Data de Conclusão', null=True, blank=True)
    
    # Responsável
    responsavel = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Responsável'
    )
    empresa_terceirizada = models.CharField('Empresa Terceirizada', max_length=200, blank=True)
    
    # Custos
    custo_estimado = models.DecimalField(
        'Custo Estimado',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    custo_real = models.DecimalField(
        'Custo Real',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Observações
    observacoes = models.TextField('Observações', blank=True)
    relatorio_conclusao = models.TextField('Relatório de Conclusão', blank=True)
    
    class Meta:
        verbose_name = 'Manutenção de Usina'
        verbose_name_plural = 'Manutenções de Usinas'
        ordering = ['-data_agendada']
    
    def __str__(self):
        return f"{self.usina.nome} - {self.get_tipo_display()} - {self.data_agendada.strftime('%d/%m/%Y')}"
    
    @property
    def duracao_estimada(self):
        """Calcula duração estimada em horas"""
        if self.data_inicio and self.data_conclusao:
            delta = self.data_conclusao - self.data_inicio
            return delta.total_seconds() / 3600
        return None
    
    @property
    def is_atrasada(self):
        """Verifica se a manutenção está atrasada"""
        from django.utils import timezone
        return (
            self.status in ['agendada', 'em_andamento'] and
            self.data_agendada < timezone.now()
        )