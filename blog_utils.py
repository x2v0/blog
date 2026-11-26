"""Общие утилиты для публикации постов в блог."""
import json
import datetime
from pathlib import Path


def slugify(text: str) -> str:
    text = text.lower().replace(" ", "_").replace("ё", "e").replace("й", "i")
    text = "".join(c for c in text if c.isalnum() or c in "_-")
    return text[:40]


def extract_subject(content: str, fallback: str = "Без названия") -> str:
    first = content.split("\n", 1)[0] if content else ""
    if first.startswith("# "):
        return first[2:].strip()
    return fallback


def load_tree(tree_path: Path) -> list:
    if tree_path.exists():
        return json.loads(tree_path.read_text(encoding="utf-8"))
    return []


def save_tree(tree_path: Path, tree: list) -> None:
    tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")


def _post_num(post: dict) -> int:
    pid = post.get("id", "")
    if pid.startswith("post-"):
        try:
            return int(pid.split("-")[1])
        except ValueError:
            return -1
    return -1


def find_existing_post(tree: list, subject: str):
    """
    Ищет существующий пост по точному subject или по slug,
    вычисленному из первого заголовка body. Если дубликатов несколько,
    берёт самый новый (наибольший числовой ID).
    """
    slug = slugify(subject)
    matches = []
    for i, p in enumerate(tree):
        if p.get("subject") == subject:
            matches.append((i, p))
            continue
        body = p.get("body", "")
        first = body.split("\n", 1)[0] if body else ""
        if first.startswith("# ") and slugify(first[2:].strip()) == slug:
            matches.append((i, p))
    if not matches:
        return None, None
    matches.sort(key=lambda item: _post_num(item[1]), reverse=True)
    return matches[0]


def upsert_post(tree: list, subject: str, content: str):
    """
    Обновляет существующий или создаёт новый пост.
    При обновлении сохраняет id, discussion_number, children, references.
    Возвращает (post, is_new).
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    idx, existing = find_existing_post(tree, subject)
    if existing is not None:
        existing["body"] = content
        existing["date"] = today
        existing["subject"] = subject
        tree[idx] = existing
        return existing, False
    max_id = 0
    for p in tree:
        n = _post_num(p)
        if n > max_id:
            max_id = n
    new_id = f"post-{max_id + 1}"
    new_post = {
        "id": new_id,
        "in_reply_to": "",
        "references": [],
        "from": "Автор",
        "subject": subject,
        "date": today,
        "body": content,
        "children": [],
    }
    tree.insert(0, new_post)
    return new_post, True


def dedupe_tree(tree: list):
    """Удаляет дубликаты, оставляя самый новый. Возвращает (clean, removed_ids)."""
    by_slug = {}
    for p in tree:
        body = p.get("body", "")
        first = body.split("\n", 1)[0] if body else ""
        subj = first[2:].strip() if first.startswith("# ") else p.get("subject", "")
        slug = slugify(subj)
        if slug not in by_slug or _post_num(p) > _post_num(by_slug[slug]):
            by_slug[slug] = p
    clean_ids = {id(p) for p in by_slug.values()}
    removed = [p.get("id") for p in tree if id(p) not in clean_ids]
    clean = sorted(by_slug.values(), key=_post_num, reverse=True)
    return clean, removed