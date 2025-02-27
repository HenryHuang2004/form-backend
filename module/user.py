import uuid
import json
import os
from filelock import FileLock

def create_user():
    user_info = {
        "user_id": str(uuid.uuid4()),
        "name": "",
        "wechat": "",
        "phone": "",
        "department": "",
        "iaaa": "",
        "highest_score": 0,
        "attempt": 0,
        "latest_score": 0,
        "registered": False,
        "last_used_problem_ids": []
    }
    file_path = f"./data/users/user{user_info['user_id']}.json"
    lock_path = f"./data/users/tmp/user{user_info['user_id']}.json" + ".lock"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with FileLock(lock_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_info, f, ensure_ascii=False, indent=4)
    return user_info["user_id"]

def get_info(user_id):
    file_path = f"./data/users/user{user_id}.json"
    lock_path = f"./data/users/tmp/user{user_id}.json" + ".lock"
    if not os.path.exists(file_path):
        return None
    with FileLock(lock_path):
        with open(file_path, "r", encoding="utf-8") as f:
            user_info = json.load(f)
            return {
                "latest_score": user_info["latest_score"],
                "highest_score": user_info["highest_score"],
                "attempt": user_info["attempt"],
                "registered": user_info["registered"]
            }

def update_info(user_id, user_info):
    file_path = f"./data/users/user{user_id}.json"
    lock_path = f"./data/users/tmp/user{user_id}.json" + ".lock"
    with FileLock(lock_path):
        with open(file_path, "r", encoding="utf-8") as f:
            user_info_old = json.load(f)
        if not user_info_old:
            return False
        user_info_new = user_info_old.copy()
        user_info_new.update(user_info)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_info_new, f, ensure_ascii=False, indent=4)
        return True
# tiny test
if __name__ == "__main__":
    uuid = create_user()
    print(uuid)
    update_info(uuid, {"name": "test", "phone": "12345678901"})
    print(get_info(uuid))