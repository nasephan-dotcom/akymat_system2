from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Status(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название')

    class Meta:
        verbose_name = 'Статус'
        verbose_name_plural = 'Статусы'

    def __str__(self):
        return self.name


class Appeal(models.Model):
    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    iin = models.CharField(max_length=12, verbose_name='ИИН')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    text = models.TextField(verbose_name='Текст обращения')

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name='Категория')
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, verbose_name='Статус')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    deadline = models.DateTimeField(verbose_name='Срок исполнения')

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appeals',
        verbose_name='Исполнитель'
    )

    class Meta:
        verbose_name = 'Обращение'
        verbose_name_plural = 'Обращения'

    def __str__(self):
        return self.full_name

    # БАГ ИСПРАВЛЕН: добавлен @property для корректной работы в шаблонах
    @property
    def is_overdue(self):
        if self.status and self.status.name.lower() in ['завершено', 'закрыто', 'выполнено']:
            return False
        return self.deadline < timezone.now()

    @property
    def days_left(self):
        delta = self.deadline - timezone.now()
        return delta.days


class AppealHistory(models.Model):
    appeal = models.ForeignKey(Appeal, on_delete=models.CASCADE, verbose_name='Обращение')
    old_status = models.ForeignKey(
        Status, on_delete=models.SET_NULL, null=True,
        related_name='old_status', verbose_name='Старый статус'
    )
    new_status = models.ForeignKey(
        Status, on_delete=models.SET_NULL, null=True,
        related_name='new_status', verbose_name='Новый статус'
    )
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Изменил')
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата изменения')
    comment = models.TextField(blank=True, verbose_name='Комментарий')

    class Meta:
        verbose_name = 'История изменений'
        verbose_name_plural = 'История изменений'
