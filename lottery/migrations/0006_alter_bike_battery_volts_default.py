from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lottery", "0005_bike_pending_command_bike_pending_duration_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bike",
            name="battery_volts",
            field=models.FloatField(
                default=24,
                verbose_name="Điện áp bình (V)",
            ),
        ),
    ]
