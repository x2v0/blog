import requests
import sys
import json

# Замени на свой токен GitHub (Settings → Developer settings → Personal access tokens)
TOKEN = "YOUR_GITHUB_TOKEN"
REPO = "x2v0/x2v0.github.io"

def fetch_comments(term):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    query = """
    query($owner: String!, $name: String!, $term: String!) {
      repository(owner: $owner, name: $name) {
        discussion(title: $term) {
          title
          comments(first: 10) {
            nodes {
              author { login }
              body
              createdAt
            }
          }
        }
      }
    }
    """
    
    variables = {"owner": "x2v0", "name": "x2v0.github.io", "term": term}
    response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
    
    if response.status_code != 200:
        print(f"Ошибка: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    discussion = data.get("data", {}).get("repository", {}).get("discussion")
    
    if not discussion:
        print(f"Обсуждение с term '{term}' не найдено.")
        return
    
    print(f"=== {discussion['title']} ===")
    for comment in discussion['comments']['nodes']:
        print(f"\n[{comment['createdAt']}] {comment['author']['login']}:")
        print(comment['body'])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 fetch_comments.py 'post-id'")
        sys.exit(1)
    fetch_comments(sys.argv[1])
