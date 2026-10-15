# -*- coding: utf-8 -*-
"""微信小程序 API（车主端）

接口一览（前缀 /api/wx）：
  POST /login                      微信登录（code -> openid）
  GET  /profile                    当前用户信息
  GET  /vehicles                   我绑定的车辆
  POST /vehicles/bind              绑定车辆
  POST /vehicles/unbind            解绑车辆
  GET  /violations                 我的违规（按绑定车牌）
  GET  /notifications              我的通知
  POST /notifications/read         标记已读
  POST /appeals                    提交申诉
  GET  /appeals                    我的申诉列表
  POST /appeals/review             审核申诉（管理端）
  GET  /stats                      统计（管理端）

鉴权：请求头 `X-Openid` 携带登录得到的 openid。
（小程序侧应在 wx.login 后立即调用 /login，并把 openid 存 storage。）
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import wechat_miniapp as wx

logger = logging.getLogger("zhitong_api")
router = APIRouter(prefix="/api/wx", tags=["微信小程序"])


class LoginRequest(BaseModel):
    code: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class BindRequest(BaseModel):
    plate_number: str
    vin_tail: Optional[str] = None
    relation: Optional[str] = "owner"


class UnbindRequest(BaseModel):
    plate_number: str


class ReadRequest(BaseModel):
    notification_id: Optional[int] = None
    all_read: bool = False


class AppealRequest(BaseModel):
    reason: str
    description: Optional[str] = ""
    violation_id: Optional[int] = None
    event_id: Optional[str] = None
    evidence_urls: Optional[List[str]] = None


class ReviewRequest(BaseModel):
    appeal_id: int
    status: str
    note: Optional[str] = ""
    reviewer: Optional[str] = "admin"


def _require_openid(x_openid: Optional[str]) -> str:
    if not x_openid:
        raise HTTPException(status_code=401, detail="缺少 X-Openid 请求头（请先调用 /api/wx/login）")
    return x_openid


@router.post("/login")
def wx_login(req: LoginRequest):
    """微信登录：用 wx.login 的 code 换 openid"""
    r = wx.code2session(req.code)
    if not r.get("ok"):
        raise HTTPException(status_code=401, detail=r.get("error") or "登录失败")
    user = wx.upsert_user(r["openid"], r.get("unionid"), r.get("session_key") or "",
                          req.nickname, req.avatar)
    return JSONResponse(content={
        "success": True,
        "data": {"openid": r["openid"], "user_id": user["id"],
                 "dev_mode": bool(r.get("dev_mode")),
                 "note": r.get("note")},
    })


@router.get("/profile")
def wx_profile(x_openid: Optional[str] = Header(None, alias="X-Openid")):
    openid = _require_openid(x_openid)
    return JSONResponse(content={
        "success": True,
        "data": {"openid": openid,
                 "vehicles": wx.list_bound_vehicles(openid),
                 "unread": len(wx.list_notifications(openid, only_unread=True, limit=200))},
    })


@router.get("/vehicles")
def wx_vehicles(x_openid: Optional[str] = Header(None, alias="X-Openid")):
    openid = _require_openid(x_openid)
    return JSONResponse(content={"success": True, "data": wx.list_bound_vehicles(openid)})


@router.post("/vehicles/bind")
def wx_bind(req: BindRequest, x_openid: Optional[str] = Header(None, alias="X-Openid")):
    openid = _require_openid(x_openid)
    r = wx.bind_vehicle(openid, req.plate_number, req.vin_tail, req.relation or "owner")
    if not r.get("ok"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return JSONResponse(content={"success": True, "data": r})


@router.post("/vehicles/unbind")
def wx_unbind(req: UnbindRequest, x_openid: Optional[str] = Header(None, alias="X-Openid")):
    openid = _require_openid(x_openid)
    return JSONResponse(content={"success": True, "data": wx.unbind_vehicle(openid, req.plate_number)})


@router.get("/violations")
def wx_violations(limit: int = 50, x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """我的违规（按绑定车牌匹配）

    注意：只有**识别到车牌**的记录才能匹配到车主。若为 0 条且已绑定车辆，
    说明当前违规记录里没有对应车牌（车牌识别是本项目的增强项）。
    """
    openid = _require_openid(x_openid)
    plates = wx.list_bound_vehicles(openid)
    rows = wx.list_my_violations(openid, limit=limit)
    return JSONResponse(content={
        "success": True, "data": rows, "total": len(rows),
        "bound_plates": [p["plate_number"] for p in plates],
        "hint": None if rows else ("未匹配到违规记录；若你的车确有违规，"
                                   "可能是该记录未识别到车牌"),
    })


@router.get("/notifications")
def wx_notifications(only_unread: bool = False, limit: int = 50,
                     x_openid: Optional[str] = Header(None, alias="X-Openid")):
    openid = _require_openid(x_openid)
    return JSONResponse(content={"success": True,
                                 "data": wx.list_notifications(openid, only_unread, limit)})


@router.post("/notifications/read")
def wx_read(req: ReadRequest, x_openid: Optional[str] = Header(None, alias="X-Openid")):
    openid = _require_openid(x_openid)
    return JSONResponse(content={"success": True,
                                 "data": wx.mark_read(openid, req.notification_id, req.all_read)})


@router.post("/appeals")
def wx_submit_appeal(req: AppealRequest, x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """提交申诉（会校验该违规属于你绑定的车辆）"""
    openid = _require_openid(x_openid)
    r = wx.submit_appeal(openid, req.reason, req.description or "",
                         req.violation_id, req.event_id, None, req.evidence_urls)
    if not r.get("ok"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return JSONResponse(content={"success": True, "data": r})


@router.get("/appeals")
def wx_my_appeals(limit: int = 50, x_openid: Optional[str] = Header(None, alias="X-Openid")):
    openid = _require_openid(x_openid)
    return JSONResponse(content={"success": True, "data": wx.list_my_appeals(openid, limit)})


@router.post("/appeals/review")
def wx_review(req: ReviewRequest):
    """审核申诉（管理端；生产环境应加管理员鉴权）"""
    r = wx.review_appeal(req.appeal_id, req.status, req.reviewer or "admin", req.note or "")
    if not r.get("ok"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return JSONResponse(content={"success": True, "data": r})


@router.get("/overview")
def wx_overview(x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """首页看板（2026-10-03 由 DSH 新增）

    小程序首页需要 total/today/pending/confirmed 这几个数，
    原 `/api/wx/stats` 返回的是系统级统计，字段对不上。此接口按
    **当前用户绑定车辆**聚合，字段名与小程序的既有代码保持一致。
    """
    try:
        import time as _t
        openid = _require_openid(x_openid)
        con = wx._conn()
        try:
            cur = con.cursor()
            cur.execute("SELECT plate_number FROM wx_vehicle_bindings WHERE openid=?", (openid,))
            plates = [r["plate_number"] for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) FROM wx_notifications WHERE openid=? AND is_read=0", (openid,))
            unread = cur.fetchone()[0]
        finally:
            con.close()
        rows = wx.list_my_violations(openid, limit=2000)
        today = _t.strftime("%Y-%m-%d")
        by_type = {}
        for r in rows:
            t = r.get("violation_type") or "unknown"
            by_type[t] = by_type.get(t, 0) + 1
        pending = len([r for r in rows if (r.get("state") or r.get("status") or "")
                       in ("triggered", "pending", "pending_ai", "manual_review")])
        confirmed = len([r for r in rows if (r.get("state") or r.get("status") or "")
                         in ("confirmed", "processed")])
        return JSONResponse(content={
            "success": True,
            "data": {
                "total": len(rows),
                "today": len([r for r in rows if str(r.get("timestamp") or "").startswith(today)]),
                "pending": pending,
                "confirmed": confirmed,
                "unread": unread,
                "bound_plates": plates,
                "by_type": [{"type": k, "count": v} for k, v in
                            sorted(by_type.items(), key=lambda x: -x[1])],
                # 前端字段兼容：既给 by_type 也给 by_status
                "by_status": [],
            },
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取看板失败: {str(e)}")


@router.get("/violations/list")
def wx_violations_alias(limit: int = 20, page: int = 1, page_size: int = None,
                        x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """兼容别名：小程序既有代码调用的是 /violations/list（2026-10-03 由 DSH 新增）

    ⚠ 本路由**必须定义在 `/violations/{violation_id}` 之前**：
    FastAPI 按注册顺序匹配，若参数路由在前，"/violations/list" 会先命中
    {violation_id} 并把 "list" 转 int -> 422。
    """
    openid = _require_openid(x_openid)
    size = int(page_size or limit or 20)
    rows = wx.list_my_violations(openid, limit=2000)
    start = max(0, (int(page) - 1) * size)
    chunk = rows[start:start + size]
    plates = [b["plate_number"] for b in wx.list_bound_vehicles(openid)]
    return JSONResponse(content={
        "success": True,
        "data": chunk,
        "items": chunk,
        "total": len(rows),
        "page": int(page),
        "page_size": size,
        "has_more": start + size < len(rows),
        "bound_plates": plates,
        "hint": None if rows else ("未匹配到违规记录；若你的车确有违规，"
                                   "可能是该记录未识别到车牌"),
    })


@router.get("/violations/{violation_id}")
def wx_violation_detail(violation_id: int,
                        x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """违规详情（含证据图/视频路径）"""
    openid = _require_openid(x_openid)
    rows = wx.list_my_violations(openid, limit=2000)
    for r in rows:
        if r.get("violation_id") == violation_id:
            return JSONResponse(content={"success": True, "data": r})
    for r in rows:
        if str(r.get("event_id")) == str(violation_id):
            return JSONResponse(content={"success": True, "data": r})
    raise HTTPException(status_code=404, detail="未找到该违规，或它不属于你绑定的车辆")


@router.get("/bind/status")
def wx_bind_status(x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """绑定状态 + 可绑定车牌建议（2026-10-03 由 DSH 新增）

    从近期违规记录里提取出现过的车牌作为"建议列表"，方便演示时直接点选。
    同时给出 has_binding，供前端做"未绑定则引导"的分支。
    """
    try:
        openid = _require_openid(x_openid)
        mine = wx.list_bound_vehicles(openid)
        con = wx._conn()
        candidates = []
        try:
            import json as _json
            cur = con.cursor()
            cur.execute("""SELECT additional_info FROM violation_evidences
                           ORDER BY id DESC LIMIT 300""")
            seen = {}
            for r in cur.fetchall():
                try:
                    p = _json.loads(r["additional_info"] or "{}").get("plate_number")
                except Exception:
                    p = None
                if p:
                    seen[p] = seen.get(p, 0) + 1
            candidates = [{"plate_number": k, "count": v}
                          for k, v in sorted(seen.items(), key=lambda x: -x[1])[:12]]
        finally:
            con.close()
        return JSONResponse(content={
            "success": True,
            "data": {"has_binding": bool(mine), "my_vehicles": mine,
                     "suggest_plates": candidates},
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取绑定状态失败: {str(e)}")


@router.post("/vehicles/bind-by-suggest")
def wx_bind_by_suggest(plate_number: str,
                       x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """一键绑定"系统识别到过的车牌"（演示/联调用，自动标记已验证）

    验证逻辑：该车牌必须**在违规记录里出现过**，否则不允许绑定
    （避免用户随意绑定他人车牌）。
    """
    try:
        openid = _require_openid(x_openid)
        norm = wx.normalize_plate(plate_number)
        con = wx._conn()
        found = False
        try:
            import json as _json
            cur = con.cursor()
            cur.execute("""SELECT additional_info FROM violation_evidences
                           ORDER BY id DESC LIMIT 500""")
            for r in cur.fetchall():
                try:
                    if wx.normalize_plate(
                            _json.loads(r["additional_info"] or "{}").get("plate_number") or "") == norm:
                        found = True
                        break
                except Exception:
                    continue
        finally:
            con.close()
        if not found:
            raise HTTPException(status_code=400,
                                detail=f"车牌 {norm} 未在系统记录中出现过，无法一键绑定")
        r = wx.bind_vehicle(openid, norm, None, "owner")
        if r.get("ok"):
            try:
                con = wx._conn()
                con.execute("UPDATE wx_vehicle_bindings SET verified=1 "
                            "WHERE openid=? AND plate_number=?", (openid, norm))
                con.commit()
                con.close()
            except Exception:
                pass
        return JSONResponse(content={"success": True, "data": r})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"绑定失败: {str(e)}")


@router.get("/statistics/overview")
def wx_stats_overview(x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """兼容别名：首页看板（小程序既有代码调 /statistics/overview）"""
    return wx_overview(x_openid)


@router.get("/appeals/list")
def wx_appeals_alias(limit: int = 50, x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """兼容别名：申诉列表（小程序既有代码调 /appeals/list）"""
    openid = _require_openid(x_openid)
    rows = wx.list_my_appeals(openid, limit)
    return JSONResponse(content={"success": True, "data": rows, "items": rows,
                                 "total": len(rows)})


@router.get("/appeals/statistics/summary")
def wx_appeals_stats(x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """兼容别名：申诉统计（小程序既有代码调 /appeals/statistics/summary）"""
    openid = _require_openid(x_openid)
    rows = wx.list_my_appeals(openid, limit=500)
    by = {}
    for r in rows:
        s = r.get("status") or "pending"
        by[s] = by.get(s, 0) + 1
    return JSONResponse(content={
        "success": True,
        "data": {"total": len(rows), "pending": by.get("pending", 0),
                 "accepted": by.get("accepted", 0), "rejected": by.get("rejected", 0),
                 "by_status": [{"status": k, "count": v} for k, v in by.items()]},
    })


@router.get("/stats")
def wx_stats():
    return JSONResponse(content={"success": True, "data": wx.stats()})


@router.post("/notify-test")
def wx_notify_test(plate_number: str, title: str = "违规通知",
                   x_openid: Optional[str] = Header(None, alias="X-Openid")):
    """给绑定该车牌的所有用户发通知（便于演示/联调）"""
    openid = _require_openid(x_openid)
    con = wx._conn()
    targets = []
    try:
        cur = con.cursor()
        cur.execute("SELECT openid FROM wx_vehicle_bindings WHERE plate_number=?",
                    (wx.normalize_plate(plate_number),))
        targets = [r["openid"] for r in cur.fetchall()]
    finally:
        con.close()
    if not targets:
        return JSONResponse(content={"success": False, "message": "该车牌暂无绑定用户",
                                     "data": {"plate": wx.normalize_plate(plate_number)}})
    res = [wx.create_notification(o, title, f"{plate_number} 有一条新违规记录",
                                  plate_number=plate_number, push=True) for o in targets]
    return JSONResponse(content={"success": True, "data": {"sent": len(res), "detail": res}})
