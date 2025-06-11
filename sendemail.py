import smtplib
from email.message import EmailMessage


SMTP_SERVER = "mail.hosting.reg.ru"
SMTP_PORT = 587
SMTP_USERNAME = "verify@folegle.ru"

CHALK_EMAIL = "mki@phystech.edu"

with open("keys/EMAIL_PASSWORD") as f:
    SMTP_PASSWORD = f.read().strip()

def send_email(recipient, password):
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        msg = EmailMessage()
        msg['From'] = SMTP_USERNAME
        msg['To'] = recipient
        msg['Subject'] = f"Пароль для Folegle: {password}"
        msg['Content-Type'] = 'text/plain; charset=utf-8'
        message = f"""\
Subject: Пароль для Folegle

Ваш одноразовый пароль:
{password}
Для входа перейдите по ссылке: https://folegle.ru/login?password={password}
Чтобы войти ещё раз, зайдите на эту страницу ещё раз и запросите новый пароль.
"""
        msg.set_content(message, subtype='plain')
        html_message = f"""\
            <html>
            <head>
                <meta charset="utf-8">
                <link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.6/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-4Q6Gf2aSP4eDXB8Miphtr37CMZZQ5oXLH2yaXMJ2w8e2ZtHTl7GptT4jmndRuHDT" crossorigin="anonymous">
                <style>
                @font-face {'{'}
                    font-family: 'Montserrat';
                    src: url("https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap") format('truetype-variations');
                    font-weight: 100 900;
                    font-style: normal;
                {'}'}
                </style>
            </head>
            <body>
            <div class="container">

                <h2>Ваш одноразовый пароль:</h2>
                <div class="m-3 p-3 bg-light border rounded" style="font-family: 'Montserrat', sans-serif; font-weight: 700; font-size: 1.5rem; text-align: center;">
                    <h2 style="font-family: 'Montserrat', sans-serif; font-weight: 700;" class="user-select-all">{password}</h2>
                </div>
                <p>Для входа перейдите по ссылке:</p>
                <a href="https://folegle.ru/login?password={password}">https://folegle.ru/login?password={password}</a>
                <p>Чтобы войти ещё раз, зайдите на эту страницу ещё раз и запросите новый пароль.</p>
            </body>
            </html>
            """
        msg.add_alternative(html_message, subtype='html')
        server.send_message(msg)

def send_chalk_message(building, room):
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        msg = EmailMessage()
        msg['From'] = SMTP_USERNAME
        msg['To'] = CHALK_EMAIL
        msg['Subject'] = f"Нет мела: {building} {room}"
        msg['Content-Type'] = 'text/plain; charset=utf-8'
        message = f"""\Нет мела в {building} {room}.\nЕсли сообщения приходят слишком часто, напишите об этом @folegle в Telegram."""
        msg.set_content(message, subtype='plain')
        html_message = f"""\
            <html>
            <head>
                <meta charset="utf-8">
                <link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.6/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-4Q6Gf2aSP4eDXB8Miphtr37CMZZQ5oXLH2yaXMJ2w8e2ZtHTl7GptT4jmndRuHDT" crossorigin="anonymous">
                <style>
                @font-face {'{'}
                    font-family: 'Montserrat';
                    src: url("https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap") format('truetype-variations');
                    font-weight: 100 900;
                    font-style: normal;
                {'}'}
                </style>
            </head>
            <body>
            <div class="container">
                <h2>Нет мела в {building} {room}.</h2>
                <p>Если сообщения приходят слишком часто, напишите об этом <a href="https://t.me/folegle">@folegle</a> в Telegram.</p>
            </div>
            </body>
            </html>
            """
        msg.add_alternative(html_message, subtype='html')
        server.send_message(msg)