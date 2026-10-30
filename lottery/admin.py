import json
from django.contrib import admin, messages
from django.utils.html import format_html
from .models import Bike, PaymentLog

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

def send_mqtt_command(bike_id, command, duration=0):
    """Hàm gửi MQTT an toàn, trả về (True, None) nếu thành công hoặc (False, Lỗi) nếu thất bại"""
    try:
        import paho.mqtt.publish as publish
        topic = f"bike/{bike_id}/control"
        payload = {"command": command}
        if duration > 0:
            payload["duration"] = duration

        publish.single(
            topic,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT
        )
        return True, None
    except Exception as e:
        return False, str(e)


@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ('bike_id', 'name', 'status_badge', 'remaining_minutes_display', 'is_active')
    actions = ['unlock_5_mins', 'unlock_30_mins', 'lock_bikes_now', 'beep_find_bike']

    def status_badge(self, obj):
        if not obj.is_active:
            return format_html(
                '<span style="color: gray; font-weight: bold;">{}</span>',
                "Bảo trì",
            )
        if obj.is_rented:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                "Đang chạy",
            )
        return format_html(
            '<span style="color: #d9534f; font-weight: bold;">{}</span>',
            "Đang khóa (Rảnh)",
        )
    status_badge.short_description = "Trạng thái"

    def remaining_minutes_display(self, obj):
        if obj.is_rented:
            return f"Còn {obj.remaining_minutes} phút"
        return "0 phút"
    remaining_minutes_display.short_description = "Thời gian còn lại"

    # --- CÁC NÚT BẤM ĐÃ BỌC BẮT LỖI AN TOÀN ---
    # Trong file admin.py, sửa lại các action của BikeAdmin như sau:

    @admin.action(description="🔓 Mở khóa / Cộng thêm 5 Phút (Cứu hộ)")
    def unlock_5_mins(self, request, queryset):
        for bike in queryset:
            bike.pending_command = "UNLOCK"
            bike.pending_duration += 300  # Cộng dồn nếu đang có lệnh chờ
            bike.add_rental_time(300)     # Hàm này đã có sẵn lệnh bike.save()
            self.message_user(request, f"Đã xếp lệnh mở khóa 5 phút cho xe {bike.bike_id}!", messages.SUCCESS)

    @admin.action(description="🔓 Mở khóa / Cộng thêm 30 Phút (Thu tiền mặt)")
    def unlock_30_mins(self, request, queryset):
        for bike in queryset:
            bike.pending_command = "UNLOCK"
            bike.pending_duration += 1800
            bike.add_rental_time(1800)
            self.message_user(request, f"Đã xếp lệnh mở khóa 30 phút cho xe {bike.bike_id}!", messages.SUCCESS)

    @admin.action(description="🔒 KHÓA XE KHẨN CẤP NGAY LẬP TỨC")
    def lock_bikes_now(self, request, queryset):
        for bike in queryset:
            bike.pending_command = "LOCK"
            bike.pending_duration = 0
            bike.lock_immediately()
            self.message_user(request, f"Đã phát lệnh KHÓA KHẨN CẤP xe {bike.bike_id}!", messages.WARNING)

    @admin.action(description="🔊 Bật còi tìm xe trong bãi")
    def beep_find_bike(self, request, queryset):
        for bike in queryset:
            bike.pending_command = "FIND"
            bike.save()
            self.message_user(request, f"Đã phát lệnh còi xe {bike.bike_id}!", messages.INFO)


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ('bike', 'amount', 'duration_sec', 'content', 'created_at')
    list_filter = ('bike', 'created_at')