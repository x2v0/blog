# Как добавить комментарии в статический блог на GitHub Pages: полный гайд

## Введение

Наш блог полностью статический: никаких серверов, баз данных и бэкенда. Он грузится за 0.4 секунды и работает без VPN. Но когда встал вопрос о комментариях, мы поняли, что «просто добавить виджет» не получится.

В этом гайде — весь путь: от неудачных попыток до рабочего решения. С настройками, ошибками и их решениями.

## Шаг 1. Подготовка GitHub

### 1.1. Включаем Discussions

**Где:** Репозиторий `x2v0/x2v0.github.io` → **Settings** (вкладка сверху).
**Что делаем:** Прокручиваем вниз до раздела **Features** → ставим галочку на **Discussions**.

После этого в верхнем меню репозитория появится вкладка **Discussions**.

### 1.2. Создаём категорию для комментариев

**Где:** Вкладка **Discussions** → слева в меню **Categories** (иконка карандаша).
**Что делаем:** Создаём новую категорию, например, **`Blog comments`**.
**Важно:** Выбираем формат **Open** (не Announcements), чтобы пользователи могли писать комментарии.

### 1.3. Устанавливаем приложение Giscus

**Где:** https://github.com/apps/giscus
**Что делаем:** Нажимаем **Install** → выбираем аккаунт `x2v0` → в списке репозиториев выбираем `x2v0.github.io` → подтверждаем.

**Важно:** Без этого Giscus не сможет создавать обсуждения.

## Шаг 2. Получаем ID для Giscus

**Где:** https://giscus.app/ru
**Что делаем:**
1. В поле «Репозиторий» вводим `x2v0/x2v0.github.io`.
2. В разделе «Страница ↔ Обсуждения» выбираем **`specific`** (потому что мы будем передавать ID поста вручную).
3. В разделе «Категория обсуждения» выбираем **`Blog comments`**.
4. Прокручиваем вниз — видим готовый скрипт. В нём два ID:
    * `data-repo-id="MDEwOlJlcG9zaXRvcnkzNDk0NTQ4NDc="`
    * `data-category-id="DIC_kwDOFNRB_84DJ5jS"`

**Сохраняем их** — они понадобятся в коде.

## Шаг 3. Создаём отдельную страницу для комментариев

Почему отдельную? Потому что если встроить Giscus в `index.html`, где несколько постов на одной странице, он загрузится только для первого поста.

Создаём файл `comments.html`. Вот его основная часть (стили и скрипт):

    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Обсуждение — Блог</title>
        <style>
            :root { --bg: #f5f3eb; --text: #333; --card-bg: #fff; --border: #ddd; }
            [data-theme="dark"] { --bg: #121212; --text: #e0e0e0; --card-bg: #1e1e1e; --border: #333; }
            body { font-family: system-ui; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
            #giscus-container { background: var(--card-bg); padding: 20px; border-radius: 12px; border: 1px solid var(--border); }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="./index.html">← Назад к блогу</a>
            <div id="post-title"></div>
            <div id="giscus-container"></div>
        </div>
        <script>
            const urlParams = new URLSearchParams(window.location.search);
            const postId = urlParams.get('id') || 'unknown';
            const postTitle = urlParams.get('title') || 'Обсуждение';
            const theme = localStorage.getItem('theme') || 'light';
            
            document.documentElement.setAttribute('data-theme', theme);
            document.getElementById('post-title').textContent = decodeURIComponent(postTitle);

            const script = document.createElement('script');
            script.src = 'https://giscus.app/client.js';
            script.setAttribute('data-repo', 'x2v0/x2v0.github.io');
            script.setAttribute('data-repo-id', 'MDEwOlJlcG9zaXRvcnkzNDk0NTQ4NDc=');
            script.setAttribute('data-category', 'Blog comments');
            script.setAttribute('data-category-id', 'DIC_kwDOFNRB_84DJ5jS');
            script.setAttribute('data-mapping', 'specific');
            script.setAttribute('data-term', postId);
            script.setAttribute('data-theme', theme === 'dark' ? 'dark' : 'light');
            script.setAttribute('data-lang', 'ru');
            script.async = true;
            document.getElementById('giscus-container').appendChild(script);
        </script>
    </body>
    </html>

## Шаг 4. Создаём Discussions для всех постов

Giscus **не создаёт Discussion автоматически**. Мы написали скрипт `create_discussions.py`, который использует **GitHub API**.

**Важно:** Для работы скрипта нужен **токен GitHub** (с правами `repo` и `discussion`). Мы сохранили его в файл `~/.git.txt`.

Скрипт:
1. Читает `tree.json` (список постов).
2. Для каждого поста создаёт Discussion с названием `post-0`, `post-1` и т.д.

## Шаг 5. Добавляем кнопку в блог

В `index.html` добавляем под каждым постом ссылку:

    <a href="./comments.html?id=post-0&title=Название_поста">💬 Обсудить</a>

**Важно:** ID поста должен быть **без кириллицы** (только латиница, цифры и дефисы). Мы используем индексы (`post-0`, `post-1`).

## Ошибки, через которые мы прошли

### 1. `KeyError: 'data'` в API
**Причина:** Неправильный токен или недостаточно прав.
**Решение:** Проверить токен, убедиться, что у него есть права `repo` и `discussion`.

### 2. Виджет загружается только для одного поста
**Причина:** Giscus встраивается в `index.html`, но находит только первый контейнер.
**Решение:** Вынести комментарии на отдельную страницу `comments.html`.

### 3. Giscus не находит Discussion
**Причина:** Discussion с таким `term` не существует.
**Решение:** Создать его через API (скрипт `create_discussions.py`) или вручную.

### 4. Кириллица в ID ломает Giscus
**Причина:** Giscus не умеет работать с русскими буквами в `term`.
**Решение:** Использовать индексы (`post-0`) или хеши.

## Заключение

Теперь у нас есть:
*   **Статический блог** (без серверов).
*   **Комментарии через GitHub Discussions** (авторизация через GitHub, защита от ботов).
*   **Автоматическое создание Discussions** при публикации.
*   **Синхронизация темы** (светлая/тёмная).

Это был долгий путь, но результат того стоит. Блог остаётся статическим, но теперь он **живой**.
