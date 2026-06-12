import argparse
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT          = Path(__file__).resolve().parent
VENV          = ROOT / ".venv"
IS_WIN        = os.name == "nt"
VENV_PYTHON   = VENV / "Scripts" / "python.exe" if IS_WIN else VENV / "bin" / "python"
GLOBAL_PYTHON = sys.executable

# Credenciales actuales del proyecto (precargadas para no tener que escribirlas)
# Repositorio privado — las claves reales están embebidas para instalación inmediata
DEFAULTS = {
    "db_name":             "movilidata_os",
    "db_user":             "root",
    "db_password":         "root",
    "db_host":             "localhost",
    "db_port":             "3306",
    "tomtom_api_key":      "4QGe4wDA4P0XKAHag1JoK6nJdq9iwUo9",
    "groq_api_key":        "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",
    "groq_model":          "llama-3.3-70b-versatile",
    "movibot_rate_limit":  "100",
    "movibot_rate_window": "60",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def run(command, **kwargs):
    print(f"\n==> {' '.join(map(str, command))}")
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def require(command, message):
    if shutil.which(command) is None:
        raise SystemExit(f"\n[ERROR] {message}")


def banner(text):
    bar = "─" * (len(text) + 4)
    print(f"\n┌{bar}┐\n│  {text}  │\n└{bar}┘")


# ── Instalación de dependencias ──────────────────────────────────────────────

def create_venv_standard():
    """Crea el entorno virtual usando el módulo nativo venv."""
    if VENV.exists():
        print(f"\n==> .venv ya existe, omitiendo creación")
        return
    print(f"\n==> Creando entorno virtual estándar en {VENV}...")
    subprocess.run([GLOBAL_PYTHON, "-m", "venv", str(VENV)], check=True)


def install_deps_global():
    """Instala dependencias en el Python global del sistema."""
    banner("Instalando dependencias globalmente")
    subprocess.run(
        [
            GLOBAL_PYTHON, "-m", "pip", "install",
            "-r", "requirements.txt",
            "--prefer-binary",
            "--no-compile",
        ],
        cwd=ROOT, check=True,
    )


def install_deps_standard():
    """
    Instala todas las dependencias usando pip nativo en el entorno virtual.
    Usa --prefer-binary para acelerar la descarga usando wheels precompilados.
    """
    banner("Instalando dependencias en el entorno virtual")
    print("   Modo rápido activo: buscando wheels precompilados...")
    
    # Primero aseguramos que pip esté actualizado en el entorno virtual
    subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "-q"],
        cwd=ROOT, check=False
    )
    
    # Instalación de los requerimientos del proyecto
    subprocess.run(
        [
            str(VENV_PYTHON), "-m", "pip", "install",
            "-r", "requirements.txt",
            "--prefer-binary",
            "--no-compile",
        ],
        cwd=ROOT, check=True,
    )


# ── .env ─────────────────────────────────────────────────────────────────────

def read_existing_env():
    """Lee el .env actual y devuelve un dict con sus valores."""
    env_file = ROOT / ".env"
    values = {}
    if not env_file.exists():
        return values
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip()
    return values


def generate_secret_key():
    result = subprocess.run(
        [
            str(VENV_PYTHON), "-c",
            "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
        ],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def write_env(args):
    """
    Escribe el .env preservando la SECRET_KEY existente si ya hay una,
    y manteniendo todas las credenciales actuales del proyecto.
    """
    existing = read_existing_env()

    # Preservar SECRET_KEY si ya existe, si no generar una nueva
    secret = existing.get("SECRET_KEY") or generate_secret_key()

    content = f"""# MoviliData OS — generado por install.py
SECRET_KEY={secret}
DEBUG=True

# Base de datos
DB_NAME={args.db_name}
DB_USER={args.db_user}
DB_PASSWORD={args.db_password}
DB_HOST={args.db_host}
DB_PORT={args.db_port}

# APIs externas
TOMTOM_API_KEY={args.tomtom_api_key}
GROQ_API_KEY={args.groq_api_key}
GROQ_MODEL={args.groq_model}

# Rate limit para Movibot
MOVIBOT_RATE_LIMIT={args.movibot_rate_limit}
MOVIBOT_RATE_WINDOW={args.movibot_rate_window}
"""
    (ROOT / ".env").write_text(content, encoding="utf-8")
    print(f"\n==> .env escrito con credenciales actuales")
    print(f"    DB:     {args.db_user}@{args.db_host}:{args.db_port}/{args.db_name}")
    print(f"    Groq:   {args.groq_model}")


# ── MySQL ─────────────────────────────────────────────────────────────────────

def mysql_cmd(args):
    cmd = ["mysql", "-h", args.db_host, "-P", args.db_port, "-u", args.db_user]
    if args.db_password:
        cmd.append(f"-p{args.db_password}")
    return cmd


def mysql_create_db(args):
    sql = f"CREATE DATABASE IF NOT EXISTS {args.db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    print(f"\n==> Creando base de datos '{args.db_name}' si no existe")
    subprocess.run(mysql_cmd(args), input=sql.encode(), cwd=ROOT, check=True)


def mysql_drop_tables(args):
    print("\n==> Limpiando tablas existentes para migrate limpio")
    drop_sql = (
        "SET FOREIGN_KEY_CHECKS = 0;\n"
        "SET SESSION group_concat_max_len = 65535;\n"
        "SELECT IFNULL(CONCAT('DROP TABLE IF EXISTS ', GROUP_CONCAT('`', TABLE_NAME, '`')), 'SELECT 1') INTO @dropper\n"
        "  FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE();\n"
        "PREPARE stmt FROM @dropper; EXECUTE stmt; DEALLOCATE PREPARE stmt;\n"
        "SET FOREIGN_KEY_CHECKS = 1;\n"
    )
    subprocess.run(mysql_cmd(args) + [args.db_name], input=drop_sql.encode(), cwd=ROOT, check=False)


def mysql_load(args):
    sql_file = ROOT / "database" / "movilidata_os.sql"
    if not sql_file.exists():
        raise SystemExit(f"\n[ERROR] No existe {sql_file}")
    print("\n==> Cargando datos iniciales desde database/movilidata_os.sql")
    with sql_file.open("rb") as f:
        subprocess.run(mysql_cmd(args) + [args.db_name], cwd=ROOT, stdin=f, check=True)


# ── Django ────────────────────────────────────────────────────────────────────

def create_admin():
    script = (
        "from django.contrib.auth.models import User\n"
        "from apps.users.models import UserProfile\n"
        "if not User.objects.filter(username='admin').exists():\n"
        "    u = User.objects.create_superuser('admin','admin@movilidata.local','admin123')\n"
        "    UserProfile.objects.create(user_id=u.id, role='Administrador', organization='MoviliData OS')\n"
        "    print('Superusuario admin creado')\n"
        "else:\n"
        "    print('Superusuario admin ya existe')\n"
    )
    run([str(VENV_PYTHON), "manage.py", "shell"], input=script.encode())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Instalador nativo de MoviliData OS",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Credenciales con valores actuales precargados como defaults
    parser.add_argument("--db-name",             default=DEFAULTS["db_name"])
    parser.add_argument("--db-user",             default=DEFAULTS["db_user"])
    parser.add_argument("--db-password",         default=DEFAULTS["db_password"])
    parser.add_argument("--db-host",             default=DEFAULTS["db_host"])
    parser.add_argument("--db-port",             default=DEFAULTS["db_port"])
    parser.add_argument("--tomtom-api-key",      default=DEFAULTS["tomtom_api_key"])
    parser.add_argument("--groq-api-key",        default=DEFAULTS["groq_api_key"])
    parser.add_argument("--groq-model",          default=DEFAULTS["groq_model"])
    parser.add_argument("--movibot-rate-limit",  default=DEFAULTS["movibot_rate_limit"])
    parser.add_argument("--movibot-rate-window", default=DEFAULTS["movibot_rate_window"])
    parser.add_argument("--no-runserver",    action="store_true", help="No lanzar el servidor al final")
    parser.add_argument("--skip-db",         action="store_true", help="Omitir pasos de base de datos")
    parser.add_argument("--skip-global",     action="store_true", help="Omitir instalación global de dependencias")
    args = parser.parse_args()

    banner("MoviliData OS — Instalador Nativo")

    # Verificación de requerimientos globales obligatorios
    require("mysql", "mysql no encontrado en PATH. Instala MySQL Server y agrégalo a tus variables de entorno.")

    # 0. Dependencias globales (opcional con --skip-global)
    if not args.skip_global:
        install_deps_global()

    # 1. Entorno virtual nativo
    create_venv_standard()

    # 2. Dependencias en el entorno virtual
    install_deps_standard()

    # 3. .env con las credenciales configuradas
    write_env(args)

    if not args.skip_db:
        # 4. Base de datos MySQL
        mysql_create_db(args)
        mysql_drop_tables(args)

        # 5. Migraciones de Django
        banner("Ejecutando migraciones Django")
        run([str(VENV_PYTHON), "manage.py", "migrate"])

        # 6. Carga de dump inicial de base de datos
        mysql_load(args)

        # 7. Creación de cuenta de administración por defecto
        create_admin()

    # 8. Verificación de integridad de Django
    banner("Verificación final")
    run([str(VENV_PYTHON), "manage.py", "check"])

    url = "http://127.0.0.1:8000/"
    banner("Instalación completada")
    print(f"  URL:       {url}")
    print(f"  Usuario:   admin")
    print(f"  Password:  admin123")
    print(f"  Modelo:    {args.groq_model}")
    print()

    if not args.no_runserver:
        webbrowser.open(url)
        run([str(VENV_PYTHON), "manage.py", "runserver", "127.0.0.1:8000"])


if __name__ == "__main__":
    main() 