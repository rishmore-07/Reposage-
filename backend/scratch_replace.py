import os
from pathlib import Path

backend_dir = Path("c:/Users/Nikita More/OneDrive/Desktop/signlanguage/backend")

replacements = {
    "from app.models.user": "from app.modules.users.models",
    "from app.models.repository": "from app.modules.repositories.models",
    "from app.models.organization": "from app.modules.organizations.models",
    "from app.models.api_key": "from app.modules.api_keys.models",
    "from app.models.notification": "from app.modules.notifications.models",
    "from app.models.base": "from app.db.mixins",
    
    "from app.schemas.auth": "from app.modules.auth.schemas",
    "from app.schemas.user": "from app.modules.users.schemas",
    "from app.schemas.repository": "from app.modules.repositories.schemas",
    
    "from app.repositories.base_repository": "from app.db.repository",
    "from app.repositories.user_repository": "from app.modules.users.repository",
    "from app.repositories.repository_repository": "from app.modules.repositories.repository",
    
    "from app.services.auth_service": "from app.modules.auth.service",
    "from app.services.repository_service": "from app.modules.repositories.service",
    
    "from app.api.v1.auth.router": "from app.modules.auth.router",
    "from app.api.v1.users.router": "from app.modules.users.router",
    "from app.api.v1.repositories.router": "from app.modules.repositories.router",
}

for folder in ["app", "tests", "alembic"]:
    folder_path = backend_dir / folder
    if not folder_path.exists():
        continue
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                new_content = content
                for old, new in replacements.items():
                    new_content = new_content.replace(old, new)
                    
                if new_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"Updated {filepath}")

print("Import replacement complete.")
