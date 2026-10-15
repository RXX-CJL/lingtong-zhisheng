# -*- coding: utf-8 -*-
"""灵瞳智声证据清理中心。只扫描数据库引用，不永久删除；清理操作仅移入可恢复隔离区。"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
import time
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "api"
DB_PATH = API_ROOT / "zhitong_violations.db"
EVENT_ROOT = API_ROOT / "output" / "event_videos"
QUARANTINE_ROOT = API_ROOT / "output" / "evidence_quarantine"
SUPPORTED_SUFFIXES = {".mp4", ".jpg", ".jpeg", ".png", ".json"}
PATH_PATTERN = re.compile(
    r"""(?i)(?:[a-z]:[\\/][^"'<>|]*?event[_-]videos[\\/]|event[_-]videos[\\/])([^"'<>|,\s\]\}]+)"""
)


def norm_key(value: str) -> str:
    normalized = value.replace("\\", "/")
    normalized = re.sub(r"/+", "/", normalized)
    return normalized.strip("/").casefold()


def extract_event_paths(value: str):
    """从数据库文本/JSON 中提取 event_videos 下的相对路径。"""
    if not value or ("event_video" not in value.casefold() and "event-video" not in value.casefold()):
        return
    for match in PATH_PATTERN.finditer(value):
        suffix = match.group(1).strip().rstrip(".,;:")
        if suffix:
            yield norm_key(suffix)


def scan_database_references(db_path: Path, event_root: Path):
    refs = set()
    missing = set()
    if not db_path.is_file():
        raise FileNotFoundError(f"数据库不存在：{db_path}")
    # 只读连接，避免本工具意外修改业务数据库。
    uri = db_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )]
        for table in tables:
            safe_table = table.replace('"', '""')
            columns = [r[1] for r in conn.execute(f'PRAGMA table_info("{safe_table}")')]
            if not columns:
                continue
            # 读取业务表文本字段，兼容 JSON 里嵌套的证据路径。
            try:
                rows = conn.execute(f'SELECT * FROM "{safe_table}"')
                names = [d[0] for d in rows.description]
                for row in rows:
                    for value in row:
                        if isinstance(value, str):
                            refs.update(extract_event_paths(value) or ())
            except sqlite3.Error:
                continue
    finally:
        conn.close()

    for key in refs:
        path = event_root.joinpath(*key.split("/"))
        try:
            path.resolve().relative_to(event_root.resolve())
        except ValueError:
            missing.add(key)
            continue
        if not path.is_file():
            missing.add(key)
    return refs, missing


def discover_candidates(event_root: Path, refs: set[str]):
    if not event_root.is_dir():
        raise FileNotFoundError(f"事件证据目录不存在：{event_root}")
    event_root = event_root.resolve()
    protected = set(refs)
    # 已被数据库引用的视频，其回放 sidecar 和同事件关键帧也必须保留。
    referenced_videos = []
    for key in refs:
        path = event_root.joinpath(*key.split("/"))
        if path.suffix.casefold() == ".mp4":
            referenced_videos.append(path)
    for video in referenced_videos:
        for companion in (Path(str(video) + ".replay.json"), video.with_suffix(".replay.json")):
            try:
                rel = companion.relative_to(event_root).as_posix()
                if companion.is_file() and not companion.is_symlink():
                    protected.add(norm_key(rel))
            except (ValueError, OSError):
                pass
        stem = video.stem
        if stem.casefold().endswith("_h264"):
            stem = stem[:-5]
        try:
            for frame in video.parent.glob(stem + "_frame_*"):
                if frame.is_file():
                    protected.add(norm_key(frame.relative_to(event_root).as_posix()))
        except OSError:
            pass

    candidates = []
    for path in event_root.rglob("*"):
        if path.is_symlink() or not path.is_file() or path.suffix.casefold() not in SUPPORTED_SUFFIXES:
            continue
        if ".tmp." in path.name.casefold() or path.name.casefold().endswith(".tmp"):
            continue
        try:
            relative = path.relative_to(event_root).as_posix()
        except (ValueError, OSError):
            continue
        key = norm_key(relative)
        if key in protected:
            continue
        stat = path.stat()
        candidates.append({
            "path": path,
            "relative": relative,
            "key": key,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "suffix": path.suffix.casefold(),
            "reason": "在当前业务数据库文本字段中未发现引用；隔离前仍需人工预览",
        })
    candidates.sort(key=lambda x: x["mtime"], reverse=True)
    return candidates, protected


class EvidenceCleanupCenter:
    def __init__(self, root):
        self.root = root
        self.root.title("灵瞳智声 · 证据清理中心")
        self.root.geometry("1180x760")
        self.root.minsize(900, 600)
        self.candidates = []
        self.filtered = []
        self.item_by_iid = {}
        self.last_scan = None
        self._build_ui()
        self.root.after(300, self.scan)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")
        ttk.Button(top, text="扫描证据与数据库关联", command=self.scan).pack(side="left", padx=(0, 8))
        ttk.Button(top, text="导出盘点 CSV…", command=self.export_csv).pack(side="left", padx=4)
        ttk.Button(top, text="隔离所选文件（可恢复）", command=self.quarantine_selected).pack(side="left", padx=4)
        ttk.Button(top, text="恢复隔离批次…", command=self.restore_batch_dialog).pack(side="left", padx=4)
        self.status = tk.StringVar(value="准备扫描。扫描阶段不会修改任何文件或数据库。")
        ttk.Label(self.root, textvariable=self.status, padding=(10, 0), wraplength=1100).pack(fill="x")

        filter_row = ttk.Frame(self.root, padding=(10, 8))
        filter_row.pack(fill="x")
        ttk.Label(filter_row, text="筛选（日期、文件名、扩展名）：").pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self.apply_filter())
        ttk.Entry(filter_row, textvariable=self.filter_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Label(filter_row, text="双击文件可用系统默认程序打开").pack(side="right")

        panes = ttk.Panedwindow(self.root, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes, padding=10)
        panes.add(left, weight=4)
        panes.add(right, weight=2)

        cols = ("relative", "type", "mb", "date")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("relative", text="相对路径")
        self.tree.heading("type", text="类型")
        self.tree.heading("mb", text="大小 MB")
        self.tree.heading("date", text="修改时间")
        self.tree.column("relative", width=470, anchor="w")
        self.tree.column("type", width=65, anchor="center")
        self.tree.column("mb", width=80, anchor="e")
        self.tree.column("date", width=140, anchor="center")
        yscroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(left, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self.preview_selected)
        self.tree.bind("<Double-1>", self.open_selected)

        ttk.Label(right, text="文件信息 / 预览", font=("", 11, "bold")).pack(anchor="w")
        self.preview_text = tk.Text(right, height=10, wrap="word", state="disabled")
        self.preview_text.pack(fill="x", pady=(6, 8))
        self.preview_image = ttk.Label(right, text="选择 JPG/PNG 可查看关键帧预览", anchor="center")
        self.preview_image.pack(fill="both", expand=True)
        self.preview_image.configure(background="#20252b")
        self._preview_photo = None
        ttk.Label(
            right,
            text="安全原则：只列出数据库未发现引用的候选文件；隔离操作会移动文件并写入清单，不做永久删除。正式证据或来源不明文件请勿清理。",
            wraplength=300,
        ).pack(anchor="w", pady=(8, 0))

    def scan(self):
        if getattr(self, "_scan_in_progress", False):
            return
        self._scan_in_progress = True
        self.status.set("正在后台扫描数据库引用和事件文件……窗口仍可操作；扫描期间请勿移动证据文件。")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        try:
            refs, missing = scan_database_references(DB_PATH, EVENT_ROOT)
            candidates, protected = discover_candidates(EVENT_ROOT, refs)
            result = (refs, missing, candidates, protected)
            self.root.after(0, lambda: self._scan_finished(result, None))
        except Exception as exc:
            error_text = str(exc)
            self.root.after(0, lambda: self._scan_finished(None, error_text))

    def _scan_finished(self, result, error):
        self._scan_in_progress = False
        if error:
            self.status.set(f"扫描失败：{error}")
            messagebox.showerror("扫描失败", error)
            return
        refs, missing, candidates, protected = result
        self.candidates = candidates
        self.last_scan = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "references": refs,
            "protected": protected,
            "missing": missing,
        }
        total_bytes = sum(x["size"] for x in candidates)
        self.status.set(
            f"扫描完成：事件目录 {EVENT_ROOT}；数据库引用路径 {len(refs):,} 条，"
            f"受保护文件关联 {len(protected):,} 个，候选 {len(candidates):,} 个 / "
            f"{total_bytes / (1024**3):.2f} GB，数据库引用缺失 {len(missing):,} 条。"
            "候选仅代表在已扫描数据库文本中未发现引用，不代表一定无用。"
        )
        self.apply_filter()

    def apply_filter(self):
        query = self.filter_var.get().strip().casefold()
        if query:
            self.filtered = [x for x in self.candidates if query in x["relative"].casefold()]
        else:
            self.filtered = list(self.candidates)
        self.tree.delete(*self.tree.get_children())
        self.item_by_iid.clear()
        # 控制一次渲染数量，避免上万条记录卡住窗口；筛选框可搜索完整候选集合。
        shown = self.filtered[:3000]
        for i, item in enumerate(shown):
            iid = f"f{i}"
            self.item_by_iid[iid] = item
            self.tree.insert("", "end", iid=iid, values=(
                item["relative"], item["suffix"], f'{item["size"] / (1024**2):.2f}',
                datetime.fromtimestamp(item["mtime"]).strftime("%Y-%m-%d %H:%M"),
            ))
        extra = f"（当前筛选命中 {len(self.filtered):,} 个，仅显示前 3,000 个）" if len(self.filtered) > 3000 else ""
        if self.last_scan:
            self.status.set(self.status.get().split(" 当前筛选：")[0] + f" 当前筛选：{len(self.filtered):,} 个{extra}")

    def selected_items(self):
        return [self.item_by_iid[iid] for iid in self.tree.selection() if iid in self.item_by_iid]

    def preview_selected(self, _event=None):
        items = self.selected_items()
        if not items:
            return
        item = items[0]
        path = item["path"]
        info = (
            f"路径：{path}\n相对路径：{item['relative']}\n类型：{item['suffix']}\n"
            f"大小：{item['size'] / (1024**2):.2f} MB\n"
            f"修改时间：{datetime.fromtimestamp(item['mtime']).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"判定依据：{item['reason']}\n注意：数据库未引用不等于无价值，请确认后再隔离。"
        )
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", info)
        self.preview_text.configure(state="disabled")
        self._preview_photo = None
        if item["suffix"] in {".jpg", ".jpeg", ".png"}:
            try:
                from PIL import Image, ImageTk
                image = Image.open(path)
                image.thumbnail((340, 360))
                self._preview_photo = ImageTk.PhotoImage(image)
                self.preview_image.configure(image=self._preview_photo, text="")
            except Exception as exc:
                self.preview_image.configure(image="", text=f"无法预览图片：{exc}")
        else:
            self.preview_image.configure(image="", text="视频 / JSON 文件：可双击条目使用系统默认程序打开")

    def open_selected(self, _event=None):
        items = self.selected_items()
        if not items:
            return
        path = str(items[0]["path"])
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen([path], shell=False)
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def export_csv(self):
        if not self.candidates:
            messagebox.showinfo("没有数据", "请先扫描证据目录。")
            return
        path = filedialog.asksaveasfilename(
            title="导出证据盘点 CSV", defaultextension=".csv",
            initialdir=str(API_ROOT / "output"),
            filetypes=[("CSV 文件", "*.csv")]
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["relative_path", "type", "size_bytes", "modified_time", "reason"])
                for item in self.candidates:
                    writer.writerow([item["relative"], item["suffix"], item["size"],
                                     datetime.fromtimestamp(item["mtime"]).isoformat(timespec="seconds"),
                                     item["reason"]])
            messagebox.showinfo("导出完成", f"已导出 {len(self.candidates):,} 条候选记录：\n{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def quarantine_selected(self):
        selected = self.selected_items()
        if not selected:
            messagebox.showinfo("未选择文件", "请先在列表中选择要隔离的候选文件。")
            return
        total = sum(x["size"] for x in selected)
        if not messagebox.askyesno(
            "确认移入隔离区",
            f"即将把选中的 {len(selected)} 个文件（约 {total / (1024**3):.2f} GB）移动到可恢复隔离区。\n"
            "不会永久删除文件，也不会修改数据库。\n"
            "请确认这些确实是无用测试证据；继续吗？"
        ):
            return
        batch_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_root = QUARANTINE_ROOT / batch_name
        moved = []
        skipped = []
        try:
            batch_root.mkdir(parents=True, exist_ok=False)
            # 若选择未引用视频，自动一并隔离其未引用的 replay sidecar。
            selected_paths = {x["path"].resolve() for x in selected}
            candidate_paths = {x["path"].resolve() for x in self.candidates}
            for item in selected:
                p = item["path"]
                if p.suffix.casefold() == ".mp4":
                    sidecar = Path(str(p) + ".replay.json")
                    if sidecar.resolve() in candidate_paths and sidecar.is_file():
                        selected_paths.add(sidecar.resolve())
            lookup = {x["path"].resolve(): x for x in self.candidates}
            for source in sorted(selected_paths, key=lambda x: str(x).casefold()):
                item = lookup.get(source)
                if item is None or not source.is_file():
                    skipped.append(str(source))
                    continue
                try:
                    rel = source.relative_to(EVENT_ROOT.resolve())
                except ValueError:
                    skipped.append(str(source))
                    continue
                destination = batch_root / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(destination))
                moved.append({
                    "relative_path": rel.as_posix(),
                    "quarantine_path": destination.relative_to(QUARANTINE_ROOT).as_posix(),
                    "size": item["size"],
                })
            manifest = {
                "format": "zhitong_evidence_quarantine_v1",
                "batch": batch_name,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "source_root": str(EVENT_ROOT),
                "items": moved,
                "skipped": skipped,
                "restored": False,
            }
            (batch_root / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            messagebox.showinfo(
                "隔离完成",
                f"已移动 {len(moved)} 个文件；跳过 {len(skipped)} 个。\n"
                f"隔离批次：{batch_root}\n需要恢复时点击“恢复隔离批次”。"
            )
            self.scan()
        except Exception as exc:
            messagebox.showerror(
                "隔离过程中发生错误",
                f"{exc}\n已移动的文件保留在：{batch_root}\n请勿手动删除该目录，可用恢复功能处理。"
            )
            self.scan()

    def restore_batch_dialog(self):
        if not QUARANTINE_ROOT.is_dir():
            messagebox.showinfo("没有隔离批次", "目前没有找到隔离区。")
            return
        batches = []
        for manifest_path in QUARANTINE_ROOT.glob("*/manifest.json"):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not data.get("restored"):
                    batches.append((data.get("created_at", ""), manifest_path, data))
            except Exception:
                continue
        batches.sort(reverse=True, key=lambda x: x[0])
        if not batches:
            messagebox.showinfo("没有待恢复批次", "隔离区中没有尚未恢复的批次。")
            return
        choice = tk.Toplevel(self.root)
        choice.title("选择要恢复的隔离批次")
        choice.geometry("760x400")
        ttk.Label(choice, text="选择一个批次，将其中文件恢复到原事件证据目录。若原路径已存在，将跳过该文件。", padding=10, wraplength=700).pack(fill="x")
        lb = tk.Listbox(choice, selectmode="browse")
        lb.pack(fill="both", expand=True, padx=10, pady=8)
        for created, manifest_path, data in batches:
            size = sum(int(x.get("size", 0)) for x in data.get("items", []))
            lb.insert("end", f"{created} | {len(data.get('items', []))} 个文件 | {size / (1024**3):.2f} GB | {manifest_path.parent.name}")
        def restore():
            selection = lb.curselection()
            if not selection:
                return
            created, manifest_path, data = batches[selection[0]]
            if not messagebox.askyesno("确认恢复", f"恢复批次 {data.get('batch')} 中的 {len(data.get('items', []))} 个文件？", parent=choice):
                return
            restored = 0
            skipped = []
            for item in data.get("items", []):
                src = QUARANTINE_ROOT / item["quarantine_path"]
                dst = EVENT_ROOT / item["relative_path"]
                try:
                    src.resolve().relative_to(QUARANTINE_ROOT.resolve())
                    dst.resolve().relative_to(EVENT_ROOT.resolve())
                except ValueError:
                    skipped.append(item["relative_path"])
                    continue
                if not src.is_file() or dst.exists():
                    skipped.append(item["relative_path"])
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                restored += 1
            data["restored"] = not any((QUARANTINE_ROOT / x["quarantine_path"]).exists() for x in data.get("items", []))
            data["restore_time"] = datetime.now().isoformat(timespec="seconds")
            data["restore_skipped"] = skipped
            manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("恢复完成", f"已恢复 {restored} 个文件，跳过 {len(skipped)} 个。", parent=choice)
            choice.destroy()
            self.scan()
        ttk.Button(choice, text="恢复选中批次", command=restore).pack(pady=(0, 10))

def main():
    root = tk.Tk()
    EvidenceCleanupCenter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
