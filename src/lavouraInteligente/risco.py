import hashlib
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .ambiental import canonical, geometry


def status_efetivo(talhao):
    """Read-time expiry and polygon checks also apply between worker executions."""
    if talhao.status!='APROVADO':return talhao.status
    try:geometry(talhao.poligono)
    except (ValueError,TypeError,KeyError):return 'REVISAO'
    analysis=talhao.atributos.get('analise_ambiental')
    if analysis:
        try:
            expires=parse_datetime(analysis.get('valido_ate',''))
            if not expires or not timezone.is_aware(expires) or expires<=timezone.now():return 'REVISAO'
            if analysis.get('poligono_sha256')!=hashlib.sha256(canonical(talhao.poligono)).hexdigest():return 'REVISAO'
        except (ValueError,TypeError):return 'REVISAO'
    return 'APROVADO'
