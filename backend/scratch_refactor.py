import os
import shutil
from pathlib import Path

backend_dir = Path("c:/Users/Nikita More/OneDrive/Desktop/signlanguage/backend")
app_dir = backend_dir / "app"
modules_dir = app_dir / "modules"

# Define modules to create
modules = ["auth", "users", "repositories", "organizations", "api_keys", "notifications"]
for module in modules:
    (modules_dir / module).mkdir(parents=True, exist_ok=True)
    (modules_dir / module / "__init__.py").touch()

# Mapping of old path -> new path
file_moves = {
    "app/schemas/auth.py": "app/modules/auth/schemas.py",
    "app/services/auth_service.py": "app/modules/auth/service.py",
    "app/api/v1/auth/router.py": "app/modules/auth/router.py",
    
    "app/models/user.py": "app/modules/users/models.py",
    "app/schemas/user.py": "app/modules/users/schemas.py",
    "app/repositories/user_repository.py": "app/modules/users/repository.py",
    "app/services/user_service.py": "app/modules/users/service.py",
    "app/api/v1/users/router.py": "app/modules/users/router.py",
    
    "app/models/repository.py": "app/modules/repositories/models.py",
    "app/schemas/repository.py": "app/modules/repositories/schemas.py",
    "app/repositories/repository_repository.py": "app/modules/repositories/repository.py",
    "app/services/repository_service.py": "app/modules/repositories/service.py",
    "app/api/v1/repositories/router.py": "app/modules/repositories/router.py",
    
    "app/models/organization.py": "app/modules/organizations/models.py",
    "app/models/api_key.py": "app/modules/api_keys/models.py",
    "app/models/notification.py": "app/modules/notifications/models.py",
    
    "app/models/base.py": "app/db/mixins.py",
    "app/repositories/base.py": "app/db/repository.py",
}

for old, new in file_moves.items():
    old_path = backend_dir / old
    new_path = backend_dir / new
    if old_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
        print(f"Moved {old} -> {new}")
    else:
        print(f"File not found: {old}")

print("Done moving files.")
