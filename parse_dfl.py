import pandas as pd

data = pd.read_excel('data/schedule.xlsx', header=None)
current_day = data.iloc[0, 1]
weekdays = {}
cur_start = 1
for i, value in enumerate(data.iloc[0, 2:].fillna(0), 2):
    if value:
        weekdays[current_day] = (cur_start, i-1)
        current_day = value
        cur_start = i
weekdays

long_form = []
for day in weekdays:
    daydata = data.iloc[1:, weekdays[day][0]:weekdays[day][1]+1].reset_index(drop=True)
    title = daydata.iloc[0, :].reset_index(drop=True)
    def shorter_title(x):
        if pd.isnull(x):
            return x
        spl = x.split(' ')
        if len(spl) < 3:
            return ' '.join(spl)
        return spl[0]+' '+spl[1][0]+'.'+spl[2][0]+'.'
    title_shorter = title.apply(shorter_title)
    daydata = daydata.iloc[2:, :]
    for col in range(daydata.shape[1]):
        for row in range(daydata.shape[0]//2):
            if pd.isnull(daydata.iloc[row*2, col]):
                continue
            event = dict(
                description=daydata.iloc[row*2, col]+" "+title_shorter[col],
                room=daydata.iloc[row*2+1, col],
                teacher=title[col],
                weekday=day,
                slot=row
            )
            long_form.append(event)
TIME_SLOTS = [
    ("09:00", "10:25"),
    ("10:45", "12:10"),
    ("12:20", "13:45"),
    ("13:55", "15:20"),
    ("15:30", "16:55"),
    ("17:05", "18:30"),
    ("18:35", "20:00"),
    ("20:00", "22:00"),
]
REVERSE_WEEKDAYS = {
    'Понедельник': 1,
    'Вторник': 2,
    'Среда': 3,
    'Четверг': 4,
    'Пятница': 5,
    'Суббота': 6,
}
df = pd.DataFrame(long_form)
df[['start', 'end']] = df['slot'].apply(lambda x: pd.Series(TIME_SLOTS[x]))
df['room'] = df["room"].astype(str)
df['room'] = df['room'].apply(lambda x: ' '.join([w for w in x.split(' ') if 'НК' not in w]))
# df['room'].unique()
df['building'] = df['room'].apply(lambda r: ('Квант' if r.isdigit() else 'ЦЯПТ'))
df['day'] = df['weekday'].apply(lambda x: REVERSE_WEEKDAYS[x])
df['time_start'] = df['start']
df['time_finish'] = df['end']
df[['description', 'building', 'room', 'time_start', 'time_finish', 'day']].to_csv('data/schedule.csv', index=False)