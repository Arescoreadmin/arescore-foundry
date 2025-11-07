from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Tuple

router = APIRouter(tags=["dev"])

class EmbedIn(BaseModel):
    text: str

@router.post("/dev/embed")
def dev_embed(payload: EmbedIn):
    # normalize whitespace so repeated calls are identical
    t = " ".join(payload.text.split())
    return {"ok": True, "vec": f"vec:{t}"}

@router.get("/dev/q")
def dev_q(q: str = Query(...), k: int = Query(10)):
    hits: List[Tuple[str, float]] = [(f"doc-{i}", 1.0 - i*0.01) for i in range(k)]
    return {"ok": True, "hits": hits}
