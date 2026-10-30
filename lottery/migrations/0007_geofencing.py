from django.db import migrations, models
import django.db.models.deletion


DEFAULT_POLYGON = [
    [21.0285, 105.8542],
    [21.0290, 105.8550],
    [21.0278, 105.8560],
]


def create_default_geofence(apps, schema_editor):
    Geofence = apps.get_model("lottery", "Geofence")
    Geofence.objects.get_or_create(
        name="Khu vực hồ",
        defaults={"polygon": DEFAULT_POLYGON, "is_active": True},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("lottery", "0006_alter_bike_battery_volts_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="bike",
            name="geofence_inside",
            field=models.BooleanField(default=True, verbose_name="Trong vùng địa lý"),
        ),
        migrations.AddField(
            model_name="bike",
            name="last_gps_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Lần GPS cuối"),
        ),
        migrations.AddField(
            model_name="bike",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="Vĩ độ GPS"),
        ),
        migrations.AddField(
            model_name="bike",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="Kinh độ GPS"),
        ),
        migrations.CreateModel(
            name="Geofence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Khu vực hồ", max_length=100, verbose_name="Tên khu vực")),
                ("polygon", models.JSONField(default=list, help_text="Danh sách điểm theo thứ tự quanh khu vực.", verbose_name="Đa giác (latitude, longitude)")),
                ("is_active", models.BooleanField(default=True, verbose_name="Kích hoạt")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")),
            ],
        ),
        migrations.CreateModel(
            name="GeofenceEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9, verbose_name="Vĩ độ")),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9, verbose_name="Kinh độ")),
                ("is_inside", models.BooleanField(verbose_name="Trong vùng")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")),
                ("bike", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="geofence_events", to="lottery.bike")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.RunPython(create_default_geofence, migrations.RunPython.noop),
    ]
