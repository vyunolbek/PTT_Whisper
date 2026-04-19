import whisper
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, Form

app = FastAPI()
model = whisper.load_model("small")  # поменяйте на нужный размер

@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(default=None)
):
    # Сохраняем временный файл с правильным расширением
    suffix = os.path.splitext(file.filename)[1] or ".ogg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path, language=language)
    finally:
        os.unlink(tmp_path)

    return {"text": result["text"]}
