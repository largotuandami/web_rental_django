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