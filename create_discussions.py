import requests
import json
import pathlib
import os

REPO = "x2v0/x2v0.github.io"
CATEGORY_ID = "DIC_kwDOFNRB_84DJ5jS"

def get_token():
    for path in [os.path.expanduser("~/git.txt"), os.path.expanduser("~/discId.txt")]:
        if os.path.exists(path):
            token = pathlib.Path(path).read_text().strip()
            if token:
                print(f"✓ Токен найден в {path}")
                return token
    return input("Вставь свой GitHub Token: ").strip()

def main():
    token = get_token()
    if not token:
        print("⚠ Токен не найден.")
        return

    tree = json.loads(pathlib.Path('tree.json').read_text(encoding='utf-8'))
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}

    # Получаем ID репозитория
    query = """
    query {
      repository(owner: "x2v0", name: "x2v0.github.io") {
        id
      }
    }
    """
    response = requests.post(url, json={"query": query}, headers=headers)
    data = response.json()
    if "errors" in data:
        print("❌ Ошибка авторизации:", data["errors"])
        return
    repo_id = data["data"]["repository"]["id"]
    print(f"✓ Repo ID: {repo_id}")

    # Создаём Discussions для всех постов
    for idx, node in enumerate(tree):
        title = f"post-{idx}"
        body = f"Обсуждение поста: {node['subject']}\n\n{node['body'][:300]}..."
        
        create_query = """
        mutation($repoId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
          createDiscussion(input: {repositoryId: $repoId, categoryId: $categoryId, title: $title, body: $body}) {
            discussion {
              id
              title
            }
          }
        }
        """
        create_vars = {
            "repoId": repo_id,
            "categoryId": CATEGORY_ID,
            "title": title,
            "body": body
        }
        create_resp = requests.post(url, json={"query": create_query, "variables": create_vars}, headers=headers)
        create_data = create_resp.json()
        
        if "errors" in create_data:
            err_msg = create_data["errors"][0].get("message", "")
            if "already exists" in err_msg.lower():
                print(f"  • Discussion {title} уже существует")
            else:
                print(f"  ✗ Ошибка создания {title}: {err_msg}")
        else:
            print(f"  ✓ Создан Discussion {title}")

if __name__ == "__main__":
    main()
