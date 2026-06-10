from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Appeal, Status, AppealHistory, Category
from .forms import AppealForm, AssignForm


def is_admin(user):
    return user.groups.filter(name='Админ').exists() or user.is_superuser


# БАГ ИСПРАВЛЕН: убран @login_required — незарегистрированный пользователь не сможет открыть страницу
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            group, _ = Group.objects.get_or_create(name='Сотрудник')
            user.groups.add(group)
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('appeal_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def appeal_list(request):
    admin = is_admin(request.user)

    # фильтр по роли применяется первым, затем поисковые фильтры
    admin = is_admin(request.user)
    appeals = Appeal.objects.all()

    status_id = request.GET.get('status')
    query = request.GET.get('q')
    overdue_only = request.GET.get('overdue')

    if status_id:
        appeals = appeals.filter(status_id=status_id)
    if query:
        appeals = appeals.filter(full_name__icontains=query)

    appeals = appeals.select_related('category', 'status', 'assigned_to').order_by('-created_at')

    # Фильтр просроченных (в Python, т.к. is_overdue — метод)
    if overdue_only:
        from django.utils import timezone
        appeals = appeals.filter(deadline__lt=timezone.now())

    paginator = Paginator(appeals, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    statuses = Status.objects.all()
    stats = Appeal.objects.values('status__name').annotate(count=Count('id')).order_by('status__name')

    # БАГ ИСПРАВЛЕН: history передаётся в контекст
    history = (AppealHistory.objects
               .select_related('appeal', 'old_status', 'new_status', 'changed_by')
               .order_by('-changed_at')[:20])

    total = Appeal.objects.count()
    overdue_count = sum(1 for a in Appeal.objects.all() if a.is_overdue)

    return render(request, 'appeals/list.html', {
        'appeals': page_obj,
        'statuses': statuses,
        'stats': stats,
        'query': query,
        'history': history,
        'is_admin': admin,
        'total': total,
        'overdue_count': overdue_count,
        'selected_status': status_id,
    })


@login_required
def create_appeal(request):
    admin = is_admin(request.user)
    if request.method == 'POST':
        form = AppealForm(request.POST, is_admin=admin)
        if form.is_valid():
            appeal = form.save(commit=False)
            appeal.assigned_to = request.user
            if not admin:
                appeal.status = Status.objects.first()
            # БАГ ИСПРАВЛЕН: save() вызывается после всех изменений
            appeal.save()
            messages.success(request, 'Обращение успешно создано.')
            return redirect('appeal_list')
    else:
        form = AppealForm(is_admin=admin)
    return render(request, 'appeals/create.html', {'form': form, 'is_admin': admin})


@login_required
def appeal_detail(request, appeal_id):
    appeal = get_object_or_404(Appeal, id=appeal_id)
    admin = is_admin(request.user)


    history = (AppealHistory.objects.filter(appeal=appeal)
               .select_related('old_status', 'new_status', 'changed_by')
               .order_by('-changed_at'))
    statuses = Status.objects.exclude(id=appeal.status.id) if appeal.status else Status.objects.all()
    workers = User.objects.filter(groups__name='Сотрудник') if admin else None

    return render(request, 'appeals/detail.html', {
        'appeal': appeal,
        'history': history,
        'statuses': statuses,
        'is_admin': admin,
        'workers': workers,
    })




@login_required
def change_status(request, appeal_id, status_id):
    appeal = get_object_or_404(Appeal, id=appeal_id)
    new_status = get_object_or_404(Status, id=status_id)
    admin = is_admin(request.user)

    if not admin and appeal.assigned_to != request.user:
        return HttpResponseForbidden("Нет доступа")

    old_status = appeal.status
    appeal.status = new_status
    appeal.save()

    AppealHistory.objects.create(
        appeal=appeal,
        old_status=old_status,
        new_status=new_status,
        changed_by=request.user,
        comment=request.POST.get('comment', '')
    )
    messages.success(request, f'Статус изменён на «{new_status.name}».')
    return redirect('appeal_detail', appeal_id=appeal.id)


@login_required
def assign_appeal(request, appeal_id):
    if not is_admin(request.user):
        return HttpResponseForbidden("Нет доступа")
    appeal = get_object_or_404(Appeal, id=appeal_id)
    worker_id = request.POST.get('worker_id')
    if worker_id:
        worker = get_object_or_404(User, id=worker_id)
        appeal.assigned_to = worker
        appeal.save()
        messages.success(request, f'Обращение назначено на {worker.username}.')
    return redirect('appeal_detail', appeal_id=appeal.id)


@login_required
def delete_appeal(request, appeal_id):
    if not is_admin(request.user):
        return HttpResponseForbidden("Нет доступа")
    appeal = get_object_or_404(Appeal, id=appeal_id)
    if request.method == 'POST':
        appeal.delete()
        messages.success(request, 'Обращение удалено.')
        return redirect('appeal_list')
    return render(request, 'appeals/confirm_delete.html', {'appeal': appeal})


@login_required
def assign_worker(request, appeal_id):
    appeal = get_object_or_404(Appeal, id=appeal_id)
    
    # только админ может назначать
    is_admin = request.user.groups.filter(name='admin').exists()
    if not is_admin:
        return HttpResponseForbidden("Нет доступа")
    
    if request.method == 'POST':
        user_id = request.POST.get('worker_id')
        from django.contrib.auth.models import User
        worker = get_object_or_404(User, id=user_id)
        appeal.assigned_to = worker
        appeal.save()
        return redirect('appeal_list')
    
    # список всех исполнителей (группа worker)
    workers = User.objects.filter(groups__name='worker')
    return render(request, 'appeals/assign.html', {
        'appeal': appeal,
        'workers': workers
    })

@login_required
def export_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Обращения'

    # Заголовки
    headers = ['№', 'ФИО', 'ИИН', 'Телефон', 'Категория', 'Статус', 'Исполнитель', 'Дата создания', 'Срок исполнения', 'Состояние']
    ws.append(headers)

    # Стиль заголовков
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(fill_type='solid', fgColor='1a56a4')
        cell.alignment = Alignment(horizontal='center')

    # Данные
    appeals = Appeal.objects.select_related('category', 'status', 'assigned_to').order_by('-created_at')
    for a in appeals:
        ws.append([
            a.id,
            a.full_name,
            a.iin,
            a.phone or '—',
            str(a.category) if a.category else '—',
            str(a.status) if a.status else '—',
            a.assigned_to.username if a.assigned_to else '—',
            a.created_at.strftime('%d.%m.%Y %H:%M'),
            a.deadline.strftime('%d.%m.%Y %H:%M'),
            'Просрочено' if a.is_overdue else 'В срок',
        ])

    # Ширина колонок
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_len + 4

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="appeals.xlsx"'
    wb.save(response)
    return response
