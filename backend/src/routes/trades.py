"""Trade history routes"""

from fastapi import APIRouter, Depends, Request, Query
from src.middleware.auth import verify_token
from typing import Optional

router = APIRouter()


@router.get("/")
async def get_trades(
    request: Request,
    payload: dict = Depends(verify_token),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    status: Optional[str] = None,
    action: Optional[str] = None,
):
    db = request.app.state.db
    query = "SELECT * FROM trades WHERE 1=1"
    params = []
    i = 1
    if status:
        query += f" AND status = ${i}"; params.append(status); i += 1
    if action:
        query += f" AND action = ${i}"; params.append(action); i += 1
    query += f" ORDER BY opened_at DESC LIMIT ${i} OFFSET ${i+1}"
    params.extend([limit, offset])

    rows = await db.fetch(query, *params)
    total = await db.fetchval("SELECT COUNT(*) FROM trades")
    return {"trades": [dict(r) for r in rows], "total": total}


@router.get("/{trade_id}")
async def get_trade(trade_id: int, request: Request, payload: dict = Depends(verify_token)):
    db = request.app.state.db
    row = await db.fetchrow("SELECT * FROM trades WHERE id = $1", trade_id)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Trade not found")
    return dict(row)
