
import requests
import json
import os, dotenv
import sqlite3
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
def judge(problem_id, answer):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM problems WHERE uuid = ?', (problem_id,))
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return None
    problem = {
        "title": row[1],
        "answer": row[4],
        "output": answer
    }
    type = row[2]
    if type == 'choice':
        try:
            completion = client.chat.completions.create(
                model="qwen-max-2025-01-25",  # 此处以 deepseek-r1 为例，可按需更换模型名称。
                messages=[
                    {"role": "system", "content": "你是一个冷酷无情的老师，你会严苛地评判答案。你会得到含有 title answer output 三个部分的 json 数据，只有 output 和 answer 中所包含的字母完全一样才得分。完全一样（除了空白字符）则得100分，否则得0分。请注意，无论如何，你都只需要返回未字符串化的，只带有 score 项的 json 数据，一定不要出现 ```json 这样的数据，也不需要出现转义符。注意，score 需要携带引号。"},
                    {"role": "user", "content": json.dumps(problem)}
                ],
                max_tokens=20
            )
            content_str = completion.choices[0].message.content
            print(content_str)
            parsed = json.loads(content_str)
            score = parsed.get("score")
            score = int(score)
            reason = parsed.get("reason")
            print(type)
        # choice problem 10 each, text problem 15 each,total 100
            return (score * 10 // 100, reason)
        except Exception as e:
            return (0, str(e))
    else:
        try:
            completion = client.chat.completions.create(
                model="qwen-max-2025-01-25",  
                messages=[
                    {"role": "system", "content": "你是一个冷酷无情的老师，你会严苛地评判答案。你会得到含有 title answer output 三个部分的 json 数据，你需要根据这三个部分进行评分。满分为一百分，其中相关性指 output 与 title 的相关性，若要给分，请你引用 output 中的文字，并说出其与title 的联系，占 30 分；正确性，首先检查 title 中是否有开放题字样，若有，这部分请给满，否则，请检查 output 与 answer 的一致性，尤其注意，如果包含代码，需要逐字检查非空白字符是否相同，占 30 分；真诚度可从字数、语气等多个维度进行考量，占 40 分。请注意，无论如何，你都只需要返回未字符串化的，只带有 score 项的 json 数据，一定不要出现 ```json 这样的数据，也不需要出现转义符。注意，score 需要携带引号，同时返回一个 reason 字段，用于说明三个部分的得分情况，不超过100字。"},
                    {"role": "user", "content": json.dumps(problem)}
                ],
                max_tokens=1000
            )
            content_str = completion.choices[0].message.content
            print(content_str)
            parsed = json.loads(content_str)
            score = parsed.get("score")
            score = int(score)
            reason = parsed.get("reason")
            print(type)
        # choice problem 10 each, text problem 15 each,total 100
            return (score * 15 // 100, reason)
        except Exception as e:
            return (0, str(e))
# tiny test
if __name__ == "__main__":
    print(judge("dff7718f-492c-4a25-a276-ec6bb67a705e", "想和大佬交流，学习 Linux 知识，提升自己的能力"))