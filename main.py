import datetime
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
from module import user, problem, judge
import os, dotenv
import requests
import fastapi_cdn_host
import logging


dotenv.load_dotenv(verbose=True)
AGENT_ADDRESS = os.getenv("AGENT_ADDRESS")
if not AGENT_ADDRESS:
    raise Exception("AGENT_ADDRESS is not set")

app = FastAPI()
fastapi_cdn_host.patch_docs(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class NewUserResponse(BaseModel):
    user_id: str = Field(..., example="123e4567-e89b-12d3-a456-426614174000")

class UserStatusResponse(BaseModel):
    latest_score: int = Field(..., example=100)
    highest_score: int = Field(..., example=100)
    attempt: int = Field(..., example=1)
    registered: bool = Field(..., example=True)

class QuestionChoice(BaseModel):
    id: str = Field(..., example="8bf738ef-5251-4678-bb7c-7b159d75e16c")
    text: str = Field(..., example="What is the capital of France?")
    options: List[str] = Field(..., example=["Paris", "London", "Berlin", "Madrid"])
    type: Literal["choice"]

class QuestionText(BaseModel):
    id: str = Field(..., example="f15db9ba-f146-4a75-ac19-0df89baf5ca5")
    text: str = Field(..., example="What is 2 + 2?")
    type: Literal["text"]
    placeholder: Optional[str] = Field(None, example="some help text")

Question = Union[QuestionChoice, QuestionText]

class QuestionsResponse(BaseModel):
    questions: List[Question]

class Answer(BaseModel):
    id: str
    answer: Union[int, str]

class SubmitRequest(BaseModel):
    user_id: str
    answers: List[Answer]

class SubmitResponse(BaseModel):
    score: int
    result: bool

class RegisterRequest(BaseModel):
    user_id: str
    name: str
    student_id: str
    college: str
    phone: str
    wechat: str
class ProblemRequest(BaseModel):
    text: str
@app.get("/user/new", response_model=NewUserResponse)
def create_user():
    new_user_id = user.create_user()
    return NewUserResponse(user_id=new_user_id)

@app.get("/user/status", response_model=UserStatusResponse)
def get_user_status(user_id: str = Query(...)):
    user_status = user.get_info(user_id)
    if user_status is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserStatusResponse(**user_status)

@app.post("/problem/submit")
def submit_problem(payload: str = Body(..., media_type="text/plain")):
    response = problem.submit_problem(payload)
    if response is False:
        raise HTTPException(status_code=500, detail="Failed to submit problem")
    return response

@app.get("/questions", response_model=QuestionsResponse)
def get_questions(user_id: str = Query(...)):
    questions = problem.get_problem(user_id)
    if questions is None:
        raise HTTPException(status_code=404, detail="User not found")
    return QuestionsResponse(questions=questions)


@app.post("/submit", response_model=SubmitResponse)
def submit_answers(payload: SubmitRequest):
    status = user.get_info(payload.user_id)
    if status is None:
        raise HTTPException(status_code=404, detail="User not found")
    scores = 0
    # log to file(./data/logs/{time}-{user_id}.log)
    time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    file_path = f"./data/logs/{time}-{payload.user_id}.log"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    logging.basicConfig(filename=file_path, level=logging.INFO)
    LOGGER = logging.getLogger(__name__)
    for answer in payload.answers:
        [score, reason] = judge.judge(answer.id, answer.answer)
        print(score, reason)
        LOGGER.info(f"Problem ID: {answer.id}, Score: {score}, Answer: {answer.answer}, Reason: {reason}")
        scores += score
    print(scores)
    user.update_info(payload.user_id, {
        "latest_score": scores,
        "highest_score": max(scores, status["highest_score"]),
        "attempt": status["attempt"] + 1
    })
    return SubmitResponse(score=scores, result=scores > 75)

@app.post("/register")
def register_user(payload: RegisterRequest):
    # 注册用户信息
    status = user.update_info(payload.user_id, {
        "name": payload.name,
        "phone": payload.phone,
        "wechat": payload.wechat,
        "department": payload.college,
        "iaaa": payload.student_id,
        "registered": True
    })
    if not status:
        raise HTTPException(status_code=404, detail="User not found")
    agent_url = AGENT_ADDRESS if AGENT_ADDRESS.startswith("http") else f"http://{AGENT_ADDRESS}"
    response = requests.get(f"{agent_url}/add?id={payload.wechat}&score={status['highest_score']}")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    user.update_info(payload.user_id, {"registered": True})
    return {"status": response.text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)