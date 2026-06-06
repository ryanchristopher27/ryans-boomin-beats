from fastapi import APIRouter

router = APIRouter()


@router.get("/account-analysis/")
def account_analysis():
    return {"status": "coming soon"}
