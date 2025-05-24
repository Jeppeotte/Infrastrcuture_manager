from fastapi import APIRouter

router = APIRouter(prefix="/api/dashboard")

@router.get("/status")
async def get_status():
    # Dummy data
    return {"status": "online"}

@router.get("/node_status")
async def get_node_status():

    return