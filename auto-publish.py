#!/usr/bin/env python3
"""auto-publish.py — публикует файл .md в блог (без интерактивных запросов)."""
import json
import pathlib
import sys
import subprocess
import os

from blog_utils import slugify, extract_subject, load_tree, save_tree, upsert_post

ROOT = pathlib.Path(__file__).parent
TREE = ROOT / "tree.json"
DISCUSSION_REPO = "x2v0/x2v0.github.io"
DISCUSSION_CATEGORY_ID = "DIC_kwDOFNRB_84DJ5jS"


def load_token():
    p = pathlib.Path.home() / "git.txt"
    if p.exists():
        return p.read_text().strip()
    return os.environ.get("GITHUB_TOKEN")


def create_discussion(token: str, title: str, body: str):
    import requests
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(url, json={"query": 'query { repository(owner: "x2v0", name: "x2v0.github.io") { id } }'}, headers=headers)
    data = r.json()
    if "data" not in data:
        print(f"[WARN] repo_id: {data}")
        return None
    repo_id = data["data"]["repository"]["id"]
    q = '''mutation($r: ID!, $c: ID!, $t: String!, $b: String!) {
      createDiscussion(input: {repositoryId: $r, categoryId: $c, title: $t, body: $b}) {
        discussion { number }
      }
    }'''
    r = requests.post(url, json={"query": q, "variables": {"r": repo_id, "c": DISCUSSION_CATEGORY_ID, "t": title, "b": body}}, headers=headers)
    data = r.json()
    if "errors" in data:
        print(f"[WARN] Discussion: {data['errors'][0]['message']}")
        return None
    return data["data"]["createDiscussion"]["discussion"]["number"]


def main():
    if len(sys.argv) != 2:
        print("Использование: python3 auto-publish.py путь/к/посту.md")
        return 1
    src = pathlib.Path(sys.argv[1])
    if not src.exists():
        print(f"[ERROR] {src} не найден")
        return 1
    content = src.read_text(encoding="utf-8").strip()
    if not content:
        print("[ERROR] файл пуст")
        return 1

    subject = extract_subject(content, src.stem)
    slug = slugify(subject)
    post_path = ROOT / "posts" / f"{slug}.md"
    (ROOT / "posts").mkdir(exist_ok=True)
    post_path.write_text(content, encoding="utf-8")
    print(f"[OK] posts/{slug}.md")

    (ROOT / "post.md").write_text(content, encoding="utf-8")
    print("[OK] post.md")

    tree = load_tree(TREE)
    post, is_new = upsert_post(tree, subject, content)
    if is_new:
        print(f"[OK] Новый пост: {post['id']}")
    else:
        print(f"[OK] Обновлён существующий: {post['id']} (без дубликата)")

    token = load_token()
    if "discussion_number" in post:
        print(f"[SKIP] Discussion уже есть: #{post['discussion_number']}")
    elif token:
        num = create_discussion(token, post["id"], f"Обсуждение поста: {subject}")
        if num:
            post["discussion_number"] = num
            print(f"[OK] Discussion #{num}")

    save_tree(TREE, tree)
    print(f"[OK] tree.json ({len(tree)} постов)")

    # collect.py
    if (ROOT / "collect.py").exists():
        print("\n=== collect.py ===")
        r = subprocess.run(["python3", "collect.py"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print("[WARN] collect.py:", r.stderr.strip()[:200])
        else:
            print("[OK] HTML сгенерирован")

    # тесты
    tests_dir = pathlib.Path.home() / "x2v0.github.io"
    if (tests_dir / "tests" / "site.test.js").exists():
        print("\n=== Тесты ===")
        r = subprocess.run(["node", "--test", "tests/site.test.js"], cwd=tests_dir, capture_output=True, text=True)
        if r.returncode != 0:
            print("[FAIL] тесты провалены")
            print(r.stdout)
            return 1
        print("[OK] тесты пройдены")
    else:
        print(f"[WARN] тесты не найдены в {tests_dir}/tests/site.test.js")

    print("\n=== git push ===")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    r = subprocess.run(["git", "-c", "user.name=blog-bot", "-c", "user.email=blog-bot@local",
                        "commit", "-m", f"feat: publish '{subject}'"], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0 and "nothing to commit" not in r.stdout:
        print(r.stderr)
        return 1
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
    print("[OK] запушено")
    if post.get("discussion_number"):
        print(f"\n🔗 https://github.com/{DISCUSSION_REPO}/discussions/{post['discussion_number']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())