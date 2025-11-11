import datetime
import uuid
import shutil
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware  
from typing import Dict, Any, List
import os

from AI_Interface.STT.Interface import TranscriptionResult
from AI_Interface.LLM.Interface import LanguageModelInterface, GenericAnalysisResult
from AI_Interface.STT.Adaptors.AssemblyAi import AssemblyAIClient
from AI_Interface.LLM.Adaptors.GoogleAIStudio import GeminiClient
from Model.tasks import LLM_TASKS
from Model.job import Job, CreateJobRequest, UploadResponse

# --- Configuration ---
# Create a temporary directory to store uploads for the mock server
UPLOAD_DIR = "temp_uploads"
if os.path.exists(UPLOAD_DIR):
    shutil.rmtree(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR)

# --- In-Memory Storage ---
JOBS_DB: Dict[str, Job] = {}

# --- Initialize Application and Clients ---
app = FastAPI(title="AI Call Center Analysis API", version="1.0.0")

# --- NEW: Cấu hình CORS ---
# Cho phép mọi nguồn (origin) truy cập API để dễ dàng phát triển.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------

stt_client = AssemblyAIClient("63b43ff9e09542a0aee99d1cfc225f47")
llm_client = GeminiClient("AIzaSyCN2N-2S7BuEHr58e5Iwq2t-8v4wxhJxQ4")


# --- Background Worker Logic ---
async def run_analysis_in_background(job_id: str, audio_urls: List[str]):
    """This function is executed by the background task."""
    print(f"Background task started for job_id: {job_id}")
    job = JOBS_DB.get(job_id)
    if not job: return
    job.status = "processing"

    final_results = []
    for url in audio_urls:
        try:
            # 1. Transcribe
            transcription = await stt_client.transcribe(audio_source=url, enable_speaker_diarization=True)

            # 2. Create the analysis tasks
            summary_task = llm_client.analyze(transcription, "summarization")
            sentiment_task = llm_client.analyze(transcription, "sentiment_analysis")
            actions_task = llm_client.analyze(transcription, "action_item_extraction")

            # Run all three LLM analyses concurrently and wait for them all to finish
            summary_dict, sentiment_dict, actions_dict = await asyncio.gather(
                summary_task,
                sentiment_task,
                actions_task
            )

            # 3. Format into the AnalysisReport structure
            final_results.append({
                "sourceUrl": url, "status": "SUCCESS", "errorMessage": None,
                "transcription": transcription.__dict__,
                "summary": summary_dict,
                "sentiment": sentiment_dict,
                "actionItems": actions_dict,
            })
        except Exception as e:
            # Add traceback for better debugging
            import traceback
            traceback.print_exc()
            final_results.append({"sourceUrl": url, "status": "FAILED", "errorMessage": str(e)})

    # Update the job in our "database" with the final results
    job.status = "completed"
    job.completedAt = datetime.datetime.now(datetime.timezone.utc)
    job.results = final_results

    print(f"Background task finished for job_id: {job_id}. Status set to 'completed'.")


# --- API Endpoints ---

@app.post("/v1/uploads", response_model=UploadResponse, status_code=201, response_model_by_alias=False)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Handles uploading a local audio file."""
    try:
        # Generate a unique filename to prevent collisions
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Save the file to the temporary directory
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        upload_url = f"{request.base_url}v1/files/{unique_filename}"

        return UploadResponse(uploadUrl=upload_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")


@app.get("/v1/files/{filename}")
async def get_uploaded_file(filename: str):
    """Serves a file from the temporary upload directory."""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.post("/v1/jobs", response_model=Job, status_code=202, response_model_by_alias=False)
async def create_job(request: CreateJobRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{uuid.uuid4()}"

    # 1. Create the initial job object with status 'queued'
    new_job = Job(
        id=job_id,
        status="queued",
        createdAt=datetime.datetime.now(datetime.timezone.utc)
    )

    # 2. Store it in our in-memory database
    JOBS_DB[job_id] = new_job

    # 3. Add the long-running analysis to the background tasks
    background_tasks.add_task(run_analysis_in_background, job_id, request.audioUrls)

    print(f"Job {job_id} created and queued. Returning 202 Accepted.")

    # 4. Return the initial job object immediately
    return new_job


@app.get("/v1/jobs/{job_id}", response_model=Job, response_model_by_alias=False)
async def get_job(job_id: str):
    job = JOBS_DB.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job