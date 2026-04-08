import json
import hashlib
from functools import lru_cache

PERMISSIONS_FILE = "data/user_permissions.json"


@lru_cache()
def load_permissions():
    with open(PERMISSIONS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_user_permissions(user_id: str):
    permissions = load_permissions()

    users = permissions.get("users", {})

    user = users.get(user_id)

    if not user:
        return {
            "regions": [],
            "divisions": []
        }

    return {
        "regions": user.get("regions", []),
        "divisions": user.get("divisions", [])
    }
    
def generate_scope_hash(regions: list, divisions: list) -> str:
    # normalize (sort)
    normalized_regions = sorted(regions)
    normalized_divisions = sorted(divisions)

    # create consistent string
    scope_string = f"regions:{','.join(normalized_regions)}|divisions:{','.join(normalized_divisions)}"

    # generate SHA256 hash
    return hashlib.sha256(scope_string.encode("utf-8")).hexdigest()

