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
    # Upgrade pip silenciosamente (sin output innecesario)
    subprocess.run(
        [str(python), "-m", "pip", "install", "--upgrade", "pip", "-q"],
        cwd=ROOT, check=True,
    )
    # Instalar dependencias con uv si está disponible, si no usar pip con flags de velocidad
    uv = shutil.which("uv")
    if uv:
        print("\n==> Instalando dependencias con uv (modo rapido)")
        subprocess.run(
            [uv, "pip", "install", "-r", "requirements.txt", "--python", str(python)],
            cwd=ROOT, check=True,
        )
    else:
        print("\n==> Instalando dependencias con pip")
        subprocess.run(
            [
                str(python), "-m", "pip", "install",
                "-r", "requirements.txt",
                "--prefer-binary",   # usa wheels precompilados, evita compilar C
                "-q",                # sin output verboso
            ],
            cwd=ROOT, check=True,
        )


def require(command, message):
    if shutil.which(command) is None:
        raise SystemExit(message)


def write_env(args):
    secret = f"django-secret-key-local-{uuid.uuid4().hex}"
    content = f"""SECRET_KEY={secret}
DEBUG=True

DB_NAME={args.db_name}
DB_USER={args.db_user}
DB_PASSWORD={args.db_password}
DB_HOST={args.db_host}
DB_PORT={args.db_port}

TOMTOM_API_KEY={args.tomtom_api_key}
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
    parser.add_argument("--tomtom-api-key", default="")
    parser.add_argument("--no-runserver", action="store_true")
    args = parser.parse_args()

    require("mysql", "No se encontro mysql en PATH. Instala MySQL Server y agrega mysql.exe al PATH.")

    # 1. Entorno virtual
    if not VENV.exists():
        run([str(GLOBAL_PYTHON), "-m", "venv", str(VENV)])

    # 2. Dependencias (solo en el venv, una sola vez)
    print("\n==> Instalando dependencias en .venv")
    pip_install(VENV_PYTHON)

    # 3. Archivo .env
    print("\n==> Generando .env")
    write_env(args)

    # 4. Crear BD vacia (sin tablas)
    mysql_create_db(args)

    # 5. Limpiar tablas Django previas (para evitar conflictos de schema)
    mysql_drop_django_tables(args)

    # 6. migrate: Django crea todas sus tablas desde cero
    run([str(VENV_PYTHON), "manage.py", "migrate"])

    # 7. Cargar SQL con datos iniciales (las tablas ya existen)
    mysql_load(args)

    # 8. Crear superusuario admin
    create_admin()

    # 9. Verificacion final
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
