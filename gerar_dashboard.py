"""
Gerar Dashboard â€” Projeto Next
Busca tarefas do ClickUp, processa e gera HTML interativo.
"""

import json
import os
import base64
import requests
from datetime import datetime, date, timedelta
from collections import defaultdict

# â”€â”€ Credenciais â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# LÃª do ambiente (GitHub Actions Secret) ou usa o valor local como fallback
CLICKUP_TOKEN = os.environ.get('CLICKUP_TOKEN', 'pk_106059012_MUHDCKFLMAKNYZ8KVO8SLBG523SGXJOT')
LIST_ID       = '901321384887'

# â”€â”€ Caminhos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, 'dashboard_template.html')
HIST_PATH     = os.path.join(BASE_DIR, 'historico_snapshots.json')
LOGO_PATH     = os.path.join(BASE_DIR, 'Projeto-Next_brasao-1.png')
OUT_LATEST    = os.path.join(BASE_DIR, 'ProjetoNext_Dashboard_LATEST.html')

TODAY     = date.today()
TODAY_STR = TODAY.strftime('%Y-%m-%d')
DATE_FMT  = TODAY.strftime('%d/%m/%Y')

# â”€â”€ Seeds iniciais â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SEEDS = [
    {'date':'2026-06-01','total':546,'CONCLUÃDO':186,'EM PROGRESSO':116,'EM ATRASO':68,'SEM PRAZO DEFINIDO':101,'CANCELADO':50,'PAUSADO':20},
    {'date':'2026-06-02','total':546,'CONCLUÃDO':188,'EM PROGRESSO':116,'EM ATRASO':66,'SEM PRAZO DEFINIDO':102,'CANCELADO':50,'PAUSADO':20},
]

# â”€â”€ Status mapping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
STATUS_MAP = {
    # valores que o ClickUp pode retornar â†’ status normalizado
    'complete':            'CONCLUÃDO',
    'concluÃ­do':           'CONCLUÃDO',
    'concluido':           'CONCLUÃDO',
    'done':                'CONCLUÃDO',
    'in progress':         'EM PROGRESSO',
    'em progresso':        'EM PROGRESSO',
    'in review':           'EM PROGRESSO',
    'revisÃ£o':             'EM PROGRESSO',
    'overdue':             'EM ATRASO',
    'em atraso':           'EM ATRASO',
    'atraso':              'EM ATRASO',
    'no due date':         'SEM PRAZO DEFINIDO',
    'sem prazo definido':  'SEM PRAZO DEFINIDO',
    'sem prazo':           'SEM PRAZO DEFINIDO',
    'cancelled':           'CANCELADO',
    'cancelado':           'CANCELADO',
    'canceled':            'CANCELADO',
    'on hold':             'PAUSADO',
    'pausado':             'PAUSADO',
    'paused':              'PAUSADO',
    'not started':         'NÃƒO INICIADO',
    'nÃ£o iniciado':        'NÃƒO INICIADO',
    'nao iniciado':        'NÃƒO INICIADO',
    'open':                'NÃƒO INICIADO',
    'to do':               'NÃƒO INICIADO',
}

ACTIVE_STATUSES = {'EM PROGRESSO', 'EM ATRASO', 'SEM PRAZO DEFINIDO', 'NÃƒO INICIADO'}

# â”€â”€ Processos vÃ¡lidos e normalizaÃ§Ã£o â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
VALID_PROCS = {
    'Novos NegÃ³cios',
    'IncorporaÃ§Ã£o Make It',
    'IncorporaÃ§Ã£o Gadens',
    'Engenharia e GMO',
    'Suprimentos',
    'Financeiro',
}

def norm_proc(p: str) -> str:
    if not p:
        return ''
    p = p.strip().rstrip('\n').strip()
    if p in ('Engenharia', 'GMO'):
        return 'Engenharia e GMO'
    return p


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 1. Busca API ClickUp
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def fetch_all_tasks() -> list[dict]:
    """Busca todas as tarefas da lista via API ClickUp (paginaÃ§Ã£o 100/pÃ¡gina)."""
    headers = {'Authorization': CLICKUP_TOKEN}
    url     = f'https://api.clickup.com/api/v2/list/{LIST_ID}/task'
    tasks   = []
    page    = 0

    print('Buscando tarefas do ClickUp...')
    while True:
        params = {
            'page':              page,
            'limit':             100,
            'include_closed':    'true',
            'subtasks':          'false',
        }
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data  = resp.json()
        batch = data.get('tasks', [])
        tasks.extend(batch)
        print(f'  PÃ¡gina {page}: {len(batch)} tarefas (total atÃ© agora: {len(tasks)})')
        if len(batch) < 100:
            break
        page += 1

    print(f'Total de tarefas recebidas: {len(tasks)}')
    return tasks


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 2. NormalizaÃ§Ã£o de tarefas
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_custom_field(task: dict, field_name: str) -> str:
    for cf in task.get('custom_fields', []):
        name = cf.get('name', '').strip()
        if name.lower() == field_name.lower():
            # dropdown
            if cf.get('type') == 'drop_down':
                opts = {o['orderindex']: o['name'] for o in cf.get('type_config', {}).get('options', [])}
                val  = cf.get('value')
                if val is not None:
                    return opts.get(val, str(val))
            # text / label
            val = cf.get('value')
            if val:
                return str(val).strip()
    return ''


def _ms_to_date(ms) -> str | None:
    if not ms:
        return None
    try:
        return datetime.utcfromtimestamp(int(ms) / 1000).strftime('%Y-%m-%d')
    except Exception:
        return None


def _resolve_status(task: dict) -> str:
    """Determina status normalizado; aplica regra de atraso baseada em due_date."""
    raw    = (task.get('status', {}) or {}).get('status', '').strip().lower()
    mapped = STATUS_MAP.get(raw, '')

    if not mapped:
        # tenta fallback: se o nome contÃ©m palavras-chave
        for key, val in STATUS_MAP.items():
            if key in raw:
                mapped = val
                break
        if not mapped:
            mapped = 'NÃƒO INICIADO'

    # Regra de atraso: se ainda ativo e due_date < hoje â†’ EM ATRASO
    if mapped in ('EM PROGRESSO', 'NÃƒO INICIADO'):
        due_ms = task.get('due_date')
        if due_ms:
            due = _ms_to_date(due_ms)
            if due and due < TODAY_STR:
                return 'EM ATRASO'

    # Regra sem prazo: se ativo e sem due_date
    if mapped in ('EM PROGRESSO', 'NÃƒO INICIADO'):
        due_ms = task.get('due_date')
        if not due_ms:
            return 'SEM PRAZO DEFINIDO'

    return mapped


def normalize_tasks(raw_tasks: list[dict]) -> list[dict]:
    tasks = []
    for t in raw_tasks:
        name = (t.get('name') or '')[:80]

        status = _resolve_status(t)

        priority_raw = (t.get('priority') or {}) if isinstance(t.get('priority'), dict) else {}
        priority     = (priority_raw.get('priority') or 'normal').lower()
        if priority not in ('urgent', 'high', 'normal', 'low'):
            priority = 'normal'

        area = _get_custom_field(t, 'Ãrea/Departamento')
        proc = norm_proc(_get_custom_field(t, 'Processo'))

        # date_done: timestamp de quando foi marcado como concluÃ­do
        date_done = None
        if status == 'CONCLUÃDO':
            date_done = _ms_to_date(t.get('date_closed') or t.get('date_updated'))

        due_date = _ms_to_date(t.get('due_date'))

        assignees = t.get('assignees') or []
        assignee  = assignees[0].get('username', '') if assignees else ''

        tasks.append({
            'name':      name,
            'status':    status,
            'priority':  priority,
            'area':      area,
            'proc':      proc,
            'date_done': date_done,
            'due_date':  due_date,
            'assignee':  assignee,
        })
    return tasks


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 3. HistÃ³rico de snapshots
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_history() -> list[dict]:
    if os.path.exists(HIST_PATH):
        with open(HIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return list(SEEDS)  # cÃ³pia dos seeds


def save_history(history: list[dict]) -> None:
    with open(HIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def build_snapshot(tasks: list[dict]) -> dict:
    snap = {
        'date':               TODAY_STR,
        'total':              len(tasks),
        'CONCLUÃDO':          0,
        'EM PROGRESSO':       0,
        'EM ATRASO':          0,
        'SEM PRAZO DEFINIDO': 0,
        'CANCELADO':          0,
        'PAUSADO':            0,
    }
    for t in tasks:
        s = t['status']
        if s in snap:
            snap[s] += 1
    return snap


def upsert_snapshot(history: list[dict], snap: dict) -> list[dict]:
    """Insere ou atualiza o snapshot do dia, mantendo histÃ³rico ordenado."""
    history = [h for h in history if h['date'] != TODAY_STR]
    history.append(snap)
    history.sort(key=lambda x: x['date'])
    return history


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 4. Curvas de evoluÃ§Ã£o
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_done_global(tasks: list[dict]) -> list[list]:
    """
    [[date, cum_count], ...] â€” concluÃ­das acumuladas globais.
    Calculado a partir do date_done real das tarefas, agrupado por semana ISO.
    """
    from collections import defaultdict
    by_week: dict[tuple, str] = {}       # week_key â†’ Ãºltima data da semana com conclusÃµes
    week_counts: dict[tuple, int] = defaultdict(int)

    for t in tasks:
        if t['status'] == 'CONCLUÃDO' and t['date_done']:
            d = date.fromisoformat(t['date_done'])
            wk = (d.isocalendar()[0], d.isocalendar()[1])
            week_counts[wk] += 1
            # guarda a data mais recente da semana como rÃ³tulo
            if wk not in by_week or t['date_done'] > by_week[wk]:
                by_week[wk] = t['date_done']

    # Acumula em ordem cronolÃ³gica
    sorted_weeks = sorted(week_counts.keys())
    cum = 0
    series = []
    for wk in sorted_weeks:
        cum += week_counts[wk]
        series.append([by_week[wk], cum])
    return series


def _weekly_snapshots(history: list[dict], field: str) -> list[list]:
    """
    Retorna um ponto por semana ISO (Ãºltimo snapshot da semana).
    Sempre inclui o snapshot mais recente, independente do dia da semana.
    """
    by_week: dict[tuple, dict] = {}
    for h in history:
        d = date.fromisoformat(h['date'])
        week_key = (d.isocalendar()[0], d.isocalendar()[1])  # (ano, semana)
        # mantÃ©m o snapshot mais recente de cada semana
        if week_key not in by_week or h['date'] > by_week[week_key]['date']:
            by_week[week_key] = h

    return [[h['date'], h[field]] for h in sorted(by_week.values(), key=lambda x: x['date'])]


def build_sp_global(history: list[dict]) -> list[list]:
    """[[date, count], ...] â€” sem prazo definido, granularidade semanal."""
    return _weekly_snapshots(history, 'SEM PRAZO DEFINIDO')


def build_atr_global(history: list[dict]) -> list[list]:
    """[[date, count], ...] â€” em atraso, granularidade semanal."""
    return _weekly_snapshots(history, 'EM ATRASO')


def build_done_by_proc(tasks: list[dict]) -> dict:
    """
    {processo: [[date, cum_count], ...]}
    Acumulado de concluÃ­das por processo, baseado em date_done das tarefas.
    """
    by_proc: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t in tasks:
        if t['status'] == 'CONCLUÃDO' and t['date_done'] and t['proc']:
            by_proc[t['proc']][t['date_done']] += 1

    result = {}
    for proc, counts in by_proc.items():
        sorted_dates = sorted(counts.keys())
        cum = 0
        series = []
        for d in sorted_dates:
            cum += counts[d]
            series.append([d, cum])
        result[proc] = series
    return result


def build_done_by_area(tasks: list[dict]) -> dict:
    """
    {area: [[date, cum_count], ...]}
    Acumulado de concluÃ­das por Ã¡rea, baseado em date_done das tarefas.
    """
    by_area: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t in tasks:
        if t['status'] == 'CONCLUÃDO' and t['date_done'] and t['area']:
            by_area[t['area']][t['date_done']] += 1

    result = {}
    for area, counts in by_area.items():
        sorted_dates = sorted(counts.keys())
        cum = 0
        series = []
        for d in sorted_dates:
            cum += counts[d]
            series.append([d, cum])
        result[area] = series
    return result


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 5. Heatmap
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_heatmap(tasks: list[dict]) -> dict:
    """
    Retorna estrutura para o heatmap no formato esperado pelo template:
    {
      'periods':  ['jun/26', 'jul/26', ...],
      'rows':     [{'area': str, 'cells': [int,...], 'sem_prazo': int}, ...],
      'max_val':  int,
      'max_sp':   int,
    }
    Inclui linha TOTAL no rodapÃ©.
    Statuses: EM PROGRESSO + NÃƒO INICIADO. SEM PRAZO DEFINIDO vai na coluna Sem Prazo.
    """
    ACTIVE = {'EM PROGRESSO', 'NÃƒO INICIADO', 'SEM PRAZO DEFINIDO'}

    MONTH_PT = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']

    def fmt_month(ym: str) -> str:
        """'2026-06' â†’ 'jun/26'"""
        y, m = ym.split('-')
        return f'{MONTH_PT[int(m)-1]}/{y[2:]}'

    # Coleta dados
    area_month: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    area_sp:    dict[str, int]            = defaultdict(int)
    months_seen: set[str] = set()

    for t in tasks:
        if t['status'] not in ACTIVE:
            continue
        area = t['area'] or 'Sem Ãrea'
        if t['status'] == 'SEM PRAZO DEFINIDO' or not t['due_date']:
            area_sp[area] += 1
        else:
            month = t['due_date'][:7]
            area_month[area][month] += 1
            months_seen.add(month)

    # SequÃªncia contÃ­nua de meses (do menor ao maior encontrado)
    if months_seen:
        first_m = min(months_seen)
        last_m  = max(months_seen)
        months  = []
        cur     = datetime.strptime(first_m + '-01', '%Y-%m-%d').date()
        end     = datetime.strptime(last_m  + '-01', '%Y-%m-%d').date()
        while cur <= end:
            months.append(cur.strftime('%Y-%m'))
            cur = cur.replace(month=cur.month + 1) if cur.month < 12 else cur.replace(year=cur.year + 1, month=1)
    else:
        months = [TODAY.strftime('%Y-%m')]

    periods = [fmt_month(m) for m in months]

    # Todas as Ã¡reas, ordenadas por volume total decrescente
    all_areas = sorted(
        set(area_month.keys()) | set(area_sp.keys()),
        key=lambda a: -(sum(area_month[a].values()) + area_sp[a])
    )

    rows = []
    totals_cells = [0] * len(months)
    total_sp     = 0

    for area in all_areas:
        cells   = [area_month[area].get(m, 0) for m in months]
        sem_prazo = area_sp[area]
        rows.append({'area': area, 'cells': cells, 'sem_prazo': sem_prazo})
        for i, v in enumerate(cells):
            totals_cells[i] += v
        total_sp += sem_prazo

    rows.append({'area': 'TOTAL', 'cells': totals_cells, 'sem_prazo': total_sp})

    max_val = max((v for r in rows[:-1] for v in r['cells']), default=1)
    max_sp  = max((r['sem_prazo'] for r in rows[:-1]), default=1)

    return {
        'periods': periods,
        'rows':    rows,
        'max_val': max_val,
        'max_sp':  max_sp,
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 6. Logo base64
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_logo_b64() -> str:
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return ''


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 7. GeraÃ§Ã£o do HTML
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generate_html(
    tasks:        list[dict],
    done_by_proc: dict,
    done_by_area: dict,
    done_global:  list,
    sp_global:    list,
    atr_global:   list,
    hm_data:      dict,
) -> str:
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    replacements = {
        '__DATE__':        DATE_FMT,
        '__TASKS__':       json.dumps(tasks,        ensure_ascii=False),
        '__DONE_BY_PROC__':json.dumps(done_by_proc, ensure_ascii=False),
        '__DONE_BY_AREA__':json.dumps(done_by_area, ensure_ascii=False),
        '__DONE_GLOBAL__': json.dumps(done_global,  ensure_ascii=False),
        '__SP_GLOBAL__':   json.dumps(sp_global,    ensure_ascii=False),
        '__ATR_GLOBAL__':  json.dumps(atr_global,   ensure_ascii=False),
        '__HM_DATA__':     json.dumps(hm_data,      ensure_ascii=False),
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    # Embutir logo se existir
    logo_b64 = load_logo_b64()
    if logo_b64:
        html = html.replace(
            'Projeto-Next_brasao-1.png',
            f'data:image/png;base64,{logo_b64}'
        )

    return html


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    # 1. Buscar tarefas
    raw_tasks = fetch_all_tasks()

    # 2. Normalizar
    tasks = normalize_tasks(raw_tasks)
    print(f'Tarefas normalizadas: {len(tasks)}')

    # 3. Carregar / criar histÃ³rico
    history = load_history()
    print(f'HistÃ³rico carregado: {len(history)} snapshots')

    # 4. Adicionar snapshot do dia
    snap    = build_snapshot(tasks)
    history = upsert_snapshot(history, snap)
    save_history(history)
    print(f'Snapshot do dia adicionado: {snap}')

    # 5. Curvas globais
    done_global = build_done_global(tasks)   # usa date_done real das tarefas
    sp_global   = build_sp_global(history)
    atr_global  = build_atr_global(history)

    # 6. Curvas por processo e Ã¡rea (do date_done das tarefas)
    done_by_proc = build_done_by_proc(tasks)
    done_by_area = build_done_by_area(tasks)

    # 7. Heatmap
    hm_data = build_heatmap(tasks)

    # 8. Gerar HTML
    html = generate_html(
        tasks        = tasks,
        done_by_proc = done_by_proc,
        done_by_area = done_by_area,
        done_global  = done_global,
        sp_global    = sp_global,
        atr_global   = atr_global,
        hm_data      = hm_data,
    )

    # 9. Salvar arquivos
    out_dated = os.path.join(BASE_DIR, f'ProjetoNext_Dashboard_{TODAY.strftime("%Y%m%d")}.html')
    for path in (OUT_LATEST, out_dated):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'Salvo: {path}')

    print('\nDashboard gerado com sucesso!')


if __name__ == '__main__':
    main()


