from fastapi import APIRouter
import os, subprocess, uuid

router = APIRouter()

@router.post('/clone')
async def clone():
    suffix = uuid.uuid4().hex[:6]
    cmd = ["bash", "scripts/prodize_clone_helper.sh", suffix]
    out = subprocess.check_output(cmd).decode()
    return {"suffix": suffix, "out": out}