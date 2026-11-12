"""Functional roles enforced by Django; Cognito/MFA are not impersonated."""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

TODAS={'cadastros','balanca','analise','campo','laboratorio','exportar','consultar'}
PERFIS={
    'Gestor':TODAS,
    'Analista':{'cadastros','analise','laboratorio','exportar','consultar'},
    'Operador da balança':{'balanca','consultar'},
    'Piloto':{'campo','consultar'},
    'Auditor':{'consultar','exportar'},
}

def capacidades(user):
    if not user.is_authenticated or not user.is_active or not user.is_staff:return set()
    if user.is_superuser:return TODAS.copy()
    groups=set(user.groups.values_list('name',flat=True))
    known=groups.intersection(PERFIS)
    # Preserve legacy staff accounts; assigning a named role enables the narrower matrix.
    if not groups:return TODAS.copy()
    return set().union(*(PERFIS[name] for name in known)) if known else {'consultar'}

def perfil(user):
    if user.is_superuser:return 'Administrador'
    names=[name for name in user.groups.values_list('name',flat=True) if name in PERFIS]
    return ', '.join(names) or 'Equipe da cooperativa'

def permite(capability):
    def decorate(view):
        @wraps(view)
        @login_required
        def wrapped(request,*args,**kwargs):
            if capability not in capacidades(request.user):
                return JsonResponse({'detalhe':'Seu perfil não permite esta ação.'},status=403)
            return view(request,*args,**kwargs)
        return wrapped
    return decorate
