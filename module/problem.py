import sqlite3
import os, dotenv
import requests, json
from module import user
from uuid import uuid4
from filelock import FileLock
from openai import OpenAI
dotenv.load_dotenv(verbose=True)
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise Exception("API_KEY is not set")
url = os.getenv("ENDPOINT")
if not url:
    raise Exception("ENDPOINT is not set")

conn = sqlite3.connect('./data/db/problem.db', check_same_thread=False)
conn.execute('''
CREATE TABLE IF NOT EXISTS problems (
    uuid TEXT PRIMARY KEY NOT NULL,
    statement TEXT NOT NULL,
    type TEXT NOT NULL,
    options TEXT,
    answer TEXT NOT NULL
);
''')
client = OpenAI(
    api_key=API_KEY,
    base_url=url
)

    
def submit_problem(text):
    try:
        completion = client.chat.completions.create(
            model="qwen-max-2025-01-25",  # 此处以 deepseek-r1 为例，可按需更换模型名称。
            messages=[
                {"role": "system", "content": "将输入内容分割成题目后，直接返回 json 格式数据，不要出现'```json'。其中“problem”项为题面。“enum”为选项，以数组形式分割每个选项且删除答案标记，这个项目不是必需的。“answer”项为答案，如果题目是选择题，也就是说 enum 存在，那么答案确定且应当已提供，请直接使用给出的答案对应的选项。否则，如果题目没有提供答案，或者题目的答案不完整，且你得到的题目确实是一个问题，你必须自己生成一个对应的答案，保存在 answer 项中，不要超过 100 字。"},
                {"role": "user", "content": text}
            ],
            temperature=0.6,
            top_p=0.7,
            max_tokens=2000
        )
        content_str = completion.choices[0].message.content
        parsed = json.loads(content_str)
        problem = parsed.get("problem")
        enum_list = parsed.get("enum")
        answer = parsed.get("answer")
        # insert into db
        cursor = conn.cursor()
        uuid = str(uuid4())
        options = json.dumps(enum_list) if enum_list else None
        cursor.execute('''
            INSERT INTO problems (uuid, statement, type, options, answer)
            VALUES (?, ?, ?, ?, ?)
        ''', (uuid, problem, 'choice' if enum_list else 'text', options, answer))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(e)
        return False

def get_problem(user_id):
    file_path = f"./data/users/user{user_id}.json"
    lock_path = f"./data/users/tmp/user{user_id}.json" + ".lock"
    if not os.path.exists(file_path):
        return None
    cursor = conn.cursor()
    with FileLock(lock_path):
        with open(file_path, "r", encoding="utf-8") as f:
            user_info = json.load(f)
            last_used_problem_ids = user_info["last_used_problem_ids"]
            latest_score = user_info["latest_score"]
            if (not last_used_problem_ids) or (latest_score != 0):
                # get 10 random choice problems and 2 random text problems     
                cursor.execute('''
                    SELECT uuid FROM problems WHERE type = 'choice' ORDER BY RANDOM() LIMIT 7
                ''')
                choice_problems = cursor.fetchall()
                cursor.execute('''
                    SELECT uuid FROM problems WHERE type = 'text' ORDER BY RANDOM() LIMIT 2
                ''')
                text_problems = cursor.fetchall()
                # concat into one list
                choice_problems = [x[0] for x in choice_problems]
                text_problems = [x[0] for x in text_problems]
                last_used_problem_ids = choice_problems + text_problems
    print(last_used_problem_ids)
    if last_used_problem_ids != user_info["last_used_problem_ids"]:
        user.update_info(user_id, {"last_used_problem_ids": last_used_problem_ids, "latest_score": 0})
    problems = []
    for problem_id in last_used_problem_ids:
        cursor.execute('''
            SELECT statement, type, options FROM problems WHERE uuid = ?
        ''', (problem_id,))
        statement, type, options = cursor.fetchone()
        if type == 'choice':
            problems.append({
                "id": problem_id,
                "text": statement,
                "options": json.loads(options),
                "type": type
            })
        else:
            problems.append({
                "id": problem_id,
                "text": statement,
                "type": type,
                "placeholder": ""
            })
    cursor.close()
    return problems
    # here
# tiny test
if __name__ == "__main__":
    print(submit_problem("为什么想加入 Linux 俱乐部？"))