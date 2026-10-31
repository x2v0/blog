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

def get_anon_name(real_name):
    if not real_name: return 'Аноним'
    parts = real_name.strip().split()
    if not parts: return 'Аноним'
    clean_name = parts[0].lower()
    if len(clean_name) < 2: return 'Аноним'
    if len(parts) >= 2 and len(parts[1]) > 1:
        return parts[0][0].upper() + '.' + parts[1][0].upper() + '.'
    else:
        return parts[0][:4].capitalize() + '.'

def censor_text(text):
    banned = ['vpn', 'telegram', 'телеграм', 'лубянка', 'фсб', 'кгб', 'кремль',
              'война', 'спецоперация', 'сво', 'нато', 'россия', 'украина',
              'концлагерь', 'митинг', 'протест', 'политик', 'власть', 'госдума',
              'закон', 'хуй', 'пизд', 'бля', 'еба', 'ёб', 'сук', 'муд', 'говн',
              'дерьм', 'жоп', 'залуп', 'манда']
    if not text: return ""
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
    for word in banned:
        text = re.sub(r'(?i)\b' + re.escape(word) + r'[а-яё]*', '[ЦЕНЗУРА]', text)
    return text.strip()

def clean_html_to_text(text):
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</(div|p|tr|li|h[1-6])>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def clean_body(body):
    body = clean_html_to_text(body)
    lines = []
    for line in body.split('\n'):
        stripped = line.strip()
        if re.match(r'^(From|To|Sent|Subject|CC|Cc|Date|Bcc):', stripped, re.IGNORECASE):
            break
        if re.match(r'^On .*wrote:', stripped, re.IGNORECASE):
            break
        if stripped.startswith('>'):
            continue
        if stripped.startswith('С уважением. Валерий Онучин'):
            continue
        if re.match(r'^[-=]{5,}', stripped):
            continue
        if stripped:
            lines.append(stripped)
    unique = []
    prev = None
    for line in lines:
        if line != prev:
            unique.append(line)
        prev = line
    return censor_text('\n'.join(unique))

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 collect.py 'Тема письма'")
        print("Пример: python3 collect.py 'debug Android with M$'")
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

                from_raw = msg.get("From", "")
                from_name, from_addr = email.utils.parseaddr(from_raw)
                if from_name and from_name.startswith('=?'):
                    parts = decode_header(from_name)
                    decoded = ""
                    for p, enc in parts:
                        if isinstance(p, bytes):
                            decoded += p.decode(enc or 'utf-8', errors='replace')
                        else:
                            decoded += p
                    from_name = decoded
                sender = get_anon_name(from_name or from_addr)

                date_str = msg.get("Date")
                try:
                    dt = email.utils.parsedate_to_datetime(date_str)
                    date = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date = datetime.now().strftime("%Y-%m-%d %H:%M")

                subject_raw = msg.get("Subject", "")
                subject_parts = decode_header(subject_raw)
                subject = ""
                for p, enc in subject_parts:
                    if isinstance(p, bytes):
                        subject += p.decode(enc or 'utf-8', errors='replace')
                    else:
                        subject += p
                subject = censor_text(subject)

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="replace")
                else:
                    body = msg.get_payload(decode=True).decode(
                        msg.get_content_charset() or "utf-8", errors="replace")

                clean = clean_body(body)
                if clean:
                    emails.append({"date": date, "from": sender, "subject": subject, "body": clean})

    emails.sort(key=lambda e: e['date'])
    mail.logout()

    out = []
    out.append("=" * 60)
    out.append(f"ПЕРЕПИСКА: {search_subject}")
    out.append("=" * 60)
    out.append("")
    out.append("Инструкция для ИИ: напиши блог-пост на основе этой переписки.")
    out.append("Структура: введение, 3-5 тезисов, вывод.")
    out.append("Убери имена, email, политику, мат. Оставь только суть.")
    out.append("")
    out.append("=" * 60)
    out.append("")

    for i, e in enumerate(emails, 1):
        out.append(f"--- Письмо {i} | {e['date']} | {e['from']} ---")
        out.append(e['body'])
        out.append("")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"✓ Сохранено {len(emails)} писем в {OUTPUT_FILE} ({len(chr(10).join(out))} символов)")

if __name__ == "__main__":
    main()
