from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from stockwise.app.db.session import SessionLocal

router = APIRouter()


@router.get("/ready")
def readiness_check():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db.commit()
        return {"status": "ready", "database": "connected"}
    except OperationalError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Service unavailable")
    finally:
        db.close()
