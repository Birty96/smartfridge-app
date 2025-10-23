import os
import sys
import subprocess
import shutil
from dotenv import dotenv_values

# --- Configuration ---
REQUIRED_ENV_VARS = [
    'SECRET_KEY',
    # Add other variables that MUST be set (and not placeholders)
    'MAIL_USERNAME',
    'MAIL_PASSWORD',
    'OPENROUTER_API_KEY' 
]

ENV_EXAMPLE_FILE = '.env.example'
ENV_FILE = '.env'
REQUIREMENTS_FILE = 'requirements.txt'
MIGRATIONS_DIR = 'migrations'

# --- Helper Functions ---
def run_command(command, check=True, capture_output=False, text=True, shell=False, cwd=None):
    """Runs a command using subprocess and handles errors."""
    print(f"\n>> Running: {' '.join(command) if isinstance(command, list) else command}")
    try:
        result = subprocess.run(
            command, 
            check=check, 
            capture_output=capture_output, 
            text=text, 
            shell=shell, # Be cautious with shell=True
            cwd=cwd
        )
        if capture_output:
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(command) if isinstance(command, list) else command}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        if e.output:
            print(f"Output:\n{e.output}", file=sys.stderr)
        if e.stderr:
            print(f"Stderr:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Command not found ('{command[0] if isinstance(command, list) else command.split()[0]}'). Make sure it's installed and in your PATH.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while running {' '.join(command) if isinstance(command, list) else command}: {e}", file=sys.stderr)
        sys.exit(1)

def check_env_vars():
    """Checks if required environment variables are set and not placeholders."""
    print(f"\n>> Checking {ENV_FILE} for required variables...")
    if not os.path.exists(ENV_FILE):
        print(f"Error: {ENV_FILE} not found.", file=sys.stderr)
        print(f"Please copy {ENV_EXAMPLE_FILE} to {ENV_FILE} and configure it:", file=sys.stderr)
        print(f"  cp {ENV_EXAMPLE_FILE} {ENV_FILE}", file=sys.stderr)
        print(f"Then generate a secure SECRET_KEY:", file=sys.stderr)
        print(f"  python -c \"import secrets; print('SECRET_KEY=' + secrets.token_hex(32))\"", file=sys.stderr)
        sys.exit(1)
        
    config = dotenv_values(ENV_FILE)
    missing_or_placeholder = []
    
    # Load placeholder values from .env.example for comparison
    placeholders = {}
    if os.path.exists(ENV_EXAMPLE_FILE):
        placeholders = dotenv_values(ENV_EXAMPLE_FILE)
        
    for var in REQUIRED_ENV_VARS:
        value = config.get(var)
        placeholder_value = placeholders.get(var)
        if not value: # Variable is missing or empty
            if var == 'SECRET_KEY':
                missing_or_placeholder.append(f"- {var} (CRITICAL: Missing or empty - generate with: python -c \"import secrets; print(secrets.token_hex(32))\")")
            else:
                missing_or_placeholder.append(f"- {var} (Missing or empty)")
        elif placeholder_value and value == placeholder_value: # Variable has the placeholder value
            if var == 'SECRET_KEY':
                missing_or_placeholder.append(f"- {var} (CRITICAL: Still has placeholder value - generate with: python -c \"import secrets; print(secrets.token_hex(32))\")")
            else:
                missing_or_placeholder.append(f"- {var} (Still has placeholder value: '{value}')")
        elif var == 'SECRET_KEY' and (value == 'you-will-never-guess' or len(value) < 32): # Specific checks for secret key
             missing_or_placeholder.append(f"- {var} (CRITICAL: Insecure value - must be at least 32 characters and cryptographically secure)")
            
    if missing_or_placeholder:
        print(f"Error: Required settings missing or using placeholder values in {ENV_FILE}:", file=sys.stderr)
        for item in missing_or_placeholder:
            print(item, file=sys.stderr)
        print(f"\nPlease edit {ENV_FILE} and provide valid values before running the application.", file=sys.stderr)
        print(f"For SECRET_KEY, run: python -c \"import secrets; print(secrets.token_hex(32))\"", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"OK: Essential variables seem to be set in {ENV_FILE}.")

# --- Main Script --- #
def main():
    print("--- FridgeApp Setup & Run Script ---")
    print("Recommendation: Run this script within a Python virtual environment.")
    print("Example: ")
    print("  python -m venv venv")
    if os.name == 'nt': # Windows
        print("  .\\venv\\Scripts\\activate")
    else: # Linux/macOS
        print("  source venv/bin/activate")
    print("  python setup_and_run.py")

    # 1. Install requirements
    print(f"\n>> Installing dependencies from {REQUIREMENTS_FILE}...")
    run_command([sys.executable, '-m', 'pip', 'install', '-r', REQUIREMENTS_FILE])

    # 2. Check/Create .env file
    if not os.path.exists(ENV_FILE):
        print(f"\n>> {ENV_FILE} not found. Copying from {ENV_EXAMPLE_FILE}...")
        try:
            shutil.copyfile(ENV_EXAMPLE_FILE, ENV_FILE)
            print(f"OK: {ENV_FILE} created.")
            print(f"IMPORTANT: Please review and edit {ENV_FILE} with your actual secrets (SECRET_KEY, Mail credentials, API keys) NOW, then re-run this script.")
            sys.exit(0) # Exit so user can edit the file
        except FileNotFoundError:
            print(f"Error: {ENV_EXAMPLE_FILE} not found. Cannot create {ENV_FILE}.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error copying {ENV_EXAMPLE_FILE} to {ENV_FILE}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"\n>> Found existing {ENV_FILE}.")

    # 3. Validate .env contents
    check_env_vars()

    # 4. Database Migrations
    # Use sys.executable to ensure we use the python/flask from the current env
    flask_cmd = [sys.executable, '-m', 'flask']

    if not os.path.exists(MIGRATIONS_DIR):
        print(f"\n>> Initializing database migrations directory ({MIGRATIONS_DIR})...")
        # Don't check=True, as it might fail if already initialized but dir deleted
        run_command(flask_cmd + ['db', 'init'], check=False)
    else:
        print(f"\n>> Migrations directory ({MIGRATIONS_DIR}) already exists.")

    print("\n>> Creating database migration...")
    # Run migrate, capture output to check if changes were detected
    migrate_result = run_command(flask_cmd + ['db', 'migrate', '-m', '"Setup migration"'], check=False, capture_output=True)
    if migrate_result.returncode != 0 and "No changes detected" not in migrate_result.stdout and "No changes detected" not in migrate_result.stderr:
         print("Error running flask db migrate. Check output above.", file=sys.stderr)
         sys.exit(1)
    elif "No changes detected" in migrate_result.stdout or "No changes detected" in migrate_result.stderr:
        print("OK: No database changes detected for migration.")
    else:
        print("OK: Migration created.")

    print("\n>> Applying database migrations...")
    run_command(flask_cmd + ['db', 'upgrade'])
    print("OK: Database migrations applied.")

    # 5. Remind about Admin User
    print("\n--- Admin User Check ---")
    print("If this is your first time running the setup, you may need to create an admin user.")
    print("Open a NEW terminal window/tab (keep this one running the app), activate the virtual environment, and run:")
    print(f"  flask create-admin <your_username> <your_email@example.com>")
    print("It will prompt you for a password.")

    # 6. Start Application with Gunicorn
    print("\n--- Starting FridgeApp using Gunicorn --- ")
    print("NOTE: This is better than the dev server, but lacks Nginx.")
    print("Access via http://localhost:5000 or http://192.168.1.100:5000 (if port forwarded to 5000)")
    print("(Press CTRL+C to stop)...")
    # Use sys.executable path for gunicorn if installed in venv
    gunicorn_path = os.path.join(os.path.dirname(sys.executable), 'gunicorn')
    if os.name == 'nt': # Add .exe for Windows
        gunicorn_path += '.exe'
        
    # Bind to 0.0.0.0 to be accessible on the local network (192.168.1.100)
    # Using port 5000 as an example. Nginx would normally handle ports 80/443.
    run_command([gunicorn_path, '--bind', '0.0.0.0:5000', '--workers', '3', 'run:app'])

    # --- Create necessary directories if they don't exist --- #
    if not os.path.exists(app.config['SESSION_FILE_DIR']):
        os.makedirs(app.config['SESSION_FILE_DIR'])

    # Create upload directories for team documents
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'team_documents')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    return app

if __name__ == '__main__':
    main() 