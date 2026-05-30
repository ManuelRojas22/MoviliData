import argparse
import os
import shutil
import subprocess
import sys
import uuid
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / "Scripts" / "python.exe" if os.name == "nt" else VENV / "bin" / "python"
GLOBAL_PYTHON = sys.executable


def run(command, **kwargs):
    print(f"\n==> {' '.join(map(str, command))}")
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)

def pip_install(python):
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "-r", "requirements.txt"])


def require(command, message):
    if shutil.which(command) is None:
        raise SystemExit(message)


def write_env(args, python_path):
    result = subprocess.run(
        [str(python_path), "-c", "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"],
        capture_output=True, text=True, check=True,
    )
    secret = result.stdout.strip()

    content = f"""SECRET_KEY={secret}
DEBUG=True

DB_NAME={args.db_name}
DB_USER={args.db_user}
DB_PASSWORD={args.db_password}
DB_HOST={args.db_host}
DB_PORT={args.db_port}

TOMTOM_API_KEY={args.tomtom_api_key}
TOMTOM_SECRET_KEY={args.tomtom_secret_key}
"""
    (ROOT / ".env").write_text(content, encoding="utf-8")


def mysql_cmd(args):
    command = ["mysql", "-h", args.db_host, "-P", args.db_port, "-u", args.db_user]
    if args.db_password:
        command.append(f"-p{args.db_password}")
    return command


def mysql_create_db(args):
    """Paso 1: solo crea la base de datos si no existe."""
    sql = f"CREATE DATABASE IF NOT EXISTS {args.db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    print(f"\n==> Creando base de datos '{args.db_name}' si no existe")
    subprocess.run(
        mysql_cmd(args),
        input=sql.encode(),
        cwd=ROOT,
        check=True,
    )


def mysql_drop_django_tables(args):
    """Borra TODAS las tablas de la base de datos para que migrate las cree desde cero."""
    print("\n==> Eliminando todas las tablas existentes (para que Django las cree frescas)")
    drop_sql = (
        "SET FOREIGN_KEY_CHECKS = 0;\n"
        "SET SESSION group_concat_max_len = 65535;\n"
        "SELECT IFNULL(CONCAT('DROP TABLE IF EXISTS ', GROUP_CONCAT('`', TABLE_NAME, '`')), 'SELECT 1') INTO @dropper\n"
        "  FROM INFORMATION_SCHEMA.TABLES\n"
        "  WHERE TABLE_SCHEMA = DATABASE();\n"
        "PREPARE stmt FROM @dropper;\n"
        "EXECUTE stmt;\n"
        "DEALLOCATE PREPARE stmt;\n"
        "SET FOREIGN_KEY_CHECKS = 1;\n"
    )
    subprocess.run(
        mysql_cmd(args) + [args.db_name],
        input=drop_sql.encode(),
        cwd=ROOT,
        check=False,
    )


def mysql_load(args):
    """Paso 3: carga datos iniciales DESPUES de migrate."""
    sql_file = ROOT / "database" / "movilidata_os.sql"
    if not sql_file.exists():
        raise SystemExit(f"No existe {sql_file}")

    print("\n==> Cargando database/movilidata_os.sql en MySQL")
    with sql_file.open("rb") as sql:
        subprocess.run(
            mysql_cmd(args) + [args.db_name],
            cwd=ROOT,
            stdin=sql,
            check=True,
        )


def create_admin():
    script = (
        "from django.contrib.auth.models import User\n"
        "from apps.users.models import UserProfile\n"
        "if not User.objects.filter(username='admin').exists():\n"
        "    u = User.objects.create_superuser('admin','admin@movilidata.local','admin123')\n"
        "    UserProfile.objects.create(user_id=u.id, role='Administrador', organization='MoviliData OS')\n"
    )
    run([str(VENV_PYTHON), "manage.py", "shell"], input=script.encode())


def main():
    parser = argparse.ArgumentParser(description="Instalador automatico de MoviliData OS")
    parser.add_argument("--db-name", default="movilidata_os")
    parser.add_argument("--db-user", default="root")
    parser.add_argument("--db-password", default="root")
    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="3306")
    parser.add_argument("--tomtom-api-key", default="skP5QP3Pf59qpi19aeRyVtPhrMlhoiC3")
    parser.add_argument("--tomtom-secret-key", default="")
    parser.add_argument("--no-runserver", action="store_true")
    args = parser.parse_args()

    require("mysql", "No se encontro mysql en PATH. Instala MySQL Server y agrega mysql.exe al PATH.")

    # 1. Entorno virtual
    if not VENV.exists():
        run([str(GLOBAL_PYTHON), "-m", "venv", str(VENV)])

    # 2. Dependencias: dentro del venv y globalmente
    print("\n==> Instalando dependencias en .venv")
    pip_install(VENV_PYTHON)
    print("\n==> Instalando dependencias globalmente")
    pip_install(GLOBAL_PYTHON)

    # 2. Archivo .env
    print("\n==> Generando .env")
    write_env(args, VENV_PYTHON)

    # 3. Crear BD vacia (sin tablas)
    mysql_create_db(args)

    # 4. Limpiar tablas Django previas (para evitar conflictos de schema)
    mysql_drop_django_tables(args)

    # 5. migrate: Django crea todas sus tablas desde cero
    run([str(VENV_PYTHON), "manage.py", "migrate"])

    # 6. Cargar SQL con datos iniciales (las tablas ya existen)
    mysql_load(args)

    # 6. Crear superusuario admin
    create_admin()

    # 7. Verificacion final
    run([str(VENV_PYTHON), "manage.py", "check"])

    url = "http://127.0.0.1:8000/"
    print("\nMoviliData OS instalado correctamente")
    print(f"URL: {url}")
    print("Usuario: admin")
    print("Contrasena: admin123")

    if not args.no_runserver:
        webbrowser.open(url)
        run([str(VENV_PYTHON), "manage.py", "runserver", "127.0.0.1:8000"])


if __name__ == "__main__":
    main()
