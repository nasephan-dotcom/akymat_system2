from django import forms
from django.contrib.auth.models import User
from .models import Appeal


class AppealForm(forms.ModelForm):
    def __init__(self, *args, is_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        if is_admin:
            self.fields['assigned_to'] = forms.ModelChoiceField(
                queryset=User.objects.filter(groups__name='Сотрудник'),
                required=False,
                label='Исполнитель',
                widget=forms.Select(attrs={'class': 'form-select'})
            )
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.TextInput) or isinstance(widget, forms.Textarea):
                widget.attrs['class'] = 'form-control'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'
            elif isinstance(widget, forms.DateTimeInput):
                widget.attrs['class'] = 'form-control'
                widget.attrs['type'] = 'datetime-local'

    class Meta:
        model = Appeal
        fields = ['full_name', 'iin', 'phone', 'text', 'category', 'deadline']
        labels = {
            'full_name': 'ФИО заявителя',
            'iin': 'ИИН',
            'phone': 'Телефон',
            'text': 'Текст обращения',
            'category': 'Категория',
            'deadline': 'Срок исполнения',
        }
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'text': forms.Textarea(attrs={'rows': 4}),
        }


class AssignForm(forms.Form):
    worker_id = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='Сотрудник'),
        label='Назначить исполнителя',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
