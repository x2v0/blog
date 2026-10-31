import imaplib
import email
from email.header import decode_header
import os
import re
import html
import sys
from datetime import datetime
import email.utils

IMAP_SERVER = "imap.yandex.ru"
EMAIL_USER = "valeriy.onuchin@yandex.ru"
PASSWORD_FILE = os.path.expanduser("~/.yandex_app_password")
OUTPUT_FILE = "thread.md"

def clean_html_to_text(text):
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</(div|p|tr|li|h[1-6])>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return text.strip()

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 collect.py 'Тема письма'")
        return

    search_subject = sys.argv[1]
    print(f"Ищем письма с темой: {search_subject}")

    if not os.path.exists(PASSWORD_FILE):
        print(f"⚠ Нет файла {PASSWORD_FILE}")
        return
    with open(PASSWORD_FILE, "r") as f:
        password = f.read().strip()

    print(f"Подключение к {IMAP_SERVER}...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, password)
    mail.select("inbox")

    status, messages = mail.search(None, f'(SUBJECT "{search_subject}")')
    if status != "OK":
        print("Ошибка поиска")
        return

    email_ids = messages[0].split()
    print(f"Найдено писем: {len(email_ids)}")

    emails = []
    for e_id in email_ids:
        status, msg_data = mail.fetch(e_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                date_str = msg.get("Date")
                try:
                    dt = email.utils.parsedate_to_datetime(date_str)
                    date = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date = datetime.now().strftime("%Y-%m-%d %H:%M")

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="replace")
                else:
                    body = msg.get_payload(decode=True).decode(
                        msg.get_content_charset() or "utf-8", errors="replace")

                clean = clean_html_to_text(body)
                emails.append({"date": date, "body": clean, "len": len(clean)})

    # Сортируем по дате (последние — в конце)
    emails.sort(key=lambda e: e['date'])

    # Берём последнее письмо (самое свежее)
    last = emails[-1]

    print(f"\n=== Последнее письмо ({last['date']}, {last['len']} символов) ===")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Переписка: {search_subject}\n\n")
        f.write(f"**Дата:** {last['date']}\n\n")
        f.write(f"**Размер:** {last['len']} символов\n\n")
        f.write("---\n\n")
        f.write(last['body'])

    print(f"✓ Сохранено в {OUTPUT_FILE}")
    print(f"✓ Размер файла: {os.path.getsize(OUTPUT_FILE)} байт")

if __name__ == "__main__":
    main()
