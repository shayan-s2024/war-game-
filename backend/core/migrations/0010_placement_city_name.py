from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0009_country_command_name")]

    operations = [
        migrations.AddField(
            model_name="placement",
            name="city_name",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
