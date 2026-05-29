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
PYTHON = VENV / "Scripts" / "python.exe" if os.name == "nt" else VENV / "bin" / "python"


def run(command, **kwargs):
    print(f"\n==> {' '.join(map(str, command))}")
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)


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


def mysql_load(args):
    sql_file = ROOT / "database" / "movilidata_os.sql"
    if not sql_file.exists():
        raise SystemExit(f"No existe {sql_file}")

    command = ["mysql", "-h", args.db_host, "-P", args.db_port, "-u", args.db_user]
    if args.db_password:
        command.append(f"-p{args.db_password}")

    print("\n==> Cargando database/movilidata_os.sql en MySQL")
    with sql_file.open("rb") as sql:
        subprocess.run(command, cwd=ROOT, stdin=sql, check=True)


def create_admin():
    code = (
        "from django.contrib.auth.models import User; "
        "User.objects.filter(username='admin').exists() or "
        "User.objects.create_superuser('admin','admin@movilidata.local','admin123')"
    )
    run([str(PYTHON), "manage.py", "shell", "-c", code])


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

    require("mysql", "No se encontro mysql en PATH. Instala MySQL Server/MySQL Workbench y agrega mysql.exe al PATH.")

    if not VENV.exists():
        run([sys.executable, "-m", "venv", str(VENV)])

    run([str(PYTHON), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(PYTHON), "-m", "pip", "install", "-r", "requirements.txt"])

    print("\n==> Generando .env")
    write_env(args)

    mysql_load(args)
    run([str(PYTHON), "manage.py", "migrate"])
    create_admin()
    run([str(PYTHON), "manage.py", "check"])

    url = "http://127.0.0.1:8000/"
    print("\nMoviliData OS instalado correctamente")
    print(f"URL: {url}")
    print("Usuario: admin")
    print("Contrasena: admin123")

    if not args.no_runserver:
        webbrowser.open(url)
        run([str(PYTHON), "manage.py", "runserver", "127.0.0.1:8000"])


if __name__ == "__main__":
    main()
