from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .forms import RegisterForm, MissingPersonForm, FoundPersonForm, ProfileForm
from .models import UserProfile, MissingPerson, FoundPerson, Conversation, Message
from .face_utils import extract_embedding, serialize_embedding, deserialize_embedding
from .matching import find_top_matches
from .utils import get_or_create_conversation


@login_required
@require_POST
def delete_report_view(request, report_type, report_id):
    if report_type == "missing":
        report = get_object_or_404(MissingPerson, id=report_id, user=request.user)
    elif report_type == "found":
        report = get_object_or_404(FoundPerson, id=report_id, user=request.user)
    else:
        return JsonResponse({"status": "error", "message": "Invalid report type"}, status=400)

    report.delete()
    return JsonResponse({"status": "success"})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password1"])
        user.save()

        UserProfile.objects.create(
            user=user,
            full_name=form.cleaned_data["full_name"],
            mobile=form.cleaned_data["mobile"],
            city=form.cleaned_data["city"],
            pincode=form.cleaned_data["pincode"],
            district=form.cleaned_data["district"],
            state=form.cleaned_data["state"],
            country=form.cleaned_data["country"],
        )

        messages.success(request, "Registration successful. Please login.")
        return redirect("login")

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid credentials. Please check your username and password.")

    return render(request, "accounts/login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_view(request):
    user = request.user

    missing_reports_count = MissingPerson.objects.count()
    found_reports_count = FoundPerson.objects.count()
    total_reunited = MissingPerson.objects.filter(status="closed").count()

    context = {
        "missing_reports_count": missing_reports_count,
        "found_reports_count": found_reports_count,
        "total_reunited": total_reunited,
    }

    return render(request, "accounts/dashboard.html", context)


@login_required
def report_missing_view(request):
    form = MissingPersonForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()

        embedding = extract_embedding(obj.photo.path)
        if embedding is None:
            obj.delete()
            messages.error(
                request,
                "No clear face detected. Please upload a proper face image.",
            )
            return redirect("report_missing")

        obj.face_embedding = serialize_embedding(embedding)
        obj.save()

        # Check if this user already reported this person as FOUND
        user_found_entries = FoundPerson.objects.filter(user=request.user).exclude(face_embedding__isnull=True)
        duplicate_matches = find_top_matches(embedding, user_found_entries, threshold=0.8)
        if duplicate_matches and duplicate_matches[0][0] >= 0.8:
            obj.delete()
            messages.error(request, "You already have added a found person entry for this person.")
            return redirect("report_missing")

        found_people = FoundPerson.objects.filter(face_embedding__isnull=False).select_related("user")
        matches = find_top_matches(embedding, found_people)
        
        # Format matches for template: convert (score, obj, confidence) to (score, obj) tuples
        # keeping confidence info in the obj context
        formatted_matches = [
            (score, obj, confidence) 
            for score, obj, confidence in matches
        ]

        messages.success(request, "Report submitted successfully.")

        return render(
            request,
            "accounts/match_results.html",
            {
                "source": obj,
                "matches": formatted_matches,
                "mode": "missing_to_found",
            },
        )

    return render(request, "accounts/report_missing.html", {"form": form})


@login_required
def report_found_view(request):
    form = FoundPersonForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()

        embedding = extract_embedding(obj.photo.path)
        if embedding is None:
            obj.delete()
            messages.error(
                request,
                "No clear face detected. Please upload a proper face image.",
            )
            return redirect("report_found")

        obj.face_embedding = serialize_embedding(embedding)
        obj.save()

        # Check if this user already reported this person as MISSING
        user_missing_entries = MissingPerson.objects.filter(user=request.user).exclude(face_embedding__isnull=True)
        duplicate_matches = find_top_matches(embedding, user_missing_entries, threshold=0.8)
        if duplicate_matches and duplicate_matches[0][0] >= 0.8:
            obj.delete()
            messages.error(request, "You already have added a missing person entry for this person.")
            return redirect("report_found")

        missing_people = MissingPerson.objects.filter(
            face_embedding__isnull=False,
            status="open",
        ).select_related("user")

        matches = find_top_matches(embedding, missing_people)
        
        # Format matches for template
        formatted_matches = [
            (score, obj, confidence) 
            for score, obj, confidence in matches
        ]

        # Only auto-close if the best match has HIGH confidence (>0.75)
        # This is more reliable than just checking score
        if formatted_matches:
            best_score, best_match, best_confidence = formatted_matches[0]
            if best_confidence['level'] == 'HIGH':
                best_match.status = "closed"
                best_match.save()

        messages.success(request, "Report submitted successfully.")

        return render(
            request,
            "accounts/match_results.html",
            {
                "source": obj,
                "matches": formatted_matches,
                "mode": "found_to_missing",
            },
        )

    return render(request, "accounts/report_found.html", {"form": form})


@login_required
def view_found_view(request):
    found_qs = FoundPerson.objects.select_related("user").order_by("-reported_at")

    paginator = Paginator(found_qs, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "found_list": page_obj.object_list,
        "page_obj": page_obj,
    }

    return render(request, "accounts/view_found.html", context)


@login_required
def view_missing_view(request):
    missing_qs = MissingPerson.objects.select_related("user").order_by("-reported_at")

    paginator = Paginator(missing_qs, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "missing_list": page_obj.object_list,
        "page_obj": page_obj,
    }

    return render(request, "accounts/view_missing.html", context)


@login_required
def my_reports_view(request):
    missing = MissingPerson.objects.filter(user=request.user).select_related("user")
    found = FoundPerson.objects.filter(user=request.user).select_related("user")
    return render(
        request,
        "accounts/my_reports.html",
        {"missing": missing, "found": found},
    )


@login_required
def update_profile_view(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            profile = form.save(commit=False)

            username = form.cleaned_data.get("username")
            email = form.cleaned_data.get("email")
            if username:
                request.user.username = username
            if email:
                request.user.email = email
            request.user.save()

            profile.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("update_profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileForm(
            instance=user_profile,
            initial={
                "username": request.user.username,
                "email": request.user.email,
            },
        )

    return render(request, "accounts/update_profile.html", {"form": form})


@login_required
def inbox(request):
    conversations_data = []
    seen_users = set()

    conversations = (
        request.user.conversations
        .prefetch_related("participants", "messages")
        .order_by("-created_at")
    )

    for convo in conversations:
        other_user = convo.participants.exclude(id=request.user.id).first()

        if not other_user:
            continue

        if other_user.id in seen_users:
            continue

        seen_users.add(other_user.id)

        last_message = convo.messages.last()

        unread_count = convo.messages.filter(
            is_read=False,
        ).exclude(sender=request.user).count()

        conversations_data.append({
            "conversation": convo,
            "other_user": other_user,
            "last_message": last_message,
            "unread_count": unread_count,
        })

    return render(
        request,
        "accounts/inbox.html",
        {"conversations": conversations_data},
    )


@login_required
def open_chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    
    # Prevent users from messaging themselves
    if request.user.id == other_user.id:
        messages.error(request, "This report was added by yourself. You cannot initiate a chat with your own entry.")
        # Try to redirect back to match results if possible, otherwise dashboard
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect("dashboard")

    conversation = get_or_create_conversation(request.user, other_user)

    # Auto-send message logic
    source_id = request.GET.get('source_id')
    match_id = request.GET.get('match_id')
    mode = request.GET.get('mode')

    if source_id and match_id and mode:
        try:
            if mode == 'missing_to_found':
                source_obj = MissingPerson.objects.get(id=source_id)
                match_obj = FoundPerson.objects.get(id=match_id)
                
                # Update status to closed to increase reunited count as requested by user
                source_obj.status = 'closed'
                source_obj.save()
                
                location = match_obj.found_location
                person_name = source_obj.name
                photo = match_obj.photo
                msg_text = f"I found this person ({person_name}) at {location}."
            else:
                source_obj = FoundPerson.objects.get(id=source_id)
                match_obj = MissingPerson.objects.get(id=match_id)
                
                # Update status to closed to increase reunited count as requested by user
                match_obj.status = 'closed'
                match_obj.save()
                
                location = source_obj.found_location
                person_name = match_obj.name
                photo = source_obj.photo
                msg_text = f"I found this person ({person_name}) at {location}."

            if not Message.objects.filter(conversation=conversation, sender=request.user, content=msg_text).exists():
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=msg_text,
                    image=photo
                )
        except (MissingPerson.DoesNotExist, FoundPerson.DoesNotExist):
            pass

    conversation.messages.filter(
        sender=other_user,
        is_read=False,
    ).update(is_read=True)

    chat_messages = conversation.messages.all().order_by("timestamp")
    for msg in chat_messages:
        msg.ist_time = timezone.localtime(msg.timestamp).strftime("%I:%M %p")

    user_profile = UserProfile.objects.filter(user=request.user).first()
    logged_user_mobile = user_profile.mobile if user_profile else ""

    return render(
        request,
        "accounts/chat.html",
        {
            "conversation": conversation,
            "chat_messages": chat_messages,
            "other_user": other_user,
            "logged_user_mobile": logged_user_mobile,
        },
    )


@login_required
@require_POST
def send_message(request, conversation_id):
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user,
    )

    text = request.POST.get("message", "").strip()
    if text:
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=text,
        )

    other_user = conversation.participants.exclude(id=request.user.id).first()
    if other_user is None:
        return redirect("inbox")
    return redirect("open_chat", user_id=other_user.id)
