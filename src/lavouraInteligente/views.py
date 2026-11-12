import json

from django.core.exceptions import FieldError
from django.db import transaction, IntegrityError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.response import Response

from .models import EventoAuditoria, Fazenda, Lote, LoteTalhao, Produtor, StatusRisco, Talhao
from django.db.models.deletion import ProtectedError
from .serializers import (
    FazendaSerializer,
    LoteSerializer,
    LoteTalhaoSerializer,
    ProdutorSerializer,
    RecebimentoSerializer,
    TalhaoSerializer,
)


class RegraNegocioError(Exception):
    pass


class ReferenciaAtiva(APIException):
    status_code = 409
    default_detail = 'Este cadastro possui referências ativas. Remova os vínculos antes de excluir.'


class RegistroAuditoriaMixin:
    def handle_exception(self, exc):
        if isinstance(exc, IntegrityError):
            return Response({'detalhe':'O cadastro viola uma regra de integridade. Confira valores positivos, '
                'documentos válidos, campos obrigatórios e registros duplicados.'}, status=409)
        return super().handle_exception(exc)

    def registrar(self,instance,acao):
        usuario=self.request.user if self.request.user.is_authenticated else None
        EventoAuditoria.objects.create(ator=usuario,acao=acao,
           recurso=instance._meta.model_name,recurso_id=instance.pk,
           descricao=f'{instance}: '+{'CRIAR':'cadastro criado','ALTERAR':'cadastro atualizado','EXCLUIR':'cadastro excluído'}[acao])

    @transaction.atomic
    def perform_create(self,serializer):
        if serializer.Meta.model is LoteTalhao:
            serializer.validated_data['lote']=Lote.objects.select_for_update().get(pk=serializer.validated_data['lote'].pk)
            serializer.validate(serializer.validated_data)
        self.registrar(serializer.save(),'CRIAR')

    @transaction.atomic
    def perform_update(self,serializer):
        target=serializer.instance
        lote=target if isinstance(target,Lote) else target.lote if isinstance(target,LoteTalhao) else None
        if lote:
            ids={lote.pk}
            if isinstance(target,LoteTalhao) and 'lote' in serializer.validated_data:ids.add(serializer.validated_data['lote'].pk)
            locked={row.pk:row for row in Lote.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
            if any(hasattr(row,'decisao') for row in locked.values()):
                raise ReferenciaAtiva('Um lote com decisão registrada e seus itens não podem ser alterados.')
            if isinstance(target,LoteTalhao):
                serializer.validated_data['lote']=locked[serializer.validated_data.get('lote',lote).pk]
                serializer.validate(serializer.validated_data)
        before=serializer.instance.poligono if isinstance(serializer.instance,Talhao) else None
        self.registrar(serializer.save(),'ALTERAR')
        if before is not None and before!=serializer.instance.poligono:
            from .ambiental import canonical
            from .cloud import enqueue
            import hashlib
            snapshot={'talhao':serializer.instance.pk,'antes':before,'depois':serializer.instance.poligono,
                'sha256':hashlib.sha256(canonical(serializer.instance.poligono)).hexdigest()}
            event=EventoAuditoria.objects.create(ator=self.request.user,acao='VERSIONAR_POLIGONO',
                recurso='talhao',recurso_id=serializer.instance.pk,
                descricao=f'{serializer.instance.codigo}: nova versão do polígono',dados=snapshot)
            enqueue('EVIDENCIA',f'poligonos/talhao-{serializer.instance.pk}/evento-{event.pk}.json',snapshot)

    @transaction.atomic
    def perform_destroy(self,instance):
        lote=instance if isinstance(instance,Lote) else instance.lote if isinstance(instance,LoteTalhao) else None
        if lote:lote=Lote.objects.select_for_update().get(pk=lote.pk)
        if lote and hasattr(lote,'decisao'):
            raise ReferenciaAtiva('Um lote com decisão registrada e seus itens são preservados.')
        if isinstance(instance,Produtor) and instance.fazendas.exists():raise ReferenciaAtiva()
        if isinstance(instance,Fazenda) and instance.talhoes.exists():raise ReferenciaAtiva()
        self.registrar(instance,'EXCLUIR')
        try:instance.delete()
        except ProtectedError:raise ReferenciaAtiva()


class ProdutorViewSet(RegistroAuditoriaMixin, viewsets.ModelViewSet):
    queryset = Produtor.objects.prefetch_related("fazendas__talhoes")
    serializer_class = ProdutorSerializer


class FazendaViewSet(RegistroAuditoriaMixin, viewsets.ModelViewSet):
    queryset = Fazenda.objects.select_related("produtor").prefetch_related("talhoes")
    serializer_class = FazendaSerializer


class TalhaoViewSet(RegistroAuditoriaMixin, viewsets.ModelViewSet):
    """CRUD de talhões com filtro por campos do JSON `atributos`.

    Exemplos: ?atributos__bioma=cerrado  |  ?atributos__ndvi__gte=0.5
              ?atributos__contains={"fonte": "MapBiomas"}  (consulta compatível com GIN; plano depende do otimizador)
    """

    serializer_class = TalhaoSerializer

    def get_queryset(self):
        qs = Talhao.objects.select_related("fazenda")
        params = self.request.query_params
        try:
            for chave in params:
                if not chave.startswith("atributos__"):
                    continue
                valor = params[chave]
                try:
                    valor = json.loads(valor)
                except ValueError:
                    pass
                qs = qs.filter(**{chave: valor})
            for campo in ("status", "cultura", "fazenda"):
                if campo in params:
                    qs = qs.filter(**{campo: params[campo]})
        except (FieldError, ValueError, TypeError) as exc:
            raise ValidationError({"filtro": str(exc)})
        return qs


class LoteTalhaoViewSet(RegistroAuditoriaMixin, viewsets.ModelViewSet):
    queryset = LoteTalhao.objects.select_related("lote", "talhao")
    serializer_class = LoteTalhaoSerializer


class LoteViewSet(RegistroAuditoriaMixin, viewsets.ModelViewSet):
    queryset = Lote.objects.prefetch_related("itens__talhao")
    serializer_class = LoteSerializer

    @action(detail=False, methods=["post"])
    def receber(self, request):
        """Recepção do lote na balança: grava Lote + itens numa única transação.

        - RN-08 / RF-LOT-03: o lote assume o pior status entre seus talhões
          (BLOQUEADO > REVISAO > APROVADO); RN-04: talhão sem polígono não é APROVADO.
        - Integridade: a soma dos pesos dos itens deve ser igual ao peso total e um
          talhão não pode se repetir no lote. Qualquer violação desfaz toda a gravação.
        """
        entrada = RecebimentoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        try:
            with transaction.atomic():
                lote = Lote.objects.create(codigo=dados["codigo"], peso_total_kg=dados["peso_total_kg"])
                soma = 0
                vistos = set()
                ambientes = set()
                piores = {StatusRisco.BLOQUEADO: [], StatusRisco.REVISAO: []}
                for item in dados["itens"]:
                    talhao = Talhao.objects.select_for_update().get(pk=item["talhao"].pk)
                    from .models import CenarioSimulado
                    ambientes.add(CenarioSimulado.objects.filter(talhao=talhao).exists())
                    if len(ambientes)>1:
                        raise RegraNegocioError('Um lote não pode misturar talhões do laboratório com origens operacionais.')
                    if talhao.pk in vistos:
                        raise RegraNegocioError(f"Talhão {talhao.codigo} repetido no mesmo lote.")
                    vistos.add(talhao.pk)
                    LoteTalhao.objects.create(lote=lote, talhao=talhao, peso_kg=item["peso_kg"])
                    soma += item["peso_kg"]
                    from .risco import status_efetivo
                    atual = status_efetivo(talhao)
                    if atual in piores:
                        piores[atual].append(talhao.codigo)
                if soma != dados["peso_total_kg"]:
                    raise RegraNegocioError(
                        f"Soma dos itens ({soma} kg) diferente do peso total ({dados['peso_total_kg']} kg)."
                    )
                if piores[StatusRisco.BLOQUEADO]:
                    lote.status = StatusRisco.BLOQUEADO
                    lote.motivo = "Recusar: talhão BLOQUEADO na origem: " + ", ".join(piores[StatusRisco.BLOQUEADO])
                elif piores[StatusRisco.REVISAO]:
                    lote.status = StatusRisco.REVISAO
                    lote.motivo = "Revisão humana: talhão em REVISÃO na origem: " + ", ".join(piores[StatusRisco.REVISAO])
                else:
                    lote.status = StatusRisco.APROVADO
                    lote.motivo = "Origem rastreável e sem ocorrência crítica nos talhões."
                lote.save()
                EventoAuditoria.objects.create(ator=request.user if request.user.is_authenticated else None,
                    acao='RECEBER_LOTE',recurso='lote',recurso_id=lote.id,
                    descricao=f'{lote.codigo}: lote recebido na balança',dados={'status':lote.status,'motivo':lote.motivo})
        except RegraNegocioError as exc:
            return Response({"detalhe": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(LoteSerializer(lote).data, status=status.HTTP_201_CREATED)
