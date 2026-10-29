from django.db import transaction as db_transaction  # Module transaction
from .models import LotteryResult, Bet  # Import từ app 'lottery'
from wallet.models import Transaction  # Import 'Transaction' từ app 'wallet'
from decimal import Decimal
import google.generativeai as genai
import os
import json
from PIL import Image


# --- LOGIC GEMINI (Động) ---
# (Toàn bộ phần 'get_dynamic_gemini_prompt' và 'get_results_from_gemini'
#  giữ nguyên, không cần thay đổi)
def get_dynamic_gemini_prompt(prize_count):
    if prize_count == 27:
        # Miền Bắc (27 giải)
        prize_structure = """
        1. Giải Đặc Biệt (1 giải)
        2. Giải Nhất (1 giải)
        3. Giải Nhì (2 giải)
        4. Giải Ba (6 giải)
        5. Giải Tư (4 giải)
        6. Giải Năm (6 giải)
        7. Giải Sáu (3 giải)
        8. Giải Bảy (4 giải)
        """
    else:
        # Miền Nam/Trung (18 giải)
        prize_structure = """
        1. Giải Đặc Biệt (1 giải)
        2. Giải Nhất (1 giải)
        3. Giải Nhì (1 giải)
        4. Giải Ba (2 giải)
        5. Giải Tư (7 giải)
        6. Giải Năm (1 giải)
        7. Giải Sáu (3 giải)
        8. Giải Bảy (1 giải)
        9. Giải Tám (1 giải)
        """

    return f"""
Bạn là một trợ lý AI chuyên bóc tách dữ liệu xổ số.
Nhiệm vụ của bạn là phân tích hình ảnh kết quả xổ số.
Hãy tìm {prize_count} giải thưởng theo đúng cấu trúc sau:
{prize_structure}

Hãy trả về CHỈ MỘT đối tượng JSON (JSON object) duy nhất,
không có bất kỳ văn bản giải thích nào khác.
Định dạng JSON:
{{
  "prizes": ["<giải ĐB>", "<giải Nhất>", ..., "<giải cuối cùng>"]
}}
"""


def get_results_from_gemini(image_file, prize_count):
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("Không tìm thấy GEMINI_API_KEY.")

    genai.configure(api_key=api_key)
    img = Image.open(image_file)

    prompt = get_dynamic_gemini_prompt(prize_count)

    print(f"Đang gửi ảnh đến Gemini (Hỏi {prize_count} giải)...")
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content([prompt, img])

    raw_json = response.text.strip().replace("```json", "").replace("```", "")
    data = json.loads(raw_json)
    prizes_list = data.get("prizes")

    if not prizes_list or len(prizes_list) != prize_count:
        raise ValueError(f"Gemini chỉ trả về {len(prizes_list)} giải (cần {prize_count}).")

    print(f"Gemini trả về {len(prizes_list)} giải. GĐB: {prizes_list[0]}")
    return prizes_list


# --- LOGIC TÍNH TOÁN (Đã nâng cấp) ---
DE_RATE = Decimal('70.0')
LO_RATE = Decimal('80.0') / Decimal('20.0')


def process_lottery_results(process_date, station_id):
    try:
        result = LotteryResult.objects.get(date=process_date, station_id=station_id)
    except LotteryResult.DoesNotExist:
        return None, f"Chưa nhập kết quả cho đài {station_id} ngày {process_date}."

    pending_bets = Bet.objects.filter(
        date=process_date,
        station_id=station_id,
        status='PENDING'
    )

    if not pending_bets.exists():
        return f"Không có vé cược PENDING nào cho đài {station_id} ngày {process_date}.", None

    win_count = 0
    lose_count = 0

    try:
        with db_transaction.atomic():  # Dùng module 'db_transaction'
            for bet in pending_bets:
                winnings = Decimal('0.00')

                if bet.bet_type == 'DE':
                    if bet.number == result.de_number:
                        winnings = bet.amount * DE_RATE

                elif bet.bet_type == 'LO':
                    hits = result.lo_numbers.count(bet.number)
                    if hits > 0:
                        winnings = (bet.amount * LO_RATE) * hits

                if winnings > 0:
                    bet.status = 'WON'
                    bet.winnings = winnings
                    win_count += 1

                    # Lỗi 'wallet' for class 'CustomUser' mà bạn thấy
                    # là lỗi của linter, không phải lỗi code.
                    # 'bet.user.wallet' sẽ chạy đúng.
                    user_wallet = bet.user.wallet
                    user_wallet.balance += winnings
                    user_wallet.save()

                    # Dòng này bây giờ đã đúng, 'Transaction'
                    # được import từ 'wallet.models'
                    Transaction.objects.create(
                        wallet=user_wallet,
                        amount=winnings,
                        transaction_type='WIN',
                        description=f"Thắng cược {bet.station.name} {bet.get_bet_type_display()} số {bet.number}"
                    )
                else:
                    bet.status = 'LOST'
                    lose_count += 1

                bet.save()

    except Exception as e:
        return None, f"Gặp lỗi nghiêm trọng khi xử lý: {e}"

    success_msg = f"Hoàn tất cho {result.station.name} ngày {process_date}! Thắng: {win_count}, Thua: {lose_count}"
    return success_msg, None