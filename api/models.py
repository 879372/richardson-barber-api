from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('barber', 'Barber'),
        ('receptionist', 'Receptionist'),
        ('client', 'Client'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    # additional fields can go here

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name else self.username

class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, null=True)
    stock_quantity = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    min_stock_alert = models.IntegerField(default=5)

    def __str__(self):
        return self.name

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Aguardando confirmação'),
        ('confirmed', 'Confirmado'),
        ('completed', 'Concluído'),
        ('cancelled', 'Cancelado'),
        ('no_show', 'Não compareceu'),
    )
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments_as_client')
    barber = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='appointments_as_barber')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    date_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client} - {self.service} at {self.date_time}"

class Payment(models.Model):
    METHOD_CHOICES = (
        ('pix', 'PIX'),
        ('cash', 'Espécie'),
        ('credit', 'Cartão de Crédito'),
        ('debit', 'Cartão de Débito'),
        ('transfer', 'Transferência'),
    )
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.method} - {self.amount}"

class Expense(models.Model):
    CATEGORY_CHOICES = (
        ('fixed', 'Fixa'),
        ('variable', 'Variável'),
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='variable')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - {self.amount}"
