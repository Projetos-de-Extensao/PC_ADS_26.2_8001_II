"""AWS delivery through a durable outbox; no embedded or copied credentials."""
import hashlib
import json
import logging
import os

from botocore.config import Config
import boto3
from django.db import transaction
from django.utils import timezone

from .models import EntregaCloud

logger=logging.getLogger(__name__)

def client(service):
    return boto3.client(service,region_name=os.environ.get('AWS_DEFAULT_REGION','us-east-2'),
        config=Config(connect_timeout=5,read_timeout=20,retries={'max_attempts':2,'mode':'standard'}))

def configured():
    return all(os.environ.get(k) for k in ['RAIZES_S3_BUCKET','RAIZES_DYNAMODB_TABLE','RAIZES_SNS_TOPIC_ARN'])

def enqueue(kind,key,payload):
    # Called inside the domain transaction: a database commit also commits delivery intent.
    return EntregaCloud.objects.create(tipo=kind,chave=key,conteudo=payload)

def deliver(row):
    payload=row.conteudo
    if row.tipo=='EVIDENCIA':
        data=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        client('s3').put_object(Bucket=os.environ['RAIZES_S3_BUCKET'],Key=row.chave,Body=data,
            ContentType='application/json',ServerSideEncryption='AES256',
            Metadata={'sha256':hashlib.sha256(data).hexdigest()})
    elif row.tipo=='STATUS':
        # Older retries must never overwrite a more recent status projection.
        from botocore.exceptions import ClientError
        try:
            client('dynamodb').put_item(TableName=os.environ['RAIZES_DYNAMODB_TABLE'],Item={
                'PK':{'S':row.chave},'SK':{'S':'STATUS'},'versao':{'N':str(row.id)},
                'status':{'S':payload['status']},'registro':{'S':json.dumps(payload,ensure_ascii=False)}},
                ConditionExpression='attribute_not_exists(versao) OR versao <= :v',
                ExpressionAttributeValues={':v':{'N':str(row.id)}})
        except ClientError as exc:
            if exc.response['Error']['Code']!='ConditionalCheckFailedException':raise
    elif row.tipo=='ALERTA':
        client('sns').publish(TopicArn=os.environ['RAIZES_SNS_TOPIC_ARN'],
            Subject='Raizes: '+('SIMULACAO de risco ambiental' if payload.get('simulado') else 'mudanca de risco ambiental'),Message=json.dumps(payload,ensure_ascii=False))
    else:raise ValueError('Tipo de entrega desconhecido')

def flush(limit=100):
    if not configured():return {'enviados':0,'falhas':0,'configurado':False}
    sent=failed=0
    ids=list(EntregaCloud.objects.filter(enviado_em__isnull=True).order_by('id').values_list('id',flat=True)[:limit])
    for pk in ids:
        with transaction.atomic():
            row=EntregaCloud.objects.select_for_update().get(pk=pk)
            if row.enviado_em:continue
            row.tentativas+=1
            try:
                deliver(row);row.enviado_em=timezone.now();row.erro='';sent+=1
            except Exception as exc:
                # Store only the class/code, never credential headers or signed URLs.
                row.erro=type(exc).__name__;failed+=1
                logger.warning('Cloud delivery %s failed (%s)',row.id,row.erro)
            row.save(update_fields=['tentativas','enviado_em','erro'])
    return {'enviados':sent,'falhas':failed,'configurado':True}
