# Блог x2v0

Статический блог на GitHub Pages. Посты хранятся в `posts/`, метаданные — в `tree.json`, комментарии — через GitHub Discussions.

## Как добавить новый пост

### Вариант 1: Автоматически (рекомендуется)

1. Создайте файл с текстом поста, например `my-new-post.md`. Первая строка должна быть заголовком `# Название поста`.
2. Запустите скрипт:
   ```bash
   python3 auto-publish.py my-new-post.md
   ```
   Скрипт сам:
   - скопирует текст в `posts/` с правильным slug-именем;
   - создаст Discussion в репозитории `x2v0/x2v0.github.io`;
   - обновит `tree.json`;
   - запустит тесты (`tests/site.test.js`);
   - запушит изменения в `main`.

### Вариант 2: Вручную

1. Напишите пост в Markdown (первая строка — `# Заголовок`).
2. Сохраните его в `post.md` в корне репозитория.
3. Запустите:
   ```bash
   python3 publish.py
   ```
4. Проверьте, что тесты прошли, и изменения ушли в `main`.

## Структура репозитория

- `posts/` — Markdown-файлы постов (генерируются в HTML при сборке).
- `tree.json` — метаданные постов (id, subject, date, discussion_number).
- `add_post.py` — создаёт пост и Discussion (интерактивно).
- `publish.py` — тесты + git push.
- `auto-publish.py` — полный цикл без интерактивного ввода.
- `collect.py` — генератор HTML из `posts/` и `tree.json`.
- `index.html` — главная страница.

## Требования

- Python 3.10+
- `requests` (`pip install requests`)
- `gh` CLI (для авторизации в GitHub)
- Токен GitHub в `~/git.txt` (для `publish.py` и `auto-publish.py`)

## Проверка после публикации

```bash
# Проверить, что пост есть в tree.json
python3 -c "import json; t=json.load(open('tree.json')); print([p['subject'] for p in t][:3])"

# Проверить, что HTML-файл сгенерирован (если используете collect.py)
python3 collect.py

# Открыть сайт
# https://x2v0.github.io/blog
```
