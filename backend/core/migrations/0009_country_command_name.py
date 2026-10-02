from django.db import migrations, models
import re

_TRANS = str.maketrans({
    "ا":"a","آ":"a","أ":"a","إ":"e","ء":"'","ب":"b","پ":"p","ت":"t","ث":"s",
    "ج":"j","چ":"ch","ح":"h","خ":"kh","د":"d","ذ":"z","ر":"r","ز":"z","ژ":"zh",
    "س":"s","ش":"sh","ص":"s","ض":"z","ط":"t","ظ":"z","ع":"a","غ":"gh","ف":"f",
    "ق":"gh","ک":"k","ك":"k","گ":"g","ل":"l","م":"m","ن":"n","و":"v","ه":"h","ی":"y","ي":"y",
    "ى":"y","ة":"h","ؤ":"v","ئ":"y","‌":"-","۰":"0","۱":"1","۲":"2","۳":"3","۴":"4",
    "۵":"5","۶":"6","۷":"7","۸":"8","۹":"9",
})
ALIASES = {"ایران":"iran","آمریکا":"usa","انگلستان":"uk","امارات متحده عربی":"uae","کره جنوبی":"south-korea","کره شمالی":"north-korea"}

def make_alias(name):
    raw = ALIASES.get(name, name.translate(_TRANS).lower())
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or "country"

def forwards(apps, schema_editor):
    Country = apps.get_model("core", "Country")
    used = set()
    for c in Country.objects.order_by("id"):
        base = make_alias(c.name)[:60]
        candidate = base or "country"
        n = 2
        while candidate in used:
            suffix = f"-{n}"
            candidate = f"{base[:72-len(suffix)]}{suffix}"
            n += 1
        used.add(candidate)
        c.command_name = candidate
        c.save(update_fields=["command_name"])

class Migration(migrations.Migration):
    dependencies = [("core", "0008_agreement_alert_diplomaticproposal_and_more")]
    operations = [
        migrations.AddField(
            model_name="country",
            name="command_name",
            field=models.CharField(blank=True, db_index=True, max_length=72, null=True, unique=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="country",
            name="command_name",
            field=models.CharField(db_index=True, max_length=72, unique=True),
        ),
    ]
