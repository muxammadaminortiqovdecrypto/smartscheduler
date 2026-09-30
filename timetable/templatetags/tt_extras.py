from django import template

register = template.Library()

SUBJECT_EMOJI = [
    (('matem', 'math'), '📐'), (('fizika', 'phys'), '⚛️'), (('ingliz', 'eng', 'til'), '🌍'),
    (('dastur', 'prog'), '💻'), (('baza', 'database', 'db'), '🗄️'), (('algoritm', 'algo'), '🧠'),
    (('kimyo', 'chem'), '🧪'), (('tarix', 'hist'), '🏛️'), (('iqtis', 'econ'), '📈'),
]
PAIR_TIMES = {1: '08:30–09:50', 2: '10:00–11:20', 3: '11:30–12:50', 4: '14:00–15:20', 5: '15:30–16:50'}


@register.filter
def subject_emoji(name):
    n = (name or '').lower()
    for keys, emo in SUBJECT_EMOJI:
        if any(k in n for k in keys):
            return emo
    return '📚'


@register.filter
def pair_time(pair):
    return PAIR_TIMES.get(pair, '')
