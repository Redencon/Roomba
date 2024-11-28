# Folegle.ru (former Roomba)

> [folegle.ru](https://folegle.ru) <- продакшн

График занятости аудиторий МФТИ. Данные содержатся в локальной MySQL БД, общение с которой идёт модулем sql.py

## Стэк (?)

> In English because docs are in English anyways

**Dash** framework over **flask** backend, written with **Python**

Most visual elements are made with **Bootstrap** (with help from **dash-bootstrap-component** to integrate Bootstrap to Dash)

SQL connection is made with ORM **sqlalchemy**.

Regular tasks are performed by cron manager on **ispmanager** within hosting (not mentioned in code)

## Текущий пул ключевых фичей

- Вывод расписания в виде гантт-графиков для всех корпусов и аудиторий
- Просмотр свободных аудиторий в выбранное время
- Поиск по мероприятиям в расписании с поддержкой различных сценариев поиска
- Автоматическая подгрузка новых данных из открытых источников

---

Для свзи, пишите [Folegle в Telegram](https://t.me/folegle), или создайте Issue
