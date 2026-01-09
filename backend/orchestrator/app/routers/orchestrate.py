from fastapi import APIRouter

router = APIRouter()

@router.post("/orchestrate")
async def orchestrate_session(session_id: str, scenario_ref: str):
    # Day 1: just accept and echo. Real orchestration comes later.
    return {"status": "accepted", "session_id": session_id, "scenario_ref": scenario_ref}
