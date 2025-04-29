from fastapi import FastAPI, HTTPException, File, UploadFile
import boto3
from fastapi import Response, Body
import tempfile
import os
import requests
from .utils import extract_sections_from_tei
import openai
from pydantic import BaseModel
from typing import Optional
app = FastAPI()

# Load OpenAI API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize AWS Polly client
polly = boto3.client("polly", region_name=os.getenv("AWS_REGION"))

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/grobid/process")
async def grobid_process(file: UploadFile = File(...)):
    """
    Upload a PDF and return structured TEI/XML from GROBID.
    """
    # Save the uploaded file to a temporary file
    suffix = os.path.splitext(file.filename)[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # Send to GROBID fulltext processing endpoint
        with open(tmp_path, "rb") as f:
            resp = requests.post(
                "http://localhost:8070/api/processFulltextDocument",
                files={"input": ("input.pdf", f, "application/pdf")}
            )
        if resp.status_code == 200:
            return {"tei": resp.text}
        else:
            raise HTTPException(status_code=502, detail=f"GROBID process error: {resp.status_code}")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"GROBID connection error: {e}")
    finally:
        # Clean up temp file
        os.remove(tmp_path)


@app.post("/grobid/parse")
async def grobid_parse(file: UploadFile = File(...)):
    """
    Upload a PDF, process with GROBID, and return parsed sections as JSON.
    """
    # Reuse the existing process endpoint logic to get TEI/XML
    result = await grobid_process(file)
    tei_xml = result.get("tei", "")
    # Extract sections from TEI/XML
    sections = extract_sections_from_tei(tei_xml)
    if not sections:
        raise HTTPException(status_code=502, detail="No sections extracted from TEI")
    return {"sections": sections}


class SummarizeRequest(BaseModel):
    text: str
    max_tokens: Optional[int] = 150

@app.post("/summarize")
async def summarize(request: SummarizeRequest):
    """
    Summarize provided text using OpenAI.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text."},
                {"role": "user", "content": request.text},
            ],
            max_tokens=request.max_tokens,
            temperature=0.9,
        )
        summary = response.choices[0].message.content.strip()
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e}")


# TTS endpoint using AWS Polly
@app.post("/tts")
async def tts(request: dict = Body(...)):
    """
    Convert provided text to speech using AWS Polly and return MP3 audio.
    """
    text = request.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Field 'text' is required")
    try:
        resp = polly.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId="Mizuki",
            Engine="standard"
        )
        audio_stream = resp["AudioStream"].read()
        return Response(content=audio_stream, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Polly error: {e}")
