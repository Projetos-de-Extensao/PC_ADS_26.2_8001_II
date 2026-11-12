"""Expressões declarativas para CHECKs reais no PostgreSQL, versionadas em migrations."""
from decimal import Decimal
from django.db import models
from django.db.models import Q, F
from django.db.models.lookups import Exact
from .validacao import UFS


def dominio(field, values, name):
    return models.CheckConstraint(condition=Q(**{field + '__in': list(values)}), name=name,
        violation_error_message='Valor fora do domínio permitido.')


def preenchido(field, name):
    return models.CheckConstraint(condition=Q(**{field + '__regex': r'[^\s]'}), name=name,
        violation_error_message='Este campo não pode ficar vazio ou conter apenas espaços.')


def positivo(field, digits, name):
    return models.CheckConstraint(condition=Q(**{field + '__gt': 0, field + '__lte': Decimal('9'*(digits-2)+'.99')}),
        name=name, violation_error_message='Informe um valor positivo dentro do limite do campo.')


def sha256(field, name):
    return models.CheckConstraint(condition=Q(**{field+'__regex': r'^[0-9a-f]{64}$'}), name=name,
        violation_error_message='O hash SHA-256 deve conter 64 caracteres hexadecimais minúsculos.')


def objeto(field, name, nullable=False):
    expression = Exact(models.Func(F(field), function='jsonb_typeof', output_field=models.CharField()),
        models.Value('object'))
    condition = Q(expression)
    if nullable:
        condition = Q(**{field+'__isnull': True}) | condition
    return models.CheckConstraint(condition=condition, name=name,
        violation_error_message='Informe um objeto JSON, não uma lista ou valor escalar.')


def uf(field, name):
    return dominio(field, UFS, name)
