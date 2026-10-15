# -*- coding: utf-8 -*-
"""微信小程序服务层（车主端：登录 / 绑定车辆 / 收到通知 / 提交申诉）

背景（2026-10-03 由 DSH 新建）：
  项目原有 `routers/wechat.py` 是**市民举报违规**的接口，与小程序实际需求
  （车主视角：收通知 + 申诉）是两套业务。且存在三个地基缺口：
    ① `verify_wechat_user(openid)` 是假实现（只判断长度 > 10），无真实 code2session
    ② **没有"用户 ↔ 车辆"关系**，车主无从知道"哪条违规是我的"
    ③ 违规记录无车牌字段、申诉塞在 system_configs 的 JSON 里，无法按用户查询
  本模块为这三件事提供最小但正确的地基，独立建表，不改动既有表结构。

设计要点：
  - 真实 `code2session`（配置缺失时降级为开发模式，并明确标记 dev_mode=True）
  - 绑定关系支持"车牌号"与"车架号后 6 位"两种方式（后者用于套牌争议）
  - 通知走微信订阅消息；未配置模板时只落库（站内信），不报错
  - 全部使用参数化 SQL，避免注入
"""

import json
import logging
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request

logger = logging.getLogger("zhitong_api")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_FILE = os.path.join(BASE_DIR, "zhitong_violations.db")
_lock = threading.Lock()

# 微信小程序配置（从环境变量/.env 读取；缺失则进入开发模式）
WX_APPID = os.environ.get("WX_APPID", "").strip()
WX_SECRET = os.environ.get("WX_SECRET", "").strip()
# 订阅消息模板 id（"违规通知"模板），未配置则只落库站内信
WX_TMPL_VIOLATION = os.environ.get("WX_TMPL_VIOLATION", "").strip()


def _conn():
    c = sqlite3.connect(_DB_FILE, timeout=15)
    c.row_factory = sqlite3.Row
    return c


def init_tables():
    """建表（幂等）"""
    with _lock:
        con = _conn()
        try:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wx_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openid TEXT UNIQUE NOT NULL,
                    unionid TEXT,
                    nickname TEXT,
                    avatar TEXT,
                    phone TEXT,
                    session_key TEXT,
                    created_at TEXT,
                    last_login TEXT
                )""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wx_vehicle_bindings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openid TEXT NOT NULL,
                    plate_number TEXT NOT NULL,
                    vin_tail TEXT,
                    relation TEXT DEFAULT 'owner',
                    verified INTEGER DEFAULT 0,
                    created_at TEXT,
                    UNIQUE(openid, plate_number)
                )""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wx_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openid TEXT NOT NULL,
                    kind TEXT DEFAULT 'violation',
                    title TEXT,
                    body TEXT,
                    plate_number TEXT,
                    violation_id INTEGER,
                    event_id TEXT,
                    payload TEXT,
                    is_read INTEGER DEFAULT 0,
                    pushed INTEGER DEFAULT 0,
                    push_result TEXT,
                    created_at TEXT
                )""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wx_appeals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openid TEXT NOT NULL,
                    violation_id INTEGER,
                    event_id TEXT,
                    plate_number TEXT,
                    reason TEXT,
                    description TEXT,
                    evidence_urls TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewer TEXT,
                    review_note TEXT,
                    reviewed_at TEXT,
                    created_at TEXT
                )""")
            for sql in (
                "CREATE INDEX IF NOT EXISTS idx_wxbind_plate ON wx_vehicle_bindings(plate_number)",
                "CREATE INDEX IF NOT EXISTS idx_wxnoti_openid ON wx_notifications(openid, is_read)",
                "CREATE INDEX IF NOT EXISTS idx_wxappeal_openid ON wx_appeals(openid, status)",
                "CREATE INDEX IF NOT EXISTS idx_wxappeal_viol ON wx_appeals(violation_id)",
            ):
                cur.execute(sql)
            con.commit()
        finally:
            con.close()


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def is_configured() -> bool:
    return bool(WX_APPID and WX_SECRET)


# ---------------------------------------------------------------------------
# 登录：code2session
# ---------------------------------------------------------------------------
def code2session(code: str) -> dict:
    """用小程序 wx.login 拿到的 code 换取 openid/session_key

    返回 {'ok': bool, 'openid':..., 'session_key':..., 'dev_mode': bool, 'error':...}
    未配置 AppID/Secret 时进入**开发模式**：openid 由 code 派生（稳定可复现），
    并显式标记 dev_mode=True，避免"以为在跑真登录"。
    """
    if not code:
        return {"ok": False, "error": "code 为空"}
    if not is_configured():
        import hashlib
        fake = "dev_" + hashlib.sha1(code.encode("utf-8")).hexdigest()[:24]
        return {"ok": True, "openid": fake, "session_key": "", "dev_mode": True,
                "error": None, "note": "未配置 WX_APPID/WX_SECRET，使用开发模式 openid"}
    url = ("https://api.weixin.qq.com/sns/jscode2session?"
           + urllib.parse.urlencode({
               "appid": WX_APPID, "secret": WX_SECRET,
               "js_code": code, "grant_type": "authorization_code"}))
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as e:
        return {"ok": False, "error": f"请求微信失败: {type(e).__name__}: {str(e)[:80]}"}
    if data.get("openid"):
        return {"ok": True, "openid": data["openid"],
                "session_key": data.get("session_key", ""),
                "unionid": data.get("unionid"), "dev_mode": False, "error": None}
    return {"ok": False, "dev_mode": False,
            "error": f"微信返回错误 {data.get('errcode')}: {data.get('errmsg')}"}


def upsert_user(openid: str, unionid: str = None, session_key: str = "",
                nickname: str = None, avatar: str = None) -> dict:
    with _lock:
        con = _conn()
        try:
            cur = con.cursor()
            cur.execute("SELECT id FROM wx_users WHERE openid=?", (openid,))
            row = cur.fetchone()
            if row:
                cur.execute("""UPDATE wx_users SET unionid=COALESCE(?,unionid),
                               session_key=COALESCE(?,session_key),
                               nickname=COALESCE(?,nickname), avatar=COALESCE(?,avatar),
                               last_login=? WHERE openid=?""",
                            (unionid, session_key, nickname, avatar, _now(), openid))
                uid = row["id"]
            else:
                cur.execute("""INSERT INTO wx_users
                               (openid,unionid,nickname,avatar,session_key,created_at,last_login)
                               VALUES (?,?,?,?,?,?,?)""",
                            (openid, unionid, nickname, avatar, session_key, _now(), _now()))
                uid = cur.lastrowid
            con.commit()
            return {"id": uid, "openid": openid}
        finally:
            con.close()


# ---------------------------------------------------------------------------
# 车辆绑定
# ---------------------------------------------------------------------------
def normalize_plate(plate: str) -> str:
    """车牌归一化：去空格/横杠、转大写。用于匹配（违规记录里的车牌可能带噪声）"""
    if not plate:
        return ""
    s = str(plate).strip().upper()
    for ch in (" ", "-", "·", ".", "\t"):
        s = s.replace(ch, "")
    return s


def bind_vehicle(openid: str, plate_number: str, vin_tail: str = None,
                 relation: str = "owner") -> dict:
    plate = normalize_plate(plate_number)
    if len(plate) < 5:
        return {"ok": False, "error": "车牌号格式不正确"}
    with _lock:
        con = _conn()
        try:
            cur = con.cursor()
            cur.execute("""INSERT INTO wx_vehicle_bindings
                           (openid,plate_number,vin_tail,relation,verified,created_at)
                           VALUES (?,?,?,?,0,?)
                           ON CONFLICT(openid,plate_number) DO UPDATE SET
                             vin_tail=COALESCE(excluded.vin_tail, vin_tail),
                             relation=excluded.relation""",
                        (openid, plate, vin_tail, relation, _now()))
            con.commit()
            return {"ok": True, "plate_number": plate}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:80]}"}
        finally:
            con.close()


def unbind_vehicle(openid: str, plate_number: str) -> dict:
    plate = normalize_plate(plate_number)
    with _lock:
        con = _conn()
        try:
            cur = con.cursor()
            cur.execute("DELETE FROM wx_vehicle_bindings WHERE openid=? AND plate_number=?",
                        (openid, plate))
            con.commit()
            return {"ok": True, "deleted": cur.rowcount}
        finally:
            con.close()


def list_bound_vehicles(openid: str) -> list:
    con = _conn()
    try:
        cur = con.cursor()
        cur.execute("""SELECT plate_number, vin_tail, relation, verified, created_at
                       FROM wx_vehicle_bindings WHERE openid=? ORDER BY created_at DESC""",
                    (openid,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        con.close()


# ---------------------------------------------------------------------------
# 违规查询（按绑定车牌）
# ---------------------------------------------------------------------------
def _violation_rows_for_plates(plates: list, limit: int = 50) -> list:
    """按车牌查违规。

    数据来源：violation_evidences.additional_info 里的 plate_number（若存在），
    以及 traffic_events.vehicle_info 里的 plate。两处都没有车牌时返回空，
    调用方应向用户说明"该记录无车牌信息"。
    """
    if not plates:
        return []
    want = {normalize_plate(p) for p in plates if p}
    out = []
    con = _conn()
    try:
        cur = con.cursor()
        # 1) violation_evidences
        try:
            cur.execute("""SELECT id, violation_type, confidence, timestamp, image_path,
                                  video_path, additional_info, status
                           FROM violation_evidences
                           ORDER BY id DESC LIMIT 2000""")
            for r in cur.fetchall():
                info = {}
                try:
                    info = json.loads(r["additional_info"] or "{}")
                except Exception:
                    info = {}
                plate = normalize_plate(info.get("plate_number") or info.get("plate") or "")
                if plate and plate in want:
                    out.append({
                        "source": "violation_evidences", "violation_id": r["id"],
                        "violation_type": r["violation_type"], "plate_number": plate,
                        "confidence": r["confidence"], "timestamp": r["timestamp"],
                        "image_path": r["image_path"], "video_path": r["video_path"],
                        "status": r["status"],
                    })
        except Exception as e:
            logger.debug(f"[wechat] 查 violation_evidences 失败: {e}")
        # 2) traffic_events
        try:
            cur.execute("""SELECT event_id, event_type, state, trigger_time, vehicle_info,
                                  event_video_path, key_frames, rule_judgment
                           FROM traffic_events ORDER BY id DESC LIMIT 2000""")
            for r in cur.fetchall():
                vi = {}
                try:
                    vi = json.loads(r["vehicle_info"] or "{}")
                except Exception:
                    vi = {}
                plate = normalize_plate(vi.get("plate") or vi.get("plate_number") or "")
                if plate and plate in want:
                    out.append({
                        "source": "traffic_events", "event_id": r["event_id"],
                        "violation_type": r["event_type"], "plate_number": plate,
                        "confidence": None, "timestamp": r["trigger_time"],
                        "state": r["state"], "video_path": r["event_video_path"],
                    })
        except Exception as e:
            logger.debug(f"[wechat] 查 traffic_events 失败: {e}")
    finally:
        con.close()
    out.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return out[:limit]


def list_my_violations(openid: str, limit: int = 50) -> list:
    plates = [b["plate_number"] for b in list_bound_vehicles(openid)]
    return _violation_rows_for_plates(plates, limit=limit)


# ---------------------------------------------------------------------------
# 通知
# ---------------------------------------------------------------------------
def create_notification(openid: str, title: str, body: str = "",
                        plate_number: str = None, violation_id: int = None,
                        event_id: str = None, payload: dict = None,
                        push: bool = True) -> dict:
    with _lock:
        con = _conn()
        try:
            cur = con.cursor()
            cur.execute("""INSERT INTO wx_notifications
                           (openid,kind,title,body,plate_number,violation_id,event_id,
                            payload,is_read,pushed,created_at)
                           VALUES (?,'violation',?,?,?,?,?,?,0,0,?)""",
                        (openid, title, body, plate_number, violation_id, event_id,
                         json.dumps(payload or {}, ensure_ascii=False), _now()))
            nid = cur.lastrowid
            con.commit()
        finally:
            con.close()
    pushed, pres = False, "未推送（未配置模板或未获取到 formId）"
    if push:
        pushed, pres = push_subscribe_message(openid, plate_number or "", body or title)
        with _lock:
            con = _conn()
            try:
                con.execute("UPDATE wx_notifications SET pushed=?, push_result=? WHERE id=?",
                            (1 if pushed else 0, pres[:300], nid))
                con.commit()
            finally:
                con.close()
    return {"id": nid, "pushed": pushed, "push_result": pres}


def list_notifications(openid: str, only_unread: bool = False, limit: int = 50) -> list:
    con = _conn()
    try:
        cur = con.cursor()
        sql = ("SELECT id,title,body,plate_number,violation_id,event_id,is_read,pushed,"
               "push_result,created_at FROM wx_notifications WHERE openid=?")
        if only_unread:
            sql += " AND is_read=0"
        sql += " ORDER BY id DESC LIMIT ?"
        cur.execute(sql, (openid, max(1, min(200, limit))))
        return [dict(r) for r in cur.fetchall()]
    finally:
        con.close()


def mark_read(openid: str, notification_id: int = None, all_read: bool = False) -> dict:
    with _lock:
        con = _conn()
        try:
            cur = con.cursor()
            if all_read:
                cur.execute("UPDATE wx_notifications SET is_read=1 WHERE openid=?", (openid,))
            elif notification_id:
                cur.execute("UPDATE wx_notifications SET is_read=1 WHERE openid=? AND id=?",
                            (openid, notification_id))
            con.commit()
            return {"ok": True, "updated": cur.rowcount}
        finally:
            con.close()


def push_subscribe_message(openid: str, plate: str, summary: str) -> tuple:
    """下发微信订阅消息（未配置模板时返回 False + 说明）"""
    if not (is_configured() and WX_TMPL_VIOLATION):
        return (False, "未配置 WX_TMPL_VIOLATION，仅站内信")
    token = get_access_token()
    if not token:
        return (False, "获取 access_token 失败")
    url = ("https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token="
           + urllib.parse.quote(token))
    body = json.dumps({
        "touser": openid,
        "template_id": WX_TMPL_VIOLATION,
        "page": "pages/violations/index",
        "data": {
            "thing1": {"value": (summary or "交通违规")[:20]},
            "character_string2": {"value": (plate or "-")[:32]},
            "time3": {"value": time.strftime("%Y-%m-%d %H:%M")},
        },
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            res = json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as e:
        return (False, f"推送失败: {type(e).__name__}")
    if res.get("errcode") == 0:
        return (True, "已推送")
    return (False, f"微信返回 {res.get('errcode')}: {res.get('errmsg')}")


_TOKEN_CACHE = {"token": None, "exp": 0}


def get_access_token() -> str:
    """获取小程序全局 access_token（带缓存，提前 5 分钟过期）"""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["exp"]:
        return _TOKEN_CACHE["token"]
    if not is_configured():
        return ""
    url = ("https://api.weixin.qq.com/cgi-bin/token?"
           + urllib.parse.urlencode({"grant_type": "client_credential",
                                     "appid": WX_APPID, "secret": WX_SECRET}))
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
        if d.get("access_token"):
            _TOKEN_CACHE["token"] = d["access_token"]
            _TOKEN_CACHE["exp"] = now + int(d.get("expires_in", 7200)) - 300
            return d["access_token"]
    except Exception as e:
        logger.warning(f"[wechat] 获取 access_token 失败: {e}")
    return ""


# ---------------------------------------------------------------------------
# 申诉
# ---------------------------------------------------------------------------
def submit_appeal(openid: str, reason: str, description: str = "",
                  violation_id: int = None, event_id: str = None,
                  plate_number: str = None, evidence_urls: list = None) -> dict:
    if not reason:
        return {"ok": False, "error": "申诉理由不能为空"}
    # 校验该违规确实属于该用户绑定的车辆（防止越权申诉他人违规）
    plates = {b["plate_number"] for b in list_bound_vehicles(openid)}
    if not plates:
        return {"ok": False, "error": "请先绑定车辆后再申诉"}
    target = None
    for row in _violation_rows_for_plates(list(plates), limit=500):
        if (violation_id is not None and row.get("violation_id") == violation_id) or \
           (event_id and row.get("event_id") == event_id):
            target = row
            break
    if target is None:
        return {"ok": False, "error": "未找到该违规记录，或它不属于你绑定的车辆"}
    with _lock:
        con = _conn()
        try:
            cur = con.cursor()
            cur.execute("""INSERT INTO wx_appeals
                           (openid,violation_id,event_id,plate_number,reason,description,
                            evidence_urls,status,created_at)
                           VALUES (?,?,?,?,?,?,?,'pending',?)""",
                        (openid, violation_id, event_id, target.get("plate_number"),
                         reason, description,
                         json.dumps(evidence_urls or [], ensure_ascii=False), _now()))
            aid = cur.lastrowid
            con.commit()
            return {"ok": True, "appeal_id": aid, "plate_number": target.get("plate_number")}
        finally:
            con.close()


def list_my_appeals(openid: str, limit: int = 50) -> list:
    con = _conn()
    try:
        cur = con.cursor()
        cur.execute("""SELECT id,violation_id,event_id,plate_number,reason,description,
                              evidence_urls,status,reviewer,review_note,reviewed_at,created_at
                       FROM wx_appeals WHERE openid=? ORDER BY id DESC LIMIT ?""",
                    (openid, max(1, min(200, limit))))
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["evidence_urls"] = json.loads(d.get("evidence_urls") or "[]")
            except Exception:
                d["evidence_urls"] = []
            rows.append(d)
        return rows
    finally:
        con.close()


def review_appeal(appeal_id: int, status: str, reviewer: str = "admin",
                  note: str = "") -> dict:
    """管理端审核申诉（accepted / rejected）"""
    if status not in ("accepted", "rejected", "pending"):
        return {"ok": False, "error": "status 必须是 accepted/rejected/pending"}
    with _lock:
        con = _conn()
        try:
            cur = con.cursor()
            cur.execute("""UPDATE wx_appeals SET status=?, reviewer=?, review_note=?,
                           reviewed_at=? WHERE id=?""",
                        (status, reviewer, note, _now(), appeal_id))
            con.commit()
            affected = cur.rowcount
        finally:
            con.close()
    if not affected:
        return {"ok": False, "error": "申诉不存在"}
    # 回写通知告知结果
    try:
        con = _conn()
        cur = con.cursor()
        cur.execute("SELECT openid, plate_number FROM wx_appeals WHERE id=?", (appeal_id,))
        row = cur.fetchone()
        con.close()
        if row:
            zh = {"accepted": "已受理", "rejected": "未通过"}.get(status, status)
            create_notification(row["openid"], f"申诉{zh}",
                                note or f"你的申诉（#{appeal_id}）{zh}",
                                plate_number=row["plate_number"], push=True)
    except Exception as e:
        logger.debug(f"[wechat] 申诉结果通知失败: {e}")
    return {"ok": True, "appeal_id": appeal_id, "status": status}


def stats() -> dict:
    con = _conn()
    try:
        cur = con.cursor()
        d = {}
        for t, k in (("wx_users", "users"), ("wx_vehicle_bindings", "bindings"),
                     ("wx_notifications", "notifications"), ("wx_appeals", "appeals")):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                d[k] = cur.fetchone()[0]
            except Exception:
                d[k] = 0
        try:
            cur.execute("SELECT status, COUNT(*) FROM wx_appeals GROUP BY status")
            d["appeals_by_status"] = {s: c for s, c in cur.fetchall()}
        except Exception:
            d["appeals_by_status"] = {}
        d["configured"] = is_configured()
        d["dev_mode"] = not is_configured()
        return d
    finally:
        con.close()


init_tables()
