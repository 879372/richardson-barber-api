from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Sum, Count
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from .models import User, Service, Product, Appointment, Payment, Expense, Goal, WorkingHour, TimeBlock, Notification, ProductSale
from .serializers import (
    UserSerializer, ServiceSerializer, ProductSerializer, 
    AppointmentSerializer, PaymentSerializer, ExpenseSerializer,
    WorkingHourSerializer, TimeBlockSerializer, ProductSaleSerializer, GoalSerializer
)

import csv
from django.http import HttpResponse

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role']
    def get_permissions(self):
        if self.action == 'me':
            return [permissions.IsAuthenticated()]
        if self.action == 'available_times':
            return [permissions.AllowAny()]
        if self.action == 'list' and self.request.query_params.get('role') == 'barber':
            return [permissions.AllowAny()]
        if self.action in ['create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def check_phone(self, request):
        phone = request.query_params.get('phone')
        if not phone:
            return Response({'error': 'Phone is required'}, status=400)
        
        # Normalize phone (remove non-digits)
        import re
        clean_phone = re.sub(r'\D', '', phone)
        
        user = User.objects.filter(phone=clean_phone, role='client').first()
        if user:
            return Response({
                'exists': True,
                'user': UserSerializer(user).data
            })
        return Response({'exists': False})

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register_client(self, request):
        name = request.data.get('name')
        phone = request.data.get('phone')
        birth_date = request.data.get('birth_date')
        
        import re
        clean_phone = re.sub(r'\D', '', phone) if phone else ''
        
        if not clean_phone:
            return Response({'error': 'Telefone é obrigatório'}, status=400)
            
        client = User.objects.filter(phone=clean_phone, role='client').first()
        if not client:
            client = User.objects.create(
                phone=clean_phone,
                username=f"user_{clean_phone}",
                first_name=name,
                birth_date=birth_date,
                role='client'
            )
        else:
            if name: client.first_name = name
            if birth_date: client.birth_date = birth_date
            client.save()
            
        return Response(UserSerializer(client).data)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def available_times(self, request, pk=None):
        barber = self.get_object()
        date_str = request.query_params.get('date') # YYYY-MM-DD
        service_id = request.query_params.get('service_id')
        if not date_str:
            return Response({'error': 'Parâmetro "date" é obrigatório.'}, status=400)
            
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Formato de data inválido. Use YYYY-MM-DD.'}, status=400)

        requested_duration = 30
        if service_id:
            try:
                service = Service.objects.get(id=service_id)
                requested_duration = service.duration_minutes
            except Service.DoesNotExist:
                pass

        day_of_week = date.weekday()
        
        # 1. Get working hours for the day
        working_hour = WorkingHour.objects.filter(barber=barber, day_of_week=day_of_week, is_active=True).first()
        if not working_hour:
            return Response([])
            
        # Use naive datetimes for internal day comparisons to avoid TZ issues
        start_dt = datetime.combine(date, working_hour.start_time)
        end_dt = datetime.combine(date, working_hour.end_time)
        
        break_start = None
        break_end = None
        if working_hour.break_start_time and working_hour.break_end_time:
            break_start = datetime.combine(date, working_hour.break_start_time)
            break_end = datetime.combine(date, working_hour.break_end_time)
        
        # 2. Get appointments and blocks
        appointments = Appointment.objects.filter(
            barber=barber, 
            date_time__date=date
        ).exclude(status='cancelled')
        
        blocks = TimeBlock.objects.filter(
            barber=barber,
            start_time__date=date
        )
        
        # 3. Generate slots
        available_slots = []
        now = timezone.now() # now is aware
        
        # If today, we need an aware reference for the past check
        today = timezone.localtime(now).date()
        
        # Determine search step: 30 mins default, or service duration if > 30
        step_minutes = 30
        if requested_duration > 30:
            step_minutes = requested_duration

        curr_dt = start_dt
        while curr_dt + timedelta(minutes=requested_duration) <= end_dt:
            # Check if in the past
            curr_aware = timezone.make_aware(curr_dt)
            if curr_aware < now:
                curr_dt += timedelta(minutes=step_minutes)
                continue
                
            req_start = curr_dt
            req_end = curr_dt + timedelta(minutes=requested_duration)
            is_busy = False

            # Check lunch break
            if break_start and break_end:
                if req_start < break_end and req_end > break_start:
                    is_busy = True
                    if curr_dt < break_end:
                        curr_dt = break_end
                        continue
            
            # Check appointments
            if not is_busy:
                for app in appointments:
                    # Convert app.date_time to naive for comparison
                    app_start = timezone.localtime(app.date_time).replace(tzinfo=None)
                    app_duration = app.service.duration_minutes if app.service else 30
                    app_end = app_start + timedelta(minutes=app_duration)
                    if req_start < app_end and req_end > app_start:
                        is_busy = True
                        curr_dt = app_end
                        break
            
            # Check manual blocks
            if not is_busy:
                for block in blocks:
                    b_start = timezone.localtime(block.start_time).replace(tzinfo=None)
                    b_end = timezone.localtime(block.end_time).replace(tzinfo=None)
                    if req_start < b_end and req_end > b_start:
                        is_busy = True
                        curr_dt = b_end
                        break
            
            if not is_busy:
                available_slots.append(curr_dt.strftime('%H:%M'))
                curr_dt += timedelta(minutes=step_minutes)
            elif is_busy and not (break_start and curr_dt < break_end):
                # If busy but not by break (already handled by continue), move to next possible slot
                # We use 5 min increment if it was an appointment/block to find the next possible start
                # but the user wants "duration" steps for 40/60?
                # Let's stick to step_minutes for consistency with user request
                curr_dt += timedelta(minutes=step_minutes)
                
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
    filterset_fields = {
        'status': ['exact'],
        'barber': ['exact'],
        'client': ['exact'],
        'date_time': ['exact', 'date', 'gte', 'lte'],
    }
    ordering_fields = ['date_time']

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def public_list(self, request):
        phone = request.query_params.get('phone')
        if not phone:
            return Response({'error': 'Telefone é obrigatório'}, status=400)
        
        import re
        clean_phone = re.sub(r'\D', '', phone)
        
        appointments = Appointment.objects.filter(
            client__phone=clean_phone
        ).order_by('-date_time')
        
        return Response(AppointmentSerializer(appointments, many=True).data)

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
        birth_date = request.data.get('birth_date')
        
        import re
        clean_phone = re.sub(r'\D', '', phone) if phone else ''
        
        service_id = request.data.get('service_id')
        barber_id = request.data.get('barber_id')
        from django.utils.dateparse import parse_datetime
        date_time_str = request.data.get('date_time')
        date_time = parse_datetime(date_time_str) if date_time_str else None
        
        # 1. Find or create client (identifying ONLY by phone)
        client = User.objects.filter(phone=clean_phone, role='client').first()
        created = False
        
        if not client:
            # Create new client if not found
            client = User.objects.create(
                phone=clean_phone,
                username=f"user_{clean_phone}",
                first_name=name,
                birth_date=birth_date,
                role='client'
            )
            created = True
        
        if not created and (name or birth_date):
            if name: client.first_name = name
            if birth_date: client.birth_date = birth_date
            client.save()
        
        notes = request.data.get('notes')
        
        # 2. Create appointment
        service = Service.objects.get(id=service_id)
        barber = User.objects.get(id=barber_id)
        
        appointment = Appointment.objects.create(
            client=client,
            barber=barber,
            service=service,
            date_time=date_time,
            total_price=service.price,
            status='confirmed',
            notes=notes
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
        total_appointments = Appointment.objects.filter(date_time__date=today).exclude(status='cancelled').count()
        completed_appointments = Appointment.objects.filter(date_time__date=today, status='completed').count()
        
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
            'completed_appointments': completed_appointments,
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

class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]

class FinancialSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        month = request.query_params.get('month', timezone.now().month)
        year = request.query_params.get('year', timezone.now().year)
        
        try:
            start_date = timezone.make_aware(datetime(int(year), int(month), 1))
            if int(month) == 12:
                end_date = timezone.make_aware(datetime(int(year) + 1, 1, 1))
            else:
                end_date = timezone.make_aware(datetime(int(year), int(month) + 1, 1))
        except ValueError:
            return Response({'error': 'Mês ou ano inválido'}, status=400)

        expenses = Expense.objects.filter(date__range=[start_date.date(), end_date.date()])
        total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        
        payments = Payment.objects.filter(created_at__range=[start_date, end_date])
        total_revenue = payments.aggregate(Sum('amount'))['amount__sum'] or 0
        
        method_summary = payments.values('method').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ).order_by('-total_amount')

        return Response({
            'total_revenue': float(total_revenue),
            'total_expenses': float(total_expenses),
            'net_profit': float(total_revenue - total_expenses),
            'method_summary': list(method_summary),
            'expenses': ExpenseSerializer(expenses, many=True).data
        })
    permission_classes = [permissions.IsAuthenticated]
