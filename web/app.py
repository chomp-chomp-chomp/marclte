from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI(title="marclite", description="HTTP wrapper for marclite CLI")


@app.get("/health")
async def health():
    return {"status": "healthy"}


async def stream_cli_output(process: asyncio.subprocess.Process) -> AsyncIterator[str]:
    """Stream CLI output line by line, converting to JSONL format."""
    if process.stdout is None:
        return

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        text = line.decode("utf-8").rstrip()
        if not text:
            continue

        try:
            json.loads(text)
            yield f"{text}\n"
        except json.JSONDecodeError:
            wrapped = json.dumps({"event": "log", "message": text})
            yield f"{wrapped}\n"

    await process.wait()

    if process.returncode != 0:
        stderr_output = ""
        if process.stderr:
            stderr_bytes = await process.stderr.read()
            stderr_output = stderr_bytes.decode("utf-8", errors="replace")[:1000]

        error_event = json.dumps({
            "event": "error",
            "message": f"CLI exited with code {process.returncode}",
            "stderr": stderr_output
        })
        yield f"{error_event}\n"


@app.post("/count")
async def count(input_file: UploadFile = File(...)):
    """Count records in a MARC file. Returns JSONL stream."""
    temp_dir = Path(tempfile.mkdtemp(prefix="marclite_count_", dir="/tmp"))

    try:
        input_path = temp_dir / input_file.filename
        content = await input_file.read()
        input_path.write_bytes(content)

        process = await asyncio.create_subprocess_exec(
            "marclite", "count", str(input_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async def cleanup_after_stream():
            async for chunk in stream_cli_output(process):
                yield chunk
            shutil.rmtree(temp_dir, ignore_errors=True)

        return StreamingResponse(
            cleanup_after_stream(),
            media_type="application/x-ndjson"
        )

    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/convert")
async def convert(
    input_file: UploadFile = File(...),
    to: str = Form(...)
):
    """Convert MARC file to specified format. Returns converted file."""
    temp_dir = Path(tempfile.mkdtemp(prefix="marclite_convert_", dir="/tmp"))

    try:
        input_path = temp_dir / input_file.filename
        content = await input_file.read()
        input_path.write_bytes(content)

        ext = "xml" if to == "marcxml" else to
        output_filename = f"{input_path.stem}_converted.{ext}"
        output_path = temp_dir / output_filename

        process = await asyncio.create_subprocess_exec(
            "marclite", "convert", str(input_path),
            "-o", str(output_path),
            "--to", to,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.wait()

        if process.returncode != 0:
            stderr_output = ""
            if process.stderr:
                stderr_bytes = await process.stderr.read()
                stderr_output = stderr_bytes.decode("utf-8", errors="replace")[:1000]
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail=f"CLI exited with code {process.returncode}: {stderr_output}"
            )

        if not output_path.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail="Output file was not created")

        return FileResponse(
            path=str(output_path),
            filename=output_filename,
            media_type="application/octet-stream",
            background=lambda: shutil.rmtree(temp_dir, ignore_errors=True)
        )

    except HTTPException:
        raise
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/split")
async def split(
    input_file: UploadFile = File(...),
    every: int = Form(...),
    to: str = Form(None)
):
    """Split MARC file into chunks. Returns zip of output files."""
    temp_dir = Path(tempfile.mkdtemp(prefix="marclite_split_", dir="/tmp"))

    try:
        input_path = temp_dir / input_file.filename
        content = await input_file.read()
        input_path.write_bytes(content)

        out_dir = temp_dir / "output"
        out_dir.mkdir()

        cmd = [
            "marclite", "split",
            "--every", str(every),
            str(input_path),
            "--out-dir", str(out_dir)
        ]

        if to:
            cmd.extend(["--to", to])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.wait()

        if process.returncode != 0:
            stderr_output = ""
            if process.stderr:
                stderr_bytes = await process.stderr.read()
                stderr_output = stderr_bytes.decode("utf-8", errors="replace")[:1000]
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail=f"CLI exited with code {process.returncode}: {stderr_output}"
            )

        zip_path = temp_dir / "split_output.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in out_dir.iterdir():
                if file_path.is_file():
                    zipf.write(file_path, arcname=file_path.name)

        return FileResponse(
            path=str(zip_path),
            filename="split_output.zip",
            media_type="application/zip",
            background=lambda: shutil.rmtree(temp_dir, ignore_errors=True)
        )

    except HTTPException:
        raise
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/merge")
async def merge(
    files: list[UploadFile] = File(...),
    to: str = Form(...)
):
    """Merge multiple MARC files into one. Returns merged file."""
    temp_dir = Path(tempfile.mkdtemp(prefix="marclite_merge_", dir="/tmp"))

    try:
        input_paths = []
        for idx, upload_file in enumerate(files):
            input_path = temp_dir / f"input_{idx}_{upload_file.filename}"
            content = await upload_file.read()
            input_path.write_bytes(content)
            input_paths.append(str(input_path))

        ext = "xml" if to == "marcxml" else to
        output_filename = f"merged.{ext}"
        output_path = temp_dir / output_filename

        cmd = [
            "marclite", "merge",
            *input_paths,
            "-o", str(output_path),
            "--to", to
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.wait()

        if process.returncode != 0:
            stderr_output = ""
            if process.stderr:
                stderr_bytes = await process.stderr.read()
                stderr_output = stderr_bytes.decode("utf-8", errors="replace")[:1000]
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail=f"CLI exited with code {process.returncode}: {stderr_output}"
            )

        if not output_path.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail="Output file was not created")

        return FileResponse(
            path=str(output_path),
            filename=output_filename,
            media_type="application/octet-stream",
            background=lambda: shutil.rmtree(temp_dir, ignore_errors=True)
        )

    except HTTPException:
        raise
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(exc))
