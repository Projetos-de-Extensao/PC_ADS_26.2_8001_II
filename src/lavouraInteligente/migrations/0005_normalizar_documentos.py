"""Normaliza documentos antes dos CHECKs; só corrige os dois seeds fictícios conhecidos."""
from django.db import migrations, models

SQL = r'''
CREATE FUNCTION raizes_documento_valido(doc text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE AS $$
DECLARE base text; pesos integer[]; soma integer; resto integer; dv integer; etapa integer; i integer;
BEGIN
 IF doc !~ '^([0-9]{11}|[A-Z0-9]{12}[0-9]{2})$' THEN RETURN false; END IF;
 IF doc = repeat(substr(doc,1,1),length(doc)) THEN RETURN false; END IF;
 base := substr(doc,1,length(doc)-2);
 FOR etapa IN 0..1 LOOP
  IF length(doc)=14 THEN
   IF etapa=0 THEN pesos:=ARRAY[5,4,3,2,9,8,7,6,5,4,3,2];
   ELSE pesos:=ARRAY[6,5,4,3,2,9,8,7,6,5,4,3,2]; END IF;
  END IF;
  soma:=0;
  FOR i IN 1..length(base) LOOP
   IF length(doc)=11 THEN soma:=soma+(ascii(substr(base,i,1))-48)*(length(base)+2-i);
   ELSE soma:=soma+(ascii(substr(base,i,1))-48)*pesos[i]; END IF;
  END LOOP;
  resto:=soma%11; dv:=CASE WHEN resto<2 THEN 0 ELSE 11-resto END;
  base:=base||dv::text;
 END LOOP;
 RETURN base=doc;
END $$;
'''


def normalizar(apps, schema_editor):
    Produtor = apps.get_model('lavouraInteligente', 'Produtor')
    alias = schema_editor.connection.alias
    changes = []
    used = set()
    invalid = []
    known = {('123.456.789-00','João Pereira'):'52998224725',
             ('12.345.678/0001-90','Maria Souza'):'11222333000181'}
    import re
    with schema_editor.connection.cursor() as cur:
        for row in Produtor.objects.using(alias).order_by('pk'):
            document = known.get((row.documento,row.nome), row.documento.strip().upper())
            demo = document == 'DEMO-RAIZES'
            if not demo:
                if not re.fullmatch(r'[A-Z0-9. /-]+', document, re.ASCII):
                    invalid.append(row.pk)
                    continue
                document = re.sub(r'[. /-]', '', document)
                cur.execute('SELECT raizes_documento_valido(%s)', [document])
                if not cur.fetchone()[0]:
                    invalid.append(row.pk)
            if document in used:
                invalid.append(row.pk)
            used.add(document)
            changes.append((row.pk, document, demo))
    if invalid:
        raise RuntimeError('Corrija CPF/CNPJ inválido ou duplicado antes de migrar. IDs de produtores: '
                           + ', '.join(map(str, sorted(set(invalid)))))
    for pk, document, demo in changes:
        Produtor.objects.using(alias).filter(pk=pk).update(documento=document, simulado=demo)


class Migration(migrations.Migration):
    dependencies = [('lavouraInteligente','0004_cenariosimulado_uploadsimulado')]
    operations = [
        migrations.AddField(model_name='produtor', name='simulado',
            field=models.BooleanField(default=False, editable=False)),
        migrations.RunSQL(SQL, 'DROP FUNCTION raizes_documento_valido(text)'),
        migrations.RunPython(normalizar, migrations.RunPython.noop),
    ]
