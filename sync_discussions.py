import json
import pathlib
import subprocess
import requests

def main():
    tree_path = pathlib.Path("/data/data/com.termux/files/home/blog-repo/tree.json")
    if not tree_path.exists():
        print("❌ tree.json не найден")
        return

    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    
    # Получаем токен
    token_path = pathlib.Path.home() / "git.txt"
    if not token_path.exists():
        print("⚠ Токен не найден (~/git.txt). Синхронизация невозможна.")
        return
    token = token_path.read_text().strip()

    print("=== Запрашиваем обсуждения у GitHub ===")
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}

    # Запрашиваем последние 100 обсуждений
    query = """
    query {
      repository(owner: "x2v0", name: "x2v0.github.io") {
        discussions(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            title
            number
          }
        }
      }
    }
    """
    
    try:
        resp = requests.post(url, json={"query": query}, headers=headers)
        data = resp.json()
        
        if "errors" in data:
            print(f"❌ Ошибка API: {data['errors'][0]['message']}")
            return
            
        discussions = data["data"]["repository"]["discussions"]["nodes"]
        disc_map = {d["title"]: d["number"] for d in discussions}
        print(f"✓ Получено {len(disc_map)} обсуждений из GitHub.")
    except Exception as e:
        print(f"❌ Ошибка при запросе: {e}")
        return

    print("\n=== Синхронизация tree.json ===")
    updated_count = 0
    for post in tree:
        post_id = post.get("id")
        if not post_id:
            continue
            
        if "discussion_number" in post and post["discussion_number"]:
            continue # Уже есть номер

        if post_id in disc_map:
            post["discussion_number"] = disc_map[post_id]
            print(f"  ✓ {post_id} -> #{disc_map[post_id]}")
            updated_count += 1
        else:
            print(f"  • {post_id} -> обсуждение не найдено (пропускаем)")

    if updated_count > 0:
        tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✓ tree.json обновлен (добавлено {updated_count} номеров)")
        
        print("\n=== Пуш на GitHub ===")
        subprocess.run(["git", "add", "tree.json"], cwd="/data/data/com.termux/files/home/blog-repo")
        subprocess.run(["git", "commit", "-m", "fix: sync discussion numbers for old posts"], cwd="/data/data/com.termux/files/home/blog-repo")
        subprocess.run(["git", "push", "origin", "main"], cwd="/data/data/com.termux/files/home/blog-repo")
        print("✓ Изменения запушены.")
    else:
        print("\n✓ Все старые посты уже синхронизированы или обсуждений не найдено.")

if __name__ == "__main__":
    main()
