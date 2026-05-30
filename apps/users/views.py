from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from .models import UserProfile


def ensure_demo_superuser():
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@movilidata.local", "admin123")


def login_view(request):
    try:
        ensure_demo_superuser()
    except Exception:
        pass
    error = None
    prefilled_username = request.GET.get("username", "")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            if not user.is_active:
                error = "Cuenta desactivada. Contacta al administrador."
            else:
                login(request, user)
                messages.success(request, f"Bienvenido de nuevo, {user.username}.")
                return redirect("dashboard")
        elif User.objects.filter(username=username).exists():
            error = "Contrasena incorrecta."
        elif User.objects.filter(email=username).exists():
            error = "Usa tu nombre de usuario, no tu correo."
        else:
            error = "El usuario no existe. ¿Quieres registrarte?"
    return render(request, "users/login.html", {"error": error, "prefilled_username": prefilled_username})


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        organization = request.POST.get("organization", "MoviliData OS").strip() or "MoviliData OS"
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        if not username or not email or not password:
            messages.error(request, "Completa todos los campos obligatorios.")
        elif password != password_confirm:
            messages.error(request, "Las contrasenas no coinciden.")
        elif len(password) < 6:
            messages.error(request, "La contrasena debe tener minimo 6 caracteres.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Ese usuario ya existe.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Ese correo ya esta registrado.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            UserProfile.objects.create(user_id=user.id, organization=organization, role="Usuario registrado")
            messages.success(request, "Cuenta creada exitosamente. Ahora puedes iniciar sesion.")
            return redirect(f"/users/login/?username={username}")
    return render(request, "users/register.html")


def logout_view(request):
    logout(request)
    return redirect("landing")


@login_required
def profile(request):
    return render(request, "users/profile.html")
