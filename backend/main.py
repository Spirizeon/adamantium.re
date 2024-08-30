from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import subprocess
import os
import requests

app = FastAPI()

#FRONTEND_CONTAINER_URL = "http://frontend:3000/report"  # Replace with the actual URL of the frontend container
FRONTEND_CONTAINER_URL = "http://frontend:3000/report"  # Replace with the actual URL of the frontend container

@app.post("/submit")
async def submit_file(file: UploadFile = File(...),
                      key: str=Form(...)):
    os.environ["ANTHROPIC_API_KEY"] = key
    # Check the file extension
    allowed_extensions = {'.exe', '.out', ''}
    extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    if extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    try:
        # Save the file temporarily
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(await file.read())

        # Process the file with test3.py
        process = subprocess.run(
            ["python3", "adam_engine/test3.py", temp_file_path],
            capture_output=True,
            text=True
        )

        # Check for errors in the process
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Processing failed: {process.stderr}")

        # Output from test3.py
        output = process.stdout

        # Forward the output to the frontend container's /report endpoint
        response = requests.post(FRONTEND_CONTAINER_URL, json={"result": output})

        # Handle the response from the frontend container
        if response.status_code == 200:
            return JSONResponse(content=response.json(), status_code=200)
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host="127.0.0.1",port=8000)

