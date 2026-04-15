from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=15)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    def __str__(self):
        return self.full_name


class MissingPerson(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("matched", "Matched"),
        ("closed", "Closed"),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open", db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10)
    last_seen_location = models.CharField(max_length=200)
    description = models.TextField()
    photo = models.ImageField(upload_to="missing_photos/", blank=True, null=True)

    face_embedding = models.BinaryField(null=True, blank=True)

    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reported_at"]

    def __str__(self):
        return f"{self.name} (Missing – {self.get_status_display()})"


class FoundPerson(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("matched", "Matched"),
        ("closed", "Closed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open", db_index=True)
    age_estimate = models.PositiveIntegerField(null=True, blank=True)
    found_location = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to="found_photos/")

    face_embedding = models.BinaryField(null=True, blank=True)

    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reported_at"]

    def __str__(self):
        return f"{self.name} (Found – {self.get_status_display()})"


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation {self.id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to="chat_images/", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Message {self.id} in {self.conversation}"
