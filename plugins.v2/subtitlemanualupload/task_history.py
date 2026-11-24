"""任务台账兼容 2.0 的队列，并接收旧插件已结束的记录。"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .media import VIDEO, metadata
from . import disc

ENDED = {"done", "failed", "skipped", "cancelled"}
OLD_STATE = {"completed": "done", "failed": "failed", "ignored": "skipped", "no_audio": "skipped", "cancelled": "cancelled"}
SOURCE = {"manual": "手动提交", "event": "入库触发", "subtitle_manual_upload": "字幕匹配联动"}
TRACK = {"auto": "自动选择", "matched_external": "匹配的外挂字幕", "local_external": "本地外挂字幕",
         "embedded": "视频内嵌字幕", "asr": "语音识别", "reuse": "沿用原稿"}
DETAIL = {"completed": "字幕生成完成", "failed": "字幕生成失败", "ignored": "字幕已存在或文件不满足原插件处理条件",
          "no_audio": "视频未检测到有效音轨，已跳过", "cancelled": "已取消"}


def migrate(conn, job_directory):
    conn.execute("BEGIN IMMEDIATE")
    fields = {r[1] for r in conn.execute("PRAGMA table_info(job)")}
    for name, kind in {"origin": "TEXT DEFAULT '海拉鲁 AI 字幕'", "finished": "TEXT DEFAULT ''", "legacy_id": "TEXT",
                       "cancel_requested": "INTEGER DEFAULT 0", "publishing": "INTEGER DEFAULT 0",
                       "hidden": "INTEGER DEFAULT 0", "rerun_of": "INTEGER"}.items():
        if name not in fields:
            conn.execute(f"ALTER TABLE job ADD COLUMN {name} {kind}")
    if "listed" not in {r[1] for r in conn.execute("PRAGMA table_info(target)")}:
        conn.execute("ALTER TABLE target ADD COLUMN listed INTEGER DEFAULT 1")
    if "finished" not in fields:
        # 2.0 仅留下译稿导出的时间，不能把它当作任务结束时间。
        for row in conn.execute("SELECT id,report FROM job WHERE state='done'"):
            try:
                stamp = (job_directory / str(row["id"]) / "export.json").stat().st_mtime
            except OSError:
                continue
            report = json.loads(row["report"])
            report["rendered"] = datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("UPDATE job SET report=? WHERE id=?", (json.dumps(report, ensure_ascii=False), row["id"]))
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS old_task ON job(legacy_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS job_date ON job(hidden,created DESC,id DESC)")


def as_utc(stamp):
    if not stamp:
        return ""
    try:
        return datetime.fromisoformat(str(stamp)).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OverflowError, OSError):
        return ""


def import_finished(conn, records):
    if not isinstance(records, dict):
        return
    conn.execute("BEGIN IMMEDIATE")
    seen = {r[0] for r in conn.execute("SELECT legacy_id FROM job WHERE legacy_id IS NOT NULL")}
    for ident, raw in records.items():
        if not isinstance(raw, dict) or str(ident) in seen:
            continue
        status = str(raw.get("status") or "")
        if status not in OLD_STATE or not isinstance(raw.get("video_file"), str) or not raw["video_file"].strip():
            continue
        # 旧媒体可能已离线或位于不同的挂载上，历史保留原路径，重新生成时再验证。
        path = Path(raw["video_file"])
        key = hashlib.sha256(os.path.normcase(str(path)).encode()).hexdigest()
        conn.execute("INSERT OR IGNORE INTO target(id,path,meta,listed) VALUES (?,?,?,0)",
                     (key, str(path), json.dumps(metadata(path), ensure_ascii=False)))
        source = str(raw.get("resolved_source") or raw.get("source_policy") or "auto")
        output = raw.get("output_path")
        report = {"source": TRACK.get(source, source), "files": [Path(output).name] if isinstance(output, str) and output else []}
        conn.execute("""INSERT INTO job(target,state,detail,report,created,finished,origin,legacy_id)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (key, OLD_STATE[status], str(raw.get("error_message") or DETAIL[status]), json.dumps(report, ensure_ascii=False),
                      as_utc(raw.get("add_time")), as_utc(raw.get("complete_time")),
                      SOURCE.get(str(raw.get("source")), "旧版联动"), str(ident)))


def describe(row):
    body = {k: row[k] for k in ("id", "target", "state", "detail", "created", "finished", "origin", "path")}
    report = json.loads(row["report"])
    report.setdefault("source", "自动选择")
    body.update(file=Path(row["path"]).name, legacy=row["legacy_id"] is not None, cancelling=bool(row["cancel_requested"]),
                publishing=bool(row["publishing"]), report=report)
    return body


def by_target(conn):
    records = {}
    rows = conn.execute("""SELECT j.*,t.path FROM job j JOIN target t ON t.id=j.target WHERE j.hidden=0
                         ORDER BY j.state IN ('queued','running') DESC,j.created DESC,j.id DESC""")
    for row in rows:
        job, count = records.get(row["target"], (None, 0))
        records[row["target"]] = (job or describe(row), count + 1)
    return records


def page(conn, state="all", order="desc", offset=0, limit=100, native_only=False, target=""):
    if state not in ENDED | {"all", "running", "queued"} or order not in ("asc", "desc"):
        raise ValueError("筛选或排序无效")
    if not conn.in_transaction:
        conn.execute("BEGIN")
    cond, params = ["j.hidden=0"], []
    if native_only:
        cond.append("j.legacy_id IS NULL")
    if target:
        cond.append("j.target=?")
        params.append(target)
    counts = {r[0]: r[1] for r in conn.execute("SELECT j.state,COUNT(*) FROM job j WHERE " + " AND ".join(cond) + " GROUP BY j.state")}
    if state != "all":
        cond.append("j.state=?")
        params.append(state)
    sort = "ASC" if order == "asc" else "DESC"
    query = ("SELECT j.*,t.path FROM job j JOIN target t ON t.id=j.target WHERE " + " AND ".join(cond) +
             f" ORDER BY j.created {sort},j.id {sort} LIMIT ? OFFSET ?")
    limit = min(max(1, limit), 200)
    rows = conn.execute(query, (*params, limit + 1, min(max(0, offset), 2**63 - 1))).fetchall()
    items = [describe(row) for row in rows[:limit]]
    return {"jobs": items, "counts": counts, "total": sum(counts.values()), "more": len(rows)>limit}


def operate(conn, action, ids):
    if action not in ("cancel", "restart", "delete") or not isinstance(ids, list) or not 0 < len(ids) <= 1000 or any(
        type(i) is not int or not 0 < i <= 2**63-1 for i in ids
    ):
        raise ValueError("请选择有效的任务及操作（每次最多 1000 条）")
    conn.execute("BEGIN IMMEDIATE")
    changed, skipped, new_ids = [], [], []
    for i in dict.fromkeys(ids):
        row = conn.execute("SELECT j.*,t.path FROM job j JOIN target t ON t.id=j.target WHERE j.id=? AND j.hidden=0",(i,)).fetchone()
        reason = ""
        if not row:
            reason = "任务已移除"
        elif action == "cancel" and row["state"] == "queued" and not row["publishing"]:
            conn.execute("UPDATE job SET state='cancelled',detail='已取消等待任务',finished=CURRENT_TIMESTAMP WHERE id=?", (i,))
        elif action == "cancel" and row["state"] == "running" and not row["publishing"] and not row["cancel_requested"]:
            conn.execute("UPDATE job SET cancel_requested=1,detail='正在取消，等待当前步骤结束' WHERE id=?", (i,))
        elif action == "delete" and row["state"] in ENDED:
            # 保留旧记录的唯一 ID，升级或刷新索引时不会再次导入已删除记录。
            conn.execute("UPDATE job SET hidden=1 WHERE id=?", (i,))
        elif action == "restart" and row["state"] in ENDED:
            path = Path(row["path"])
            if disc.is_original(path):
                reason = "原盘使用 SubHD 或手动字幕"
            elif not path.is_absolute() or path.suffix.lower() not in VIDEO:
                reason = "当前路径或媒体格式不支持翻译"
            elif not path.is_file():
                reason = "媒体文件已移动或离线"
            elif conn.execute("SELECT 1 FROM job WHERE target=? AND state IN ('queued','running')", (row["target"],)).fetchone():
                reason = "本影片已有任务"
            else:
                new_ids.append(conn.execute("INSERT INTO job(target,state,origin,rerun_of) VALUES (?,'queued','重新生成',?)",
                                            (row["target"],i)).lastrowid)
        else:
            reason = "任务当前状态不能执行此操作"
        if reason:
            skipped.append({"id":i,"reason":reason})
        else:
            changed.append(i)
    return {"changed": changed, "skipped": skipped, "new_jobs": new_ids}
