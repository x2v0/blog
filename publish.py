import json
import pathlib
import datetime
import sys
import subprocess
import requests
import os

def run_tests():
    """Запускает тесты из основного репозитория перед пушем."""
    print("\n=== Запуск тестов (site.test.js) ===")
    try:
        tests_dir = pathlib.Path.home() / "x2v0.github.io"
        result = subprocess.run(
            ["node", "--test", "tests/site.test.js"],
            cwd=tests_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("❌ ТЕСТЫ ПРОВАЛЕНЫ! Пуш отменён.")
            print(result.stdout)
            print(result.stderr)
            return False
        print("✅ Все тесты пройдены.")
        return True
    except Exception as e:
        print(f"⚠ Не удалось запустить тесты: {e}")
        return True

def main():
    post_file = "post.md"
    if not pathlib.Path(post_file).exists():
        print(f"⚠ Файл {post_file} не найден. Создай его с текстом поста.")
        return

    content = pathlib.Path(post_file).read_text(encoding="utf-8").strip()
    if not content:
        print("⚠ Файл пуст.")
        return

    first_line = content.split("\n")[0]
    if first_line.startswith("# "):
        subject = first_line[2:].strip()
    else:
        subject = "Без названия"

    slug = subject.lower().replace(" ", "_").replace("ё", "e").replace("й", "i")
    slug = "".join(c for c in slug if c.isalnum() or c in "_-")[:40]
    filename = f"posts/{slug}.md"

    pathlib.Path(filename).write_text(content, encoding="utf-8")
    print(f"✓ Пост сохранён: {filename}")

    tree_path = pathlib.Path("tree.json")
    tree = json.loads(tree_path.read_text(encoding="utf-8")) if tree_path.exists() else []

    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # ИСПОЛЬЗУЕМ ЧИСЛОВОЙ ID (для Giscus)
    max_id = 0
    for p in tree:
        if p.get("id", "").startswith("post-"):
            try:
                num = int(p["id"].split("-")[1])
                if num > max_id: max_id = num
            except: pass
    new_id = f"post-{max_id + 1}"
    new_post = {
        "id": new_id,
        "in_reply_to": "",
        "references": [],
        "from": "Автор",
        "subject": subject,
        "date": today,
        "body": content,
        "children": []
    }

    # === СОЗДАНИЕ DISCUSSION И ПОЛУЧЕНИЕ НОМЕРА ===
    token = None
    token_path = pathlib.Path.home() / "git.txt"
    if token_path.exists():
        token = token_path.read_text().strip()

    disc_number = None
    if token:
        print("\n=== Создание Discussion и получение номера ===")
        try:
            url = "https://api.github.com/graphql"
            headers = {"Authorization": f"Bearer {token}"}

            # Получаем ID репозитория
            repo_query = 'query { repository(owner: "x2v0", name: "x2v0.github.io") { id } }'
            repo_resp = requests.post(url, json={"query": repo_query}, headers=headers)

            if "data" in repo_resp.json():
                repo_id = repo_resp.json()["data"]["repository"]["id"]

                # Создаём Discussion и запрашиваем номер (number)
                create_query = """
                mutation($repoId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
                  createDiscussion(input: {repositoryId: $repoId, categoryId: $categoryId, title: $title, body: $body}) {
                    discussion { id number }
                  }
                }
                """
                create_vars = {
                    "repoId": repo_id,
                    "categoryId": "DIC_kwDOFNRB_84DJ5jS",
                    "title": new_id,
                    "body": f"Обсуждение поста: {subject}"
                }
                create_resp = requests.post(url, json={"query": create_query, "variables": create_vars}, headers=headers)

                if "errors" in create_resp.json():
                    print(f"⚠ Discussion не создан: {create_resp.json()['errors'][0]['message']}")
                else:
                    disc_number = create_resp.json()["data"]["createDiscussion"]["discussion"]["number"]
                    print(f"✓ Discussion #{disc_number} создан для {new_id}")
                    new_post["discussion_number"] = disc_number # Сохраняем номер в пост
        except Exception as e:
            print(f"⚠ Не удалось создать Discussion: {e}")
    else:
        print("⚠ Токен не найден (~/git.txt). Discussion не создан.")

    # === СОХРАНЕНИЕ TREE.JSON ===
    existing_ids = [n.get("id", "") for n in tree]
    if new_id in existing_ids:
        print(f"⚠ Пост с id {new_id} уже есть. Обновляю...")
        for i, n in enumerate(tree):
            if n.get("id") == new_id:
                tree[i] = new_post
                break
    else:
        tree.insert(0, new_post)

    tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ tree.json обновлён (всего постов: {len(tree)})")

    # === ЗАПУСК ТЕСТОВ ПЕРЕД ПУШЕМ ===
    if not run_tests():
        print("⚠ Публикация остановлена из-за ошибок в тестах.")
        return

    # === ПУШ НА GITHUB ===
    print("\n=== Пуш на GitHub ===")
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m", f"feat: add post '{subject}'"])
    subprocess.run(["git", "push", "origin", "main"])
    
    if disc_number:
        print(f"\n🔗 Прямая ссылка на обсуждение: https://github.com/x2v0/x2v0.github.io/discussions/{disc_number}")
    print("✓ Готово! Пост опубликован.")

if __name__ == "__main__":
    main()
