from rest_framework.permissions import BasePermission, SAFE_METHODS


class LeituraPublicaEscritaEquipe(BasePermission):
    """Keep the academic read demonstration while requiring staff for mutations."""
    def has_permission(self,request,view):
        if request.method in SAFE_METHODS:return True
        from .acesso import capacidades
        capability='balanca' if view.__class__.__name__ in ['LoteViewSet','LoteTalhaoViewSet'] else 'cadastros'
        return capability in capacidades(request.user)
