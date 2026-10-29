from django import forms
from .models import DepositRequest, WithdrawalRequest

class DepositRequestForm(forms.ModelForm):
    class Meta:
        model = DepositRequest
        fields = ['amount', 'transaction_code']
        labels = {
            'amount': 'Số tiền bạn đã chuyển',
            'transaction_code': 'Nội dung CK / Mã giao dịch'
        }
        widgets = {
            'amount': forms.NumberInput(attrs={'placeholder': 'Ví dụ: 500000', 'step': '10000'}),
            'transaction_code': forms.TextInput(attrs={'placeholder': 'Ví dụ: VCB 123456 Nguyễn Văn A'})
        }

# ... (Giữ nguyên các form khác) ...

class WithdrawalRequestForm(forms.ModelForm):
    class Meta:
        model = WithdrawalRequest
        # Thêm 3 trường mới vào 'fields'
        fields = ['amount', 'full_name_cccd', 'bank_name', 'account_number']
        labels = {
            'amount': 'Số tiền muốn rút',
            'full_name_cccd': 'Tên chủ tài khoản (trên CCCD)',
            'bank_name': 'Tên ngân hàng',
            'account_number': 'Số tài khoản',
        }
        widgets = {
            'amount': forms.NumberInput(attrs={'placeholder': 'Ví dụ: 500000', 'step': '10000'}),
        }

    # (Giữ nguyên hàm __init__ và clean_amount)
    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop('wallet', None) # Nhận ví từ view
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.wallet and amount > self.wallet.balance:
            raise forms.ValidationError(f"Số dư không đủ. Bạn chỉ có {self.wallet.balance}đ.")
        if amount <= 0:
            raise forms.ValidationError("Số tiền rút phải lớn hơn 0.")
        return amount