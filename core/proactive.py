"""EVA-nın proaktiv yoxlama, dəyişiklik aşkarlama və bildiriş siyasəti."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable

from actions.agenda import get_daily_agenda
from actions.email import search_emails
from actions.whatsapp_read_action import read_whatsapp_conversations
from memory.memory_manager import load_memory


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STATE_FILE = BASE_DIR / ".eva" / "proactive-state.json"
DEFAULT_INTERVAL = 120
DEFAULT_RATE_LIMIT = 3
DEFAULT_COOLDOWN_MINUTES = 360
DEFAULT_QUIET_START = "23:00"
DEFAULT_QUIET_END = "07:00"


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _item_id(item: dict[str, Any], source: str) -> str:
    for key in ("id", "gmail_message_id", "google_task_id", "event_id", "conversation_id"):
        value = str(item.get(key, "") or "").strip()
        if value:
            return f"{source}:{value}"
    return f"{source}:{_fingerprint(item)}"


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        # Preserve an existing timezone. Converting to the host's local timezone
        # makes UTC timestamps compare incorrectly on other hosts.
        return parsed
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None


def _event_title(source: str, item: dict[str, Any]) -> str:
    if source == "gmail":
        subject = str(item.get("subject", "")).strip()
        sender = str(item.get("from", "")).strip()
        return f"Yeni email: {subject or '(mövzusuz)'}" + (f" — {sender}" if sender else "")
    if source == "whatsapp":
        title = str(item.get("title") or item.get("contact_name") or "WhatsApp").strip()
        return f"WhatsApp: {title}"
    if source == "calendar":
        return f"Təqvim: {str(item.get('title') or item.get('summary') or 'Yeni hadisə').strip()}"
    if source == "tasks":
        return f"Task: {str(item.get('title') or item.get('name') or 'Yeni task').strip()}"
    return "Yaddaş dəyişdi"


def _event_text(source: str, item: dict[str, Any]) -> str:
    if source == "gmail":
        subject = str(item.get("subject") or "(mövzusuz)").strip()
        sender = str(item.get("from") or "").strip()
        return f"Yeni email gəldi: {subject}" + (f", göndərən {sender}" if sender else "") + "."
    if source == "whatsapp":
        title = str(item.get("title") or item.get("contact_name") or "bir söhbətdən").strip()
        unread = int(item.get("unread_count", 0) or 0)
        return f"WhatsApp-da {title} söhbətində yeni mesaj var" + (f" ({unread} oxunmamış)." if unread else ".")
    if source == "calendar":
        title = str(item.get("title") or item.get("summary") or "Yeni hadisə").strip()
        start = str(item.get("start") or item.get("date") or "").strip()
        return f"Təqvimdə yaxın hadisə: {title}" + (f" — {start}." if start else ".")
    if source == "tasks":
        title = str(item.get("title") or item.get("name") or "Task").strip()
        due = str(item.get("due") or item.get("date") or "").strip()
        return f"Task diqqət tələb edir: {title}" + (f" — son tarix {due}." if due else ".")
    return "Yaddaşda dəyişiklik aşkarlandı."


def _quiet_now(now: datetime, start: str, end: str) -> bool:
    try:
        start_h, start_m = (int(x) for x in start.split(":", 1))
        end_h, end_m = (int(x) for x in end.split(":", 1))
        current = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        if start_minutes == end_minutes:
            return False
        if start_minutes < end_minutes:
            return start_minutes <= current < end_minutes
        return current >= start_minutes or current < end_minutes
    except (ValueError, TypeError):
        return False


class NotificationPolicy:
    """Bildirişlərin nə vaxt və hansı tezlikdə istifadəçiyə göstəriləcəyini müəyyən edir."""

    def __init__(self, rate_limit: int = DEFAULT_RATE_LIMIT, cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES, quiet_start: str = DEFAULT_QUIET_START, quiet_end: str = DEFAULT_QUIET_END) -> None:
        self.rate_limit = max(1, int(rate_limit))
        self.cooldown = timedelta(minutes=max(0, int(cooldown_minutes)))
        self.quiet_start = quiet_start
        self.quiet_end = quiet_end

    def _eligible(self, event: dict[str, Any], now: datetime) -> bool:
        source = str(event.get("source", ""))
        item = event.get("item") or {}
        if source in {"gmail", "whatsapp"}:
            return True
        if source == "calendar":
            start = _parse_datetime(item.get("start") or item.get("date"))
            if start is None:
                return bool(event.get("changed", False))
            return start <= now + timedelta(minutes=60) and start >= now - timedelta(minutes=15)
        if source == "tasks":
            due = _parse_datetime(item.get("due") or item.get("date"))
            if due is None:
                return False
            return due <= now + timedelta(hours=24)
        if source == "memory":
            text = " ".join(str(item.get(key, "")) for key in ("title", "value", "notes", "due", "type")).casefold()
            return any(word in text for word in ("urgent", "vacib", "təcili", "deadline")) or bool(item.get("due"))
        return False

    def choose(self, pending: dict[str, dict[str, Any]], history: dict[str, str], now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now().astimezone()
        if _quiet_now(now, self.quiet_start, self.quiet_end):
            return []
        recent = 0
        for timestamp in history.values():
            parsed = _parse_datetime(timestamp)
            if parsed and now - parsed <= timedelta(hours=1):
                recent += 1
        if recent >= self.rate_limit:
            return []
        selected: list[dict[str, Any]] = []
        for key, event in pending.items():
            last_sent = _parse_datetime(str(history.get(key, "")))
            if last_sent and now - last_sent < self.cooldown:
                continue
            if not self._eligible(event, now):
                continue
            selected.append(event)
            if len(selected) + recent >= self.rate_limit:
                break
        return selected


class ProactiveEngine:
    """Mənbə snapshot-larını müqayisə edir və pending proaktiv hadisələri saxlayır."""

    def __init__(self, state_file: str | Path | None = None, policy: NotificationPolicy | None = None) -> None:
        self.state_file = Path(state_file or os.getenv("EVA_PROACTIVE_STATE_FILE") or DEFAULT_STATE_FILE)
        self.policy = policy or NotificationPolicy(
            rate_limit=int(os.getenv("EVA_PROACTIVE_RATE_LIMIT", DEFAULT_RATE_LIMIT)),
            cooldown_minutes=int(os.getenv("EVA_PROACTIVE_COOLDOWN_MINUTES", DEFAULT_COOLDOWN_MINUTES)),
            quiet_start=os.getenv("EVA_PROACTIVE_QUIET_START", DEFAULT_QUIET_START),
            quiet_end=os.getenv("EVA_PROACTIVE_QUIET_END", DEFAULT_QUIET_END),
        )
        self._lock = threading.Lock()
        self._collection_failures: set[str] = set()

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.state_file.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                value.setdefault("snapshots", {})
                value.setdefault("pending", {})
                value.setdefault("history", {})
                return value
        except Exception:
            pass
        return {"snapshots": {}, "pending": {}, "history": {}}

    def _save(self, state: dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_file.with_suffix(self.state_file.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_file)

    @staticmethod
    def _source_snapshot(source: str, result: Any) -> dict[str, Any]:
        if source == "memory":
            return {"fingerprint": _fingerprint(result)}
        items = result if isinstance(result, list) else []
        normalized: dict[str, dict[str, Any]] = {}
        for item in items:
            if isinstance(item, dict):
                normalized[_item_id(item, source)] = item
        return {"items": normalized}

    def _collect(self) -> dict[str, Any]:
        sources: dict[str, Any] = {}
        self._collection_failures = set()
        try:
            result = search_emails("in:inbox is:unread", 20)
            sources["gmail"] = result.get("data", []) if result.get("status") != "error" else []
            if result.get("status") == "error":
                self._collection_failures.add("gmail")
        except Exception:
            sources["gmail"] = []
            self._collection_failures.add("gmail")
        try:
            result = read_whatsapp_conversations()
            sources["whatsapp"] = result.get("data", []) if result.get("status") != "error" else []
            if result.get("status") == "error":
                self._collection_failures.add("whatsapp")
        except Exception:
            sources["whatsapp"] = []
            self._collection_failures.add("whatsapp")
        try:
            result = get_daily_agenda(limit=50, date_text=datetime.now().astimezone().date().isoformat())
            if isinstance(result, dict) and result.get("status") == "error":
                raise RuntimeError("agenda source error")
            groups = result.get("meta", {}).get("groups", {}) if isinstance(result, dict) else {}
            sources["calendar"] = groups.get("calendar", [])
            sources["tasks"] = groups.get("tasks", [])
        except Exception:
            sources["calendar"] = []
            sources["tasks"] = []
            self._collection_failures.update({"calendar", "tasks"})
        try:
            sources["memory"] = load_memory()
        except Exception:
            sources["memory"] = {}
            self._collection_failures.add("memory")
        return sources

    def poll(self, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now().astimezone()
        with self._lock:
            state = self._load()
            sources = self._collect()
            snapshots = state["snapshots"]
            pending = state["pending"]
            history = state["history"]
            for source, raw in sources.items():
                if source in self._collection_failures:
                    continue
                current = self._source_snapshot(source, raw)
                previous = snapshots.get(source)
                if previous is not None:
                    if source == "memory":
                        if previous.get("fingerprint") != current.get("fingerprint"):
                            key = f"memory:{current['fingerprint']}"
                            pending[key] = {"key": key, "source": source, "item": {"value": "memory changed"}, "changed": True}
                    else:
                        old_items = previous.get("items", {})
                        for item_id, item in current.get("items", {}).items():
                            old_item = old_items.get(item_id)
                            changed = old_item is None or _fingerprint(old_item) != _fingerprint(item)
                            if source == "whatsapp":
                                old_unread = int((old_item or {}).get("unread_count", 0) or 0)
                                new_unread = int(item.get("unread_count", 0) or 0)
                                changed = new_unread > old_unread
                            if not changed:
                                continue
                            key = f"{item_id}:{_fingerprint(item)}"
                            pending[key] = {"key": key, "source": source, "item": item, "changed": old_item is not None}
                snapshots[source] = current
            selected = self.policy.choose(pending, history, now)
            for event in selected:
                key = str(event["key"])
                history[key] = now.isoformat()
                pending.pop(key, None)
                event["title"] = _event_title(str(event.get("source", "")), event.get("item") or {})
                event["text"] = _event_text(str(event.get("source", "")), event.get("item") or {})
            state["snapshots"] = snapshots
            state["pending"] = pending
            state["history"] = history
            state["last_poll"] = now.isoformat()
            self._save(state)
            return selected


class ProactiveScheduler:
    """ProactiveEngine-i daemon thread-də periodik icra edir."""

    def __init__(self, engine: ProactiveEngine, on_notification: Callable[[dict[str, Any]], None], interval: int = DEFAULT_INTERVAL) -> None:
        self.engine = engine
        self.on_notification = on_notification
        self.interval = max(10, int(interval))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="EVA-Proactive")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def poll_once(self) -> list[dict[str, Any]]:
        events = self.engine.poll()
        for event in events:
            try:
                self.on_notification(event)
            except Exception:
                pass
        return events

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception as exc:
                print(f"[EVA Proactive] ❌ {exc}")
            self._stop.wait(self.interval)
