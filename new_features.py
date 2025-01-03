from dash import html


def new_features():
    return html.Div([
        html.H2("Оптимизация"),
        html.Small("01/12/2024", className="text-muted"),
        html.P("Графики кэшируются, меньше нагружая сервер"),
        html.P(" ".join([
            "Линия текущего времени не входит в кэширование, поэтому она осталась, но не обновляется автоматически."
            "По этой же причине страница теперь не обновляется автоматически.",
        ])),
        html.Hr(),
        html.H2("Вертикальная мобильность"),
        html.Small("29/11/2024", className="text-muted"),
        html.P("Добавлена возможность быстро перемещаться вверх и вниз к нужным разделам"),
        html.P([" ".join([
            "Для перехода к нужной секции наверху страницы добавлено меню «Перейти к» со",
            "ссылками на все разделы. Для возврата обратно наверх добавлена кнопка ",
        ]), html.I(className="bi bi-chevron-up")]),
        html.Hr(),
        html.H2("Свободные аудитории"),
        html.Small("25/11/2024", className="text-muted"),
        html.P("Добавлен раздел «Свободные аудитории»"),
        html.P("Зайти посмотреть можно по нажатию кнопки «Свободные аудитории» наверху страницы"),
        html.P(" ".join([
            "В открывшемся окне можно посмотреть свободные аудитории сейчас или в выбранное время",
            "для дня, выбранного в календаре в основном окне. Также можно отфильтровать аудитории по корпусу." 
        ])),
        html.P(html.Em([
            "Если аудитория занята учебным занятием, при том что она отображается как свободная, ",
            "напишите об этом на почту ",
            html.A("МКИ", href="mailto:mki@phystech.edu"),
            " или ", html.A("Folegle", href="tg://resolve?domain=folegle&text=Привет! Я нашёл несоответствие расписанию на сайте:")
        ])),
        html.Hr(),
        html.H2("Поиск по группе"),
        html.Small("28/11/2024", className="text-muted"),
        html.P("Поиск теперь поддерживает учебные группы"),
        html.P(" ".join([
            "Кроме занятий, которые проходят у указанной группы по расписанию,",
            "теперь в результатах также отображаются лекции, которые читаются",
            "для всего потока, к которой эта группа относится."
        ])),
        html.P(html.Em([
            "Если ваша группа не даёт ожидаемых результатов, сообщите об этом нам."
        ])),
        html.Hr(),
        html.H2("Расписание ДИЯ"),
        html.Small("25/11/2024", className="text-muted"),
        html.P("В расписание были добавлены аудитории ДИЯ"),
    ])