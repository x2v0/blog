import json
import pathlib
import datetime
import sys
import subprocess

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
    new_post = {
        "id": f"post-{slug}",
        "in_reply_to": "",
        "references": [],
        "from": "Автор",
        "subject": subject,
        "date": today,
        "body": content,
        "children": []
    }

    existing_ids = [n.get("id", "") for n in tree]
    if new_post["id"] in existing_ids:
        print(f"⚠ Пост с id {new_post['id']} уже есть. Обновляю...")
        for i, n in enumerate(tree):
            if n.get("id") == new_post["id"]:
                tree[i] = new_post
                break
    else:
        tree.insert(0, new_post)

    tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ tree.json обновлён (всего постов: {len(tree)})")

    print("\n=== Пуш на GitHub ===")
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m", f"feat: add post '{subject}'"])
    subprocess.run(["git", "push", "origin", "main"])
    print("✓ Готово! Пост опубликован.")

if __name__ == "__main__":
    main()
