#!/usr/bin/env python3
"""Публикует пост из post.md в блог. Обновляет существующий, не создаёт дубликаты."""
import json
import pathlib
import sys
import subprocess
import requests
import os

from blog_utils import slugify, extract_subject, load_tree, save_tree, upsert_post

ROOT = pathlib.Path(__file__).parent
TREE = ROOT / "tree.json"
DISCUSSION_CATEGORY_ID = "DIC_kwDOFNRB_84DJ5jS"
DISCUSSION_REPO = "x2v0/x2v0.github.io"


def run_tests():
    print("\n=== Тесты ===")
    tests_dir = pathlib.Path.home() / "x2v0.github.io"
    if not (tests_dir / "tests" / "site.test.js").exists():
        print(f"[WARN] тесты не найдены в {tests_dir}/tests/site.test.js")
        return True
    r = subprocess.run(["node", "--test", "tests/site.test.js"], cwd=tests_dir, capture_output=True, text=True)
    if r.returncode != 0:
        print("[FAIL] тесты провалены, пуш отменён")
        print(r.stdout)
        print(r.stderr)
        return False
    print("[OK] тесты пройдены")
    return True


def create_discussion(token: str, title: str, body: str):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(url, json={"query": 'query { repository(owner: "x2v0", name: "x2v0.github.io") { id } }'}, headers=headers)
    data = r.json()
    if "data" not in data:
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
    post_file = ROOT / "post.md"
    if not post_file.exists():
        print(f"[ERROR] {post_file} не найден")
        return 1
    content = post_file.read_text(encoding="utf-8").strip()
    if not content:
        print("[ERROR] post.md пуст")
        return 1

    subject = extract_subject(content)
    slug = slugify(subject)
    (ROOT / "posts").mkdir(exist_ok=True)
    (ROOT / "posts" / f"{slug}.md").write_text(content, encoding="utf-8")
    print(f"[OK] posts/{slug}.md")

    tree = load_tree(TREE)
    post, is_new = upsert_post(tree, subject, content)
    if is_new:
        print(f"[OK] Новый пост: {post['id']}")
    else:
        print(f"[OK] Обновлён существующий: {post['id']} (без дубликата)")

    # Discussion — только если его ещё нет
    token_path = pathlib.Path.home() / "git.txt"
    if "discussion_number" in post:
        print(f"[SKIP] Discussion уже есть: #{post['discussion_number']}")
    elif token_path.exists():
        token = token_path.read_text().strip()
        num = create_discussion(token, post["id"], f"Обсуждение поста: {subject}")
        if num:
            post["discussion_number"] = num
            print(f"[OK] Discussion #{num}")

    save_tree(TREE, tree)
    print(f"[OK] tree.json ({len(tree)} постов)")

    if not run_tests():
        return 1

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
    return 0


if __name__ == "__main__":
    sys.exit(main())