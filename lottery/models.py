from django.db import models
from django.utils import timezone
from datetime import timedelta

class Bike(models.Model):
    bike_id = models.CharField("Mã xe (VD: BIKE_01)", max_length=20, unique=True)
    name = models.CharField("Tên hiển thị", max_length=50, default="Xe điện ven hồ 01")
    is_active = models.BooleanField("Cho phép hoạt động", default=True)
    rental_end_time = models.DateTimeField("Thời điểm hết giờ", null=True, blank=True)
    battery_volts = models.FloatField("Điện áp bình (V)", default=24)
    updated_at = models.DateTimeField(auto_now=True)
    # ---> THÊM 2 DÒNG NÀY ĐỂ HÀNG ĐỢI LỆNH CHO ESP32 LẤY VỀ <---
    pending_command = models.CharField("Lệnh chờ", max_length=20, blank=True, default="")
    pending_duration = models.IntegerField("Thời gian chờ (Giây)", default=0)
    latitude = models.DecimalField("Vĩ độ GPS", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("Kinh độ GPS", max_digits=9, decimal_places=6, null=True, blank=True)
    geofence_inside = models.BooleanField("Trong vùng địa lý", default=True)
    last_gps_at = models.DateTimeField("Lần GPS cuối", null=True, blank=True)

    @property
    def is_rented(self):
        """Kiểm tra xe hiện tại có đang trong thời gian thuê hay không"""
        if self.rental_end_time and self.rental_end_time > timezone.now():
            return True
        return False

    @property
    def remaining_minutes(self):
        """Số phút thuê còn lại"""
        if self.is_rented:
            diff = self.rental_end_time - timezone.now()
            return max(1, int(diff.total_seconds() // 60))
        return 0

    def add_rental_time(self, seconds):
        """Cộng dồn thời gian thuê mới vào Database"""
        now = timezone.now()
        if self.rental_end_time and self.rental_end_time > now:
            self.rental_end_time += timedelta(seconds=seconds)
        else:
            self.rental_end_time = now + timedelta(seconds=seconds)
        self.save()

    def lock_immediately(self):
        """Khóa xe ngay lập tức"""
        self.rental_end_time = timezone.now()
        self.save()

    def __str__(self):
        status = f"Đang chạy ({self.remaining_minutes}p)" if self.is_rented else "Đang rảnh"
        return f"{self.bike_id} - {status}"


class PaymentLog(models.Model):
    bike = models.ForeignKey(Bike, on_delete=models.CASCADE, related_name="payments")
    amount = models.IntegerField("Số tiền (VNĐ)")
    duration_sec = models.IntegerField("Thời gian cấp (Giây)")
    content = models.CharField("Nội dung CK", max_length=255)
    created_at = models.DateTimeField("Thời gian", auto_now_add=True)

    def __str__(self):
        return f"{self.bike.bike_id} - {self.amount}đ ({self.created_at.strftime('%H:%M %d/%m')})"


class Geofence(models.Model):
    name = models.CharField("Tên khu vực", max_length=100, default="Khu vực hồ")
    polygon = models.JSONField(
        "Đa giác (latitude, longitude)",
        default=list,
        help_text="Danh sách điểm theo thứ tự quanh khu vực.",
    )
    is_active = models.BooleanField("Kích hoạt", default=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    def __str__(self):
        return self.name


class GeofenceEvent(models.Model):
    bike = models.ForeignKey(Bike, on_delete=models.CASCADE, related_name="geofence_events")
    latitude = models.DecimalField("Vĩ độ", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("Kinh độ", max_digits=9, decimal_places=6)
    is_inside = models.BooleanField("Trong vùng")
    created_at = models.DateTimeField("Thời gian", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        state = "Trong vùng" if self.is_inside else "Ngoài vùng"
        return f"{self.bike.bike_id} - {state} ({self.created_at:%d/%m %H:%M})"