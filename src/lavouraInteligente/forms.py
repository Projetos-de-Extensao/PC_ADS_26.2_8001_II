from django import forms
from .models import Produtor
from .validacao import normalizar_documento, formatar_documento


class ProdutorForm(forms.ModelForm):
    documento = forms.CharField(label='CPF/CNPJ', max_length=18,
        help_text='CPF: 11 dígitos. CNPJ: 14 caracteres. A pontuação é aplicada automaticamente.',
        widget=forms.TextInput(attrs={'data-documento':'', 'autocomplete':'off', 'spellcheck':'false'}))

    class Meta:
        model = Produtor
        fields = '__all__'

    class Media:
        js = ['raizes/documentos.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['documento'] = formatar_documento(self.instance.documento)
            if self.instance.simulado:
                self.fields['documento'].disabled = True

    def clean_documento(self):
        return normalizar_documento(self.cleaned_data['documento'])
