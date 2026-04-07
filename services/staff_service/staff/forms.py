from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class StaffLoginForm(AuthenticationForm):
    username = forms.CharField(label="Staff username", max_length=150)
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput)


class StaffRegisterForm(forms.Form):
    username = forms.CharField(label="Username", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirm password", strip=False, widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Password confirmation does not match.")
        return cleaned_data


class ItemForm(forms.Form):
    ACTION_CHOICES = [
        ("create", "Create item"),
        ("update", "Update item"),
        ("delete", "Delete item"),
    ]
    SERVICE_CHOICES = [
        ("laptop", "Laptop service"),
        ("mobile", "Mobile service"),
        ("accessory", "Accessory service"),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES, initial="create")
    service = forms.ChoiceField(choices=SERVICE_CHOICES, initial="laptop")
    product_id = forms.IntegerField(required=False, min_value=1)
    name = forms.CharField(max_length=255, required=False)
    brand = forms.CharField(max_length=120, required=False)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    image_url = forms.URLField(required=False)
    price = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    stock = forms.IntegerField(min_value=0, required=False)

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        product_id = cleaned_data.get("product_id")

        if action in {"update", "delete"} and not product_id:
            raise forms.ValidationError("product_id is required for update/delete actions.")

        if action in {"create", "update"}:
            required_fields = ["name", "brand", "price", "stock"]
            missing = [field for field in required_fields if cleaned_data.get(field) in [None, ""]]
            if missing:
                raise forms.ValidationError("Please provide name, brand, price, and stock for create/update.")

        return cleaned_data


class _BaseItemMutationForm(forms.Form):
    SERVICE_CHOICES = [
        ("laptop", "Laptop service"),
        ("mobile", "Mobile service"),
        ("accessory", "Accessory service"),
    ]

    service = forms.ChoiceField(choices=SERVICE_CHOICES)
    name = forms.CharField(max_length=255)
    brand = forms.CharField(max_length=120)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    image_url = forms.URLField(required=False)
    price = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    stock = forms.IntegerField(min_value=0)


class CreateItemForm(_BaseItemMutationForm):
    pass


class UpdateItemForm(_BaseItemMutationForm):
    product_id = forms.IntegerField(min_value=1)


class DeleteItemForm(forms.Form):
    SERVICE_CHOICES = [
        ("laptop", "Laptop service"),
        ("mobile", "Mobile service"),
        ("accessory", "Accessory service"),
    ]

    service = forms.ChoiceField(choices=SERVICE_CHOICES)
    product_id = forms.IntegerField(min_value=1)
