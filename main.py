import io
import contextlib
import traceback
import sys
import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str

client = OpenAI(
    api_key=os.environ["AIPIPE_API_KEY"],
    base_url="https://aipipe.org/openai/v1",
)

def analyze_error_with_ai(code, traceback_text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    'Identify the line numbers causing the Python error. '
                    'Return JSON only, such as {"error": [3]}.'
                ),
            },
            {
                "role": "user",
                "content": f"Code:\n{code}\n\nTraceback:\n{traceback_text}",
            },
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content).get("error", [])

def execute_code(code):
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(compile(code, "<user_code>", "exec"), {})
        return {"result": output.getvalue(), "error": []}
    except Exception:
        error_text = traceback.format_exc()
        try:
            lines = analyze_error_with_ai(code, error_text)
        except Exception:
            tb = traceback.extract_tb(sys.exc_info()[2])
            lines = [
                frame.lineno for frame in tb
                if frame.filename == "<user_code>"
            ]
        return {"result": error_text, "error": lines}

@app.get("/")
def home():
    return {"message": "Code Interpreter API is running"}

@app.post("/code-interpreter")
def code_interpreter(request: CodeRequest):
    return execute_code(request.code)
