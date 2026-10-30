import json
import re
import urllib.parse
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import paho.mqtt.publish as publish
from .models import Bike, PaymentLog

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

BANK_ID = "TPB"                  # Mã ngân hàng của bạn
ACCOUNT_NO = "37312101986"       # Số tài khoản của bạn
ACCOUNT_NAME = "DO NGOC TUAN"   # Tên chủ tài khoản
SEPAY_API_KEY = "Tuan.m12345*"

PRICING = {
    2000: 60,      # Test: 2.000đ -> 1 phút
    30000: 1800,   # 30.000đ -> 30 phút
    50000: 3600,   # 50.000đ -> 60 phút
}

def rent_bike_view(request, bike_id):
    bike, _ = Bike.objects.get_or_create(bike_id=bike_id)

    if not bike.is_active:
        return HttpResponse("<h2 style='text-align:center;margin-top:50px;'>Xe đang tạm ngưng bảo trì. Vui lòng chọn xe bên cạnh!</h2>")

    clean_bike_id = bike.bike_id.replace("_", "")
    amount = int(request.GET.get("amount", 30000))
    transfer_content = f"THUEXE {clean_bike_id}"

    encoded_content = urllib.parse.quote(transfer_content)
    encoded_name = urllib.parse.quote(ACCOUNT_NAME)
    qr_url = f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact2.png?amount={amount}&addInfo={encoded_content}&accountName={encoded_name}"

    # Lấy số giây hiện tại lúc khách vừa mở trang web (để so sánh khi có tiền mới vào)
    from django.utils import timezone
    initial_rem_sec = 0
    if bike.is_rented:
        initial_rem_sec = max(0, int((bike.rental_end_time - timezone.now()).total_seconds()))

    if bike.is_rented:
        status_banner = f"""
        <div id="status-banner" class="status-banner" style="background:#fff3cd; color:#856404; font-weight:bold;">
            ⚡ Xe đang hoạt động (Còn <span id="banner-mins">{bike.remaining_minutes}</span> phút).<br>
            Quét mã bên dưới nếu bạn muốn MUA THÊM GIỜ!
        </div>
        """
    else:
        status_banner = """
        <div id="status-banner" class="status-banner" style="background:#d4edda; color:#155724; font-weight:bold;">
            ✅ Xe đang sẵn sàng phục vụ!
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Thuê Xe Điện - {bike.bike_id}</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                min-height: 100vh;
                padding: 5px 0 20px;
                background: #f4f7f6;
                color: #111;
                font-family: Arial, sans-serif;
                text-align: center;
            }}
            .card {{
                width: min(100%, 550px);
                min-height: 100vh;
                margin: 0 auto;
                padding: 34px 22px 24px;
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.08);
            }}
            h2 {{
                margin: 14px auto 28px;
                max-width: 500px;
                font-size: clamp(25px, 5vw, 31px);
                line-height: 1.15;
            }}
            .status-banner {{
                margin: 0 0 18px;
                padding: 13px 10px;
                border-radius: 10px;
                font-size: 20px;
            }}
            .package-label {{
                margin: 0 0 18px;
                font-size: 20px;
            }}
            .package-options {{
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 8px;
            }}
            .btn {{
                display: inline-block;
                min-width: 126px;
                padding: 12px 13px;
                background: #087df5;
                color: white;
                text-decoration: none;
                border-radius: 7px;
                font-size: 16px;
                font-weight: bold;
            }}
            .btn:hover {{ background: #0568d0; }}
            .qr-image {{
                display: block;
                width: min(100%, 280px);
                margin: 27px auto 0;
                border: 1px solid #264a85;
                border-radius: 0;
            }}
            .waiting-message {{
                margin: 28px 0 0;
                color: #ef4b4b;
                font-size: 21px;
                font-weight: bold;
                line-height: 1.4;
            }}
            .waiting-message small {{
                display: block;
                color: #555;
                font-size: 16px;
                font-weight: normal;
                line-height: 1.35;
            }}
            @media (max-width: 420px) {{
                .card {{ padding: 25px 14px 20px; }}
                .btn {{ min-width: 0; flex: 1 1 100px; font-size: 14px; }}
                .status-banner, .package-label {{ font-size: 17px; }}
                .waiting-message {{ font-size: 19px; }}
            }}

            /* Giao diện thông báo mở khóa thành công (Mặc định ẩn, hiện lên khi nhận được tiền) */
            #success-box {{
                display: none;
                background: #e8f5e9;
                border: 2px solid #28a745;
                color: #155724;
                padding: 25px 15px;
                border-radius: 12px;
                margin-top: 15px;
                animation: popIn 0.4s ease;
            }}
            @keyframes popIn {{
                0% {{ transform: scale(0.8); opacity: 0; }}
                100% {{ transform: scale(1); opacity: 1; }}
            }}
            .timer-big {{ font-size: 32px; font-weight: bold; color: #28a745; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>{bike.name}<br>({bike.bike_id})</h2>
            {status_banner}

            <!-- HỘP THÔNG BÁO THÀNH CÔNG (Tự động bật lên khi chuyển khoản xong) -->
            <div id="success-box">
                <div style="font-size: 50px;">🎉</div>
                <h3 style="color: #28a745; margin: 10px 0;">ĐÃ MỞ KHÓA XE THÀNH CÔNG!</h3>
                <p id="esp-sync-msg" style="font-size: 14px; color: #555;">
                    Hệ thống đã nhận được thanh toán và bật điện xe. Chúc bạn dạo hồ vui vẻ!
                </p>
                <div class="timer-big" id="countdown-display">--:--</div>
                <p style="font-size: 13px; color: #666;">Thời gian sử dụng còn lại</p>
                <button onclick="document.getElementById('qr-section').style.display='block'; this.style.display='none';"
                        style="margin-top:10px; padding:8px 15px; background:#17a2b8; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">
                    + Mua thêm giờ
                </button>
            </div>

            <!-- KHU VỰC CHỌN GÓI & QUÉT MÃ QR -->
            <div id="qr-section">
                <p class="package-label">Bấm chọn gói thời gian:</p>
                <div class="package-options">
                    <a class="btn" href="?amount=2000">Test 1P (2k)</a>
                    <a class="btn" href="?amount=30000">30 Phút (30k)</a>
                    <a class="btn" href="?amount=50000">60 Phút (50k)</a>
                </div>
                <img class="qr-image" src="{qr_url}" alt="Mã VietQR" />
                <p class="waiting-message">
                    ⏳ Đang chờ thanh toán...
                    <small>(Màn hình này sẽ tự động báo thành công ngay sau khi bạn chuyển khoản!)</small>
                </p>
            </div>
        </div>

        <script>
            let initialSec = {initial_rem_sec};
            let currentRemSec = initialSec;
            let isUnlockedTriggered = false;

            function formatTime(sec) {{
                let m = Math.floor(sec / 60);
                let s = sec % 60;
                return (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
            }}

            // Hàm chuyển giao diện sang trạng thái "BÁO HẾT GIỜ"
            function showExpiredMessage() {{
                isUnlockedTriggered = false;
                initialSec = 0;
                document.getElementById("success-box").style.display = "none";
                document.getElementById("qr-section").style.display = "block";

                let banner = document.getElementById("status-banner");
                banner.style.display = "block";
                banner.style.background = "#f8d7da";
                banner.style.color = "#721c24";
                banner.innerHTML = "⏰ <b>ĐÃ HẾT GIỜ THUÊ & KHÓA XE!</b><br>Cảm ơn bạn đã sử dụng dịch vụ. Quét mã bên dưới nếu bạn muốn thuê tiếp!";

                if (navigator.vibrate) navigator.vibrate([300, 100, 300, 100, 300]);
            }}

            // Đếm ngược từng giây trên màn hình
            setInterval(() => {{
                if (currentRemSec > 0) {{
                    currentRemSec--;
                    document.getElementById("countdown-display").innerText = formatTime(currentRemSec);

                    // Cảnh báo đổi màu đồng hồ sang Đỏ khi còn dưới 60 giây
                    if (currentRemSec <= 60) {{
                        document.getElementById("countdown-display").style.color = "#dc3545";
                    }} else {{
                        document.getElementById("countdown-display").style.color = "#28a745";
                    }}

                    // Khi đếm ngược chạm 0 -> Báo hết giờ ngay!
                    if (currentRemSec === 0 && isUnlockedTriggered) {{
                        showExpiredMessage();
                    }}
                }}
            }}, 1000);

            // Đồng bộ với Server mỗi 2 giây
            setInterval(() => {{
                fetch('/api/status/{bike.bike_id}/')
                    .then(res => res.json())
                    .then(data => {{
                        // 1. Khi khách vừa nạp tiền (hoặc mua thêm giờ)
                        if (data.is_rented && data.remaining_seconds > initialSec + 10) {{
                            currentRemSec = data.remaining_seconds;
                            initialSec = data.remaining_seconds;

                            document.getElementById("qr-section").style.display = "none";
                            document.getElementById("status-banner").style.display = "none";
                            document.getElementById("success-box").style.display = "block";
                            document.getElementById("countdown-display").innerText = formatTime(currentRemSec);

                            if (!isUnlockedTriggered && navigator.vibrate) {{
                                navigator.vibrate([200, 100, 200]);
                            }}
                            isUnlockedTriggered = true;
                        }}

                        // 2. Nếu đang chạy mà hết giờ trên Server (hoặc Chủ xe bấm Khóa khẩn cấp từ Admin)
                        if (isUnlockedTriggered && !data.is_rented) {{
                            currentRemSec = 0;
                            showExpiredMessage();
                        }}

                        // 3. Cập nhật xác nhận từ mạch ESP32
                        if (isUnlockedTriggered) {{
                            if (data.esp32_confirmed) {{
                                document.getElementById("esp-sync-msg").innerHTML = "✅ <b>Xe đã bật điện!</b> Bạn có thể vặn ga di chuyển ngay.";
                            }} else {{
                                document.getElementById("esp-sync-msg").innerHTML = "⏳ Đang gửi tín hiệu bật điện xuống xe (chờ 2-3 giây)...";
                            }}
                        }}
                    }})
                    .catch(err => console.log(err));
            }}, 2000);
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)


@csrf_exempt
def payment_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        content = str(data.get("content") or data.get("description") or "").upper()
        amount = int(data.get("transferAmount") or data.get("amount") or 0)

        match = re.search(r"THUEXE\s*BIKE(\d+)", content)
        if match:
            bike_number = match.group(1)
            bike_id = f"BIKE_{bike_number}"

            bike, _ = Bike.objects.get_or_create(bike_id=bike_id)

            duration_sec = PRICING.get(amount)
            if not duration_sec:
                duration_sec = int((amount / 1000) * 60)

            if duration_sec > 0:
                # 1. Bắn lệnh MQTT xuống ESP32
                topic = f"bike/{bike.bike_id}/control"
                payload = json.dumps({"command": "UNLOCK", "duration": duration_sec})
                #publish.single(topic, payload=payload, hostname=MQTT_BROKER, port=MQTT_PORT)
                if duration_sec > 0:
                    bike.pending_command = "UNLOCK"
                    bike.pending_duration += duration_sec
                    bike.add_rental_time(duration_sec) # Tự động lưu vào DB

                    PaymentLog.objects.create(
                        bike=bike, amount=amount, duration_sec=duration_sec, content=content
                    )
                    return JsonResponse({"success": True, "bike": bike.bike_id, "added_sec": duration_sec})

                # 2. Cập nhật thời gian vào Database và lưu lịch sử thu tiền
                bike.add_rental_time(duration_sec)
                PaymentLog.objects.create(
                    bike=bike,
                    amount=amount,
                    duration_sec=duration_sec,
                    content=content
                )

                return JsonResponse({"success": True, "bike": bike.bike_id, "added_sec": duration_sec})

        return JsonResponse({"success": True, "message": "Ignored"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
@csrf_exempt
def esp32_sync_api(request, bike_id):
    bike, _ = Bike.objects.get_or_create(bike_id=bike_id)

    # Cập nhật điện áp ắc quy từ ESP32 gửi lên (nếu có)
    batt = request.GET.get("batt")
    if batt:
        try:
            bike.battery_volts = float(batt)
        except ValueError:
            pass

    # Lấy lệnh đang chờ gửi xuống cho ESP32
    cmd = bike.pending_command
    dur = bike.pending_duration

    # Sau khi giao lệnh cho ESP32 xong thì xóa lệnh chờ đi để không bị lặp lại
    if cmd:
        bike.pending_command = ""
        bike.pending_duration = 0
    bike.save()

    return JsonResponse({
        "command": cmd if cmd else "NONE",
        "duration": dur
    })

def bike_status_api(request, bike_id):
    bike = get_object_or_404(Bike, bike_id=bike_id)

    # Tính chính xác tổng số giây còn lại
    remaining_seconds = 0
    if bike.is_rented:
        from django.utils import timezone
        diff = bike.rental_end_time - timezone.now()
        remaining_seconds = max(0, int(diff.total_seconds()))

    return JsonResponse({
        "is_rented": bike.is_rented,
        "remaining_minutes": bike.remaining_minutes,
        "remaining_seconds": remaining_seconds,
        # Cờ báo hiệu mạch ESP32 đã lấy lệnh về chưa (pending_command == "" nghĩa là ESP32 đã nhận lệnh)
        "esp32_confirmed": (bike.pending_command == "")
    })