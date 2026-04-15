import re
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, MissingPerson, FoundPerson

# Maximum upload size: 5 MB
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]


def _validate_image(image):
    """Validate uploaded image file size and type."""
    if image.size > MAX_UPLOAD_SIZE:
        raise forms.ValidationError(
            "Image file too large. Maximum size is 5 MB."
        )
    if hasattr(image, "content_type") and image.content_type not in ALLOWED_IMAGE_TYPES:
        raise forms.ValidationError(
            "Unsupported image format. Please upload a JPEG or PNG file."
        )
    return image


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"}),
        label="Password",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password"}),
        label="Confirm Password",
    )

    full_name = forms.CharField()
    mobile = forms.CharField()
    city = forms.CharField()
    pincode = forms.CharField()
    district = forms.CharField()
    state = forms.CharField()
    country = forms.CharField()

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "This username is already taken. Please choose another."
            )
        return username

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return data


class MissingPersonForm(forms.ModelForm):
    class Meta:
        model = MissingPerson
        fields = ["name", "age", "gender", "last_seen_location", "description", "photo"]

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo:
            return _validate_image(photo)
        return photo


class FoundPersonForm(forms.ModelForm):
    class Meta:
        model = FoundPerson
        fields = ["name", "age_estimate", "found_location", "description", "photo"]

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo:
            return _validate_image(photo)
        return photo

    def clean_age_estimate(self):
        age = self.cleaned_data.get("age_estimate")
        if age in (None, ""):
            return None

        if isinstance(age, int):
            return age

        if isinstance(age, str):
            m = re.search(r"(\d{1,3})", age)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    return None
        return None


class ProfileForm(forms.ModelForm):
    username = forms.CharField(required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "mobile",
            "city",
            "district",
            "state",
            "country",
            "pincode",
        ]

    def save(self, commit=True):
        profile = super().save(commit=commit)
        return profile
