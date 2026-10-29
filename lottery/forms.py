from django import forms
from .models import Bet, LotteryStation
from django.utils import timezone
from django.db.models import Q
import datetime


# (Hàm này có thể cần di chuyển hoặc import tùy cấu trúc của bạn)
def get_local_now():
    try:
        return timezone.now().astimezone(timezone.get_current_timezone())
    except Exception:
        return timezone.now()


class BetForm(forms.Form):

    def __init__(self, *args, **kwargs):
        # View sẽ truyền vào 2 queryset: 1 cho hôm nay, 1 cho ngày mai
        stations_today = kwargs.pop('stations_today', LotteryStation.objects.none())
        stations_tomorrow = kwargs.pop('stations_tomorrow', LotteryStation.objects.none())

        super().__init__(*args, **kwargs)

        # Tạo các lựa chọn (choices) theo nhóm
        choices = []
        if stations_today.exists():
            choices.append(
                ('Hôm nay', [(s.id, s.name) for s in stations_today])
            )
        if stations_tomorrow.exists():
            choices.append(
                ('Ngày mai', [(s.id, s.name) for s in stations_tomorrow])
            )

        self.fields['station'].choices = choices

    # Sửa lại: Dùng ChoiceField thay vì ModelChoiceField để hỗ trợ nhóm
    station = forms.ChoiceField(
        choices=[],  # Khởi tạo rỗng, __init__ sẽ điền vào
        label="Chọn đài (và ngày cược)",
    )

    bet_type = forms.ChoiceField(
        choices=Bet.BET_TYPES,
        label="Loại cược"
    )

    number = forms.CharField(
        label="Các số cược (mỗi số 2 chữ số)",
        widget=forms.TextInput(attrs={'placeholder': 'Ví dụ: 15253534'})
    )

    amount = forms.DecimalField(
        label="Số tiền cược (cho mỗi số)",
        min_value=1000,
        widget=forms.NumberInput(attrs={'placeholder': 'Tối thiểu 1,000', 'step':'1000'})
    )

    def clean_number(self):
        # (Giữ nguyên logic clean_number cược nhiều số)
        raw_numbers = self.cleaned_data['number']
        normalized_string = raw_numbers.replace(" ", "").replace(",", "").replace("\n", "").replace(".", "")
        if not normalized_string:
            raise forms.ValidationError("Bạn chưa nhập số cược.")
        if not normalized_string.isdigit():
            raise forms.ValidationError("Chỉ được nhập số.")
        if len(normalized_string) % 2 != 0:
            raise forms.ValidationError("Chuỗi số phải có độ dài chẵn.")
        number_list = [normalized_string[i:i + 2] for i in range(0, len(normalized_string), 2)]
        unique_numbers = list(set(number_list))
        return unique_numbers


# --- Form Upload Ảnh Của Admin (Cũng cần sửa) ---
class ImageUploadForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Ngày của kết quả"
    )
    # ModelChoiceField là đúng ở đây
    station = forms.ModelChoiceField(
        queryset=LotteryStation.objects.all(),
        label="Chọn đài",
        empty_label=None
    )
    image = forms.ImageField(label="Ảnh chụp màn hình kết quả")