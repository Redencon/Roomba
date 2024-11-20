import smtplib


SMTP_SERVER = "mail.hosting.reg.ru"
SMTP_PORT = 587
SMTP_USERNAME = "verify@folegle.ru"

with open("keys/EMAIL_PASSWORD") as f:
    SMTP_PASSWORD = f.read().strip()

def send_email(recipient, password):
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        message = f"""\
Subject: Пароль для Roomba

Ваш одноразовый пароль:
{password}
Для входа перейдите по ссылке: https://folegle.ru/login
Чтобы войти ещё раз, зайдите на эту страницу ещё раз и запросите новый пароль.
""".encode("utf-8")
        server.sendmail(SMTP_USERNAME, recipient, message)