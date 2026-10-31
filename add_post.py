import json
import pathlib
import datetime
import sys

def add_post():
    print("=== Добавление нового поста в блог ===\n")
    
    # 1. Спрашиваем название
    subject = input("Название поста (например, 'Как я учил Go'): ").strip()
    if not subject:
        print("⚠ Название не может быть пустым.")
        return
    
    # 2. Спрашиваем текст (многострочный)
    print("\nВведите текст поста в Markdown (закончите пустой строкой дважды):")
    lines = []
    while True:
        line = input()
        if line == "" and len(lines) > 0 and lines[-1] == "":
            break
        lines.append(line)
    body = "\n".join(lines).strip()
    
    if not body:
        print("⚠ Текст не может быть пустым.")
        return
    
    # 3. Создаём файл
    slug = subject.lower().replace(" ", "_").replace("ё", "e").replace("й", "i")
    slug = "".join(c for c in slug if c.isalnum() or c in "_-")[:40]
    filename = f"posts/{slug}.md"
    pathlib.Path(filename).write_text(f"# {subject}\n\n{body}", encoding="utf-8")
    print(f"\n✓ Файл создан: {filename}")
    
    # 4. Добавляем в tree.json
    tree_path = pathlib.Path("tree.json")
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    new_post = {
        "id": f"post-{slug}",
        "in_reply_to": "",
        "references": [],
        "from": "Автор",
        "subject": subject,
        "date": today,
        "body": f"# {subject}\n\n{body}",
        "children": []
    }
    
    tree.insert(0, new_post)  # новый пост — сверху
    tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Пост добавлен в tree.json (всего постов: {len(tree)})")
    
    # 5. Пушим
    print("\n=== Пуш на GitHub ===")
    import subprocess
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m", f"feat: add post '{subject}'"])
    subprocess.run(["git", "push", "origin", "main"])
    print("✓ Готово! Пост опубликован.")

if __name__ == "__main__":
    add_post()
