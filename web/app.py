"""FastAPI web service wrapper for marclite CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse

app = FastAPI(title="marclite", version="0.1.0")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/count")
async def count(input_file: UploadFile = File(...)):
    """Count records in a MARC file.

    Returns JSONL stream with events from marclite count command.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="marclite_"))
    try:
        input_path = tmp_dir / input_file.filename
        with input_path.open("wb") as f:
            content = await input_file.read()
            f.write(content)

        process = subprocess.Popen(
            ["marclite", "count", str(input_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        def generate():
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                    yield line + "\n"
                except json.JSONDecodeError:
                    event = {"event": "log", "message": line}
                    yield json.dumps(event, ensure_ascii=False) + "\n"

            process.wait()
            if process.returncode != 0:
                stderr = process.stderr.read(4096)
                error_event = {"event": "error", "message": f"Process failed: {stderr}"}
                yield json.dumps(error_event, ensure_ascii=False) + "\n"

        return StreamingResponse(generate(), media_type="application/x-ndjson")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/convert")
async def convert(input_file: UploadFile = File(...), to: str = Form(...)):
    """Convert MARC file to specified format.

    Returns converted file as attachment.
    """
    valid_formats = {"mrc", "mrk", "marcxml"}
    if to not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid format. Must be one of: {valid_formats}")

    tmp_dir = Path(tempfile.mkdtemp(prefix="marclite_"))
    try:
        input_path = tmp_dir / input_file.filename
        with input_path.open("wb") as f:
            content = await input_file.read()
            f.write(content)

        ext = "xml" if to == "marcxml" else to
        output_filename = f"{input_path.stem}_converted.{ext}"
        output_path = tmp_dir / output_filename

        process = subprocess.run(
            ["marclite", "convert", str(input_path), "-o", str(output_path), "--to", to],
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            stderr = process.stderr[:4096]
            raise HTTPException(status_code=500, detail=f"Conversion failed: {stderr}")

        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Output file was not created")

        return FileResponse(
            path=str(output_path),
            filename=output_filename,
            media_type="application/octet-stream",
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/split")
async def split(
    input_file: UploadFile = File(...),
    every: int = Form(...),
    to: str = Form(None),
):
    """Split MARC file into chunks.

    Returns zip archive containing split files.
    """
    if to and to not in {"mrc", "mrk", "marcxml"}:
        raise HTTPException(status_code=400, detail=f"Invalid format: {to}")

    tmp_dir = Path(tempfile.mkdtemp(prefix="marclite_"))
    try:
        input_path = tmp_dir / input_file.filename
        with input_path.open("wb") as f:
            content = await input_file.read()
            f.write(content)

        out_dir = tmp_dir / "output"
        out_dir.mkdir()

        cmd = ["marclite", "split", "--every", str(every), str(input_path), "--out-dir", str(out_dir)]
        if to:
            cmd.extend(["--to", to])

        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            stderr = process.stderr[:4096]
            raise HTTPException(status_code=500, detail=f"Split failed: {stderr}")

        zip_path = tmp_dir / "output.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", out_dir)

        if not zip_path.exists():
            raise HTTPException(status_code=500, detail="Zip file was not created")

        return FileResponse(
            path=str(zip_path),
            filename=f"{input_path.stem}_split.zip",
            media_type="application/zip",
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/merge")
async def merge(
    files: List[UploadFile] = File(...),
    to: str = Form(...),
):
    """Merge multiple MARC files.

    Returns merged file as attachment.
    """
    valid_formats = {"mrc", "mrk", "marcxml"}
    if to not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid format. Must be one of: {valid_formats}")

    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least 2 files required for merge")

    tmp_dir = Path(tempfile.mkdtemp(prefix="marclite_"))
    try:
        input_paths = []
        for idx, file in enumerate(files):
            input_path = tmp_dir / f"input_{idx}_{file.filename}"
            with input_path.open("wb") as f:
                content = await file.read()
                f.write(content)
            input_paths.append(str(input_path))

        ext = "xml" if to == "marcxml" else to
        output_filename = f"merged.{ext}"
        output_path = tmp_dir / output_filename

        cmd = ["marclite", "merge"] + input_paths + ["-o", str(output_path), "--to", to]

        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            stderr = process.stderr[:4096]
            raise HTTPException(status_code=500, detail=f"Merge failed: {stderr}")

        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Output file was not created")

        return FileResponse(
            path=str(output_path),
            filename=output_filename,
            media_type="application/octet-stream",
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
