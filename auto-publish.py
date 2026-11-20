#!/usr/bin/env python3
"""
auto-publish.py — публикует пост в блог без интерактивного ввода.

Использование:
    python3 auto-publish.py путь/к/посту.md

Скрипт:
1. Читает файл поста (первая строка должна быть "# Заголовок").
2. Копирует его в posts/<slug>.md.
3. Копирует в post.md (для совместимости с add_post.py).
4. Создаёт Discussion в x2v0/x2v0.github.io через GitHub API.
5. Обновляет tree.json (без дубликатов).
6. Запускает тесты tests/site.test.js.
7. Коммитит и пушит в main.
"""
import json
import pathlib
import datetime
import subprocess
import sys
import os

ROOT = pathlib.Path(__file__).parent
TREE = ROOT / "tree.json"
POSTS = ROOT / "posts"
DISCUSSION_REPO = "x2v0/x2v0.github.io"
DISCUSSION_CATEGORY_ID = "DIC_kwDOFNRB_84DJ5jS"


def slugify(text: str) -> str:
    text = text.lower().replace(" ", "_").replace("ё", "e").replace("й", "i")
    text = "".join(c for c in text if c.isalnum() or c in "_-")
    return text[:40]


def load_token():
    p = pathlib.Path.home() / "git.txt"
    if p.exists():
        return p.read_text().strip()
    return os.environ.get("GITHUB_TOKEN")


def create_discussion(token: str, title: str, body: str):
    import requests
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}

    repo_query = 'query { repository(owner: "x2v0", name: "x2v0.github.io") { id } }'
    r = requests.post(url, json={"query": repo_query}, headers=headers)
    data = r.json()
    if "data" not in data:
        print(f"[WARN] Не удалось получить repo_id: {data}")
        return None
    repo_id = data["data"]["repository"]["id"]

    create_query = '''
    mutation($repoId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {repositoryId: $repoId, categoryId: $categoryId, title: $title, body: $body}) {
        discussion { number }
      }
    }
    '''
    variables = {
        "repoId": repo_id,
        "categoryId": DISCUSSION_CATEGORY_ID,
        "title": title,
        "body": body,
    }
    r = requests.post(url, json={"query": create_query, "variables": variables}, headers=headers)
    data = r.json()
    if "errors" in data:
        print(f"[WARN] Discussion не создан: {data['errors'][0]['message']}")
        return None
    return data["data"]["createDiscussion"]["discussion"]["number"]


def main():
    if len(sys.argv) != 2:
        print("Использование: python3 auto-publish.py путь/к/посту.md")
        sys.exit(1)

    src = pathlib.Path(sys.argv[1])
    if not src.exists():
        print(f"[ERROR] Файл не найден: {src}")
        sys.exit(1)

    content = src.read_text(encoding="utf-8").strip()
    if not content:
        print("[ERROR] Файл пуст")
        sys.exit(1)

    first_line = content.split("\n")[0]
    subject = first_line[2:].strip() if first_line.startswith("# ") else src.stem

    slug = slugify(subject)
    post_path = POSTS / f"{slug}.md"
    POSTS.mkdir(exist_ok=True)
    post_path.write_text(content, encoding="utf-8")
    print(f"[OK] Пост сохранён: {post_path}")

    (ROOT / "post.md").write_text(content, encoding="utf-8")
    print("[OK] post.md обновлён")

    tree = json.loads(TREE.read_text(encoding="utf-8")) if TREE.exists() else []

    for p in tree:
        if p.get("subject") == subject:
            print(f"[WARN] Пост с таким subject уже есть в tree.json (id={p.get('id')}). Обновляю...")
            tree.remove(p)
            break

    max_id = 0
    for p in tree:
        if p.get("id", "").startswith("post-"):
            try:
                n = int(p["id"].split("-")[1])
                if n > max_id:
                    max_id = n
            except ValueError:
                pass
    new_id = f"post-{max_id + 1}"

    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
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

    token = load_token()
    if token:
        print("\n=== Создание Discussion ===")
        num = create_discussion(token, new_id, f"Обсуждение поста: {subject}")
        if num:
            new_post["discussion_number"] = num
            print(f"[OK] Discussion #{num} создан для {new_id}")
    else:
        print("[WARN] Токен не найден (~/git.txt или GITHUB_TOKEN). Discussion не создан.")

    tree.insert(0, new_post)
    TREE.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] tree.json обновлён (всего постов: {len(tree)})")

    print("\n=== Генерация HTML (collect.py) ===")
    if (ROOT / "collect.py").exists():
        r = subprocess.run(["python3", "collect.py"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print("[WARN] collect.py завершился с ошибкой:")
            print(r.stdout)
            print(r.stderr)
        else:
            print("[OK] HTML сгенерирован")
    else:
        print("[SKIP] collect.py не найден")

    print("\n=== Тесты ===")
    r = subprocess.run(["node", "--test", "tests/site.test.js"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print("[FAIL] Тесты провалены. Пуш отменён.")
        print(r.stdout)
        print(r.stderr)
        sys.exit(1)
    print("[OK] Тесты пройдены")

    print("\n=== Git push ===")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    r = subprocess.run(
        ["git", "-c", "user.name=blog-bot", "-c", "user.email=blog-bot@local",
         "commit", "-m", f"feat: add post '{subject}'"],
        cwd=ROOT, capture_output=True, text=True,
    )
    print(r.stdout.strip())
    if r.returncode != 0 and "nothing to commit" not in r.stdout:
        print(r.stderr)
        sys.exit(1)

    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
    print("[OK] Запушено в main")

    if new_post.get("discussion_number"):
        print(f"\n🔗 Discussion: https://github.com/{DISCUSSION_REPO}/discussions/{new_post['discussion_number']}")
    print("✓ Готово. Пост опубликован.")


if __name__ == "__main__":
    main()