"""Regras compartilhadas por modelos, Admin e API. Máscara não é armazenamento."""
import re

from django.core.exceptions import ValidationError

UFS = tuple('AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split())
UF_CHOICES = [(uf, uf) for uf in UFS]
DOCUMENTO_DEMO = 'DEMO-RAIZES'


def normalizar_documento(value):
    text = str(value).strip().upper()
    if text == DOCUMENTO_DEMO:
        return text
    if not re.fullmatch(r'[A-Z0-9. /-]+', text, flags=re.ASCII):
        raise ValidationError('Informe CPF ou CNPJ, com ou sem a pontuação da máscara.')
    return re.sub(r'[. /-]', '', text)


def documento_valido(value):
    """CPF numérico ou CNPJ numérico/alfanumérico; DV módulo 11 (ASCII − 48)."""
    if not re.fullmatch(r'(?:[0-9]{11}|[A-Z0-9]{12}[0-9]{2})', value, flags=re.ASCII):
        return False
    if len(set(value)) == 1:
        return False
    base = value[:-2]
    for offset in range(2):
        if len(value) == 11:
            weights = list(range(len(base) + 1, 1, -1))
        else:
            weights = ([5,4,3,2,9,8,7,6,5,4,3,2] if offset == 0 else
                       [6,5,4,3,2,9,8,7,6,5,4,3,2])
        rest = sum((ord(c) - 48) * w for c, w in zip(base, weights)) % 11
        base += str(0 if rest < 2 else 11 - rest)
    return base == value


def validar_documento(value):
    if not documento_valido(normalizar_documento(value)):
        raise ValidationError('CPF/CNPJ inválido: confira o tamanho e os dígitos verificadores.')


def formatar_documento(value):
    if value == DOCUMENTO_DEMO:
        return value
    if len(value) == 11:
        return f'{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:]}'
    if len(value) == 14:
        return f'{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}'
    return value
