from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from .models import User, Service, Product, Appointment, Payment, Expense, Goal, WorkingHour, TimeBlock, Notification, ProductSale
    WorkingHourSerializer, TimeBlockSerializer, ProductSaleSerializer
)

import csv
from django.http import HttpResponse

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    def get_permissions(self):
        if self.action in ['me', 'available_times']:
            return [permissions.IsAuthenticated()]
        # Allow any for barber list and available_times in portal
        if self.action == 'available_times':
            return [permissions.AllowAny()]
        if self.action == 'list' and self.request.query_params.get('role') == 'barber':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def available_times(self, request, pk=None):
        barber = self.get_object()
        date_str = request.query_params.get('date') # YYYY-MM-DD
        if not date_str:
            return Response({'error': 'Parâmetro "date" é obrigatório.'}, status=400)
            
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Formato de data inválido. Use YYYY-MM-DD.'}, status=400)

        day_of_week = date.weekday()
        
        # 1. Get working hours for the day
        working_hour = WorkingHour.objects.filter(barber=barber, day_of_week=day_of_week, is_active=True).first()
        if not working_hour:
            return Response([]) # Not working this day
            
        # 2. Generate slots (every 30 mins)
        slots = []
        curr_time = datetime.combine(date, working_hour.start_time)
        end_time = datetime.combine(date, working_hour.end_time)
        
        while curr_time < end_time:
            slots.append(curr_time)
            curr_time += timedelta(minutes=30)
            
        # 3. Filter out existing appointments
        appointments = Appointment.objects.filter(
            barber=barber, 
            date_time__date=date
        ).exclude(status='cancelled')
        
        # 4. Filter out time blocks
        blocks = TimeBlock.objects.filter(
            barber=barber,
            start_time__date=date
        )
        
        available_slots = []
        for slot in slots:
            is_busy = False
            for app in appointments:
                app_start = app.date_time
                duration = app.service.duration_minutes if app.service else 30
                app_end = app_start + timedelta(minutes=duration)
                if slot >= app_start and slot < app_end:
                    is_busy = True
                    break
            if is_busy: continue
            for block in blocks:
                if slot >= block.start_time and slot < block.end_time:
                    is_busy = True
                    break
            if not is_busy:
                available_slots.append(slot.strftime('%H:%M'))
                
        return Response(available_slots)

    @action(detail=False, methods=['get'])
    def birthdays(self, request):
        today = timezone.now().date()
        # Today's birthdays
        today_bdays = User.objects.filter(
            role='client',
            birth_date__month=today.month,
            birth_date__day=today.day
        )
        
        # Week's birthdays
        next_week = today + timedelta(days=7)
        # Handle year rollover if needed, but for simplicity:
        week_bdays = User.objects.filter(
            role='client',
            birth_date__isnull=False
        )
        # Filter in python for complex date range across months
        upcoming = []
        for user in week_bdays:
            # Check if bday is in next 7 days
            bday_this_year = user.birth_date.replace(year=today.year)
            if today <= bday_this_year <= next_week:
                upcoming.append(user)
        
        return Response({
            'today': UserSerializer(today_bdays, many=True).data,
            'week': UserSerializer(upcoming, many=True).data
        })

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'barber', 'client', 'date_time']
    ordering_fields = ['date_time']

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="agendamentos.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Cliente', 'Barbeiro', 'Serviço', 'Data/Hora', 'Status', 'Preço Total'])
        
        appointments = self.get_queryset()
        for app in appointments:
            writer.writerow([
                app.id,
                app.client.get_full_name() if app.client else 'N/A',
                app.barber.get_full_name() if app.barber else 'N/A',
                app.service.name if app.service else 'N/A',
                app.date_time.strftime('%Y-%m-%d %H:%M'),
                app.get_status_display(),
                app.total_price
            ])
            
        return response

    def get_permissions(self):
        if self.action in ['create', 'public_booking']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def public_booking(self, request):
        name = request.data.get('name')
        phone = request.data.get('phone')
        service_id = request.data.get('service_id')
        barber_id = request.data.get('barber_id')
        date_time = request.data.get('date_time')
        
        # 1. Find or create client
        # In a real app, you'd use email or phone as unique ID. Let's use phone.
        client, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'username': f"user_{phone}",
                'first_name': name,
                'role': 'client'
            }
        )
        
        # 2. Create appointment
        service = Service.objects.get(id=service_id)
        barber = User.objects.get(id=barber_id)
        
        appointment = Appointment.objects.create(
            client=client,
            barber=barber,
            service=service,
            date_time=date_time,
            total_price=service.price,
            status='pending'
        )
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete_with_payments(self, request, pk=None):
        appointment = self.get_object()
        payments_data = request.data.get('payments', [])
        
        if not payments_data:
            return Response({'error': 'Nenhum pagamento informado.'}, status=400)
            
        total_paid = sum(float(p['amount']) for p in payments_data)
        
        # Validation: sum of payments must equal total price
        if abs(total_paid - float(appointment.total_price)) > 0.01:
            return Response({
                'error': f'A soma dos pagamentos (R$ {total_paid:.2f}) não bate com o valor total (R$ {appointment.total_price:.2f}).'
            }, status=400)
            
        # Create payments
        for p_data in payments_data:
            Payment.objects.create(
                appointment=appointment,
                method=p_data['method'],
                amount=p_data['amount']
            )
            
        # Update status
        appointment.status = 'completed'
        appointment.save()
        
        return Response({'status': 'Agendamento concluído com sucesso!'})

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        
        # 1. Total appointments today
        total_appointments = Appointment.objects.filter(date_time__date=today).count()
        
        # 2. Predicted revenue today (all confirmed/pending appointments)
        predicted_revenue = Appointment.objects.filter(
            date_time__date=today
        ).exclude(status='cancelled').aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        # 3. Actual revenue today (completed appointments)
        completed_revenue = Appointment.objects.filter(
            date_time__date=today,
            status='completed'
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        # 4. Daily goal
        goal = Goal.objects.filter(period='daily', start_date__lte=today).order_by('-start_date').first()
        daily_goal = goal.target_amount if goal else 0
        
        return Response({
            'total_appointments': total_appointments,
            'predicted_revenue': float(predicted_revenue),
            'completed_revenue': float(completed_revenue),
            'daily_goal': float(daily_goal),
            'progress_percentage': (float(completed_revenue) / float(daily_goal) * 100) if daily_goal > 0 else 0
        })

class WorkingHourViewSet(viewsets.ModelViewSet):
    queryset = WorkingHour.objects.all()
    serializer_class = WorkingHourSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['barber']

class TimeBlockViewSet(viewsets.ModelViewSet):
    queryset = TimeBlock.objects.all()
    serializer_class = TimeBlockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['barber']

class ProductSaleViewSet(viewsets.ModelViewSet):
    queryset = ProductSale.objects.all()
    serializer_class = ProductSaleSerializer
    permission_classes = [permissions.IsAuthenticated]
