# -*- coding: utf-8 -*-
"""
Gerar Dashboard - Projeto Next
Busca tarefas do ClickUp, processa e gera HTML interativo.
"""

import json
import os
import base64
import requests
from datetime import datetime, date
from collections import defaultdict

# Credenciais
CLICKUP_TOKEN = os.environ.get('CLICKUP_TOKEN', 'pk_106059012_MUHDCKFLMAKNYZ8KVO8SLBG523SGXJOT')
LIST_ID       = '901321384887'

# Caminhos
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, 'dashboard_template.html')
HIST_PATH     = os.path.join(BASE_DIR, 'historico_snapshots.json')
LOGO_PATH     = os.path.join(BASE_DIR, 'Projeto-Next_brasao-1.png')
OUT_LATEST    = os.path.join(BASE_DIR, 'ProjetoNext_Dashboard_LATEST.html')

TODAY     = date.today()
TODAY_STR = TODAY.strftime('%Y-%m-%d')
DATE_FMT  = TODAY.strftime('%d/%m/%Y')

# Seeds iniciais do historico
SEEDS = [
    {'date':'2026-06-01','total':546,'CONCLUÍDO':186,'EM PROGRESSO':116,'EM ATRASO':68,'SEM PRAZO DEFINIDO':101,'CANCELADO':50,'PAUSADO':20},
    {'date':'2026-06-02','total':546,'CONCLUÍDO':188,'EM PROGRESSO':116,'EM ATRASO':66,'SEM PRAZO DEFINIDO':102,'CANCELADO':50,'PAUSADO':20},
]

# Status normalizado usando unicode escapes para evitar problemas de encoding
ST_CONCLUIDO      = 'CONCLUÍDO'        # CONCLUÍDO
ST_EM_PROGRESSO   = 'EM PROGRESSO'
ST_EM_ATRASO      = 'EM ATRASO'
ST_SEM_PRAZO      = 'SEM PRAZO DEFINIDO'
ST_CANCELADO      = 'CANCELADO'
ST_PAUSADO        = 'PAUSADO'
ST_NAO_INICIADO   = 'NÃO INICIADO'     # NÃO INICIADO

STATUS_MAP = {
    'complete':           ST_CONCLUIDO,
    'concluído':     ST_CONCLUIDO,
    'concluido':          ST_CONCLUIDO,
    'done':               ST_CONCLUIDO,
    'in progress':        ST_EM_PROGRESSO,
    'em progresso':       ST_EM_PROGRESSO,
    'in review':          ST_EM_PROGRESSO,
    'revisão':       ST_EM_PROGRESSO,
    'overdue':            ST_EM_ATRASO,
    'em atraso':          ST_EM_ATRASO,
    'atraso':             ST_EM_ATRASO,
    'no due date':        ST_SEM_PRAZO,
    'sem prazo definido': ST_SEM_PRAZO,
    'sem prazo':          ST_SEM_PRAZO,
    'cancelled':          ST_CANCELADO,
    'cancelado':          ST_CANCELADO,
    'canceled':           ST_CANCELADO,
    'on hold':            ST_PAUSADO,
    'pausado':            ST_PAUSADO,
    'paused':             ST_PAUSADO,
    'not started':        ST_NAO_INICIADO,
    'não iniciado':  ST_NAO_INICIADO,
    'nao iniciado':       ST_NAO_INICIADO,
    'open':               ST_NAO_INICIADO,
    'to do':              ST_NAO_INICIADO,
}

def norm_proc(p):
    if not p:
        return ''
    p = p.strip().rstrip('\n').strip()
    if p in ('Engenharia', 'GMO'):
        return 'Engenharia e GMO'
    return p


# 1. Busca API ClickUp

def fetch_all_tasks():
    headers = {'Authorization': CLICKUP_TOKEN}
    url     = 'https://api.clickup.com/api/v2/list/{}/task'.format(LIST_ID)
    tasks   = []
    page    = 0
    print('Buscando tarefas do ClickUp...')
    while True:
        params = {'page': page, 'limit': 100, 'include_closed': 'true', 'subtasks': 'false'}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        batch = resp.json().get('tasks', [])
        tasks.extend(batch)
        print('  Pagina {}: {} tarefas (total: {})'.format(page, len(batch), len(tasks)))
        if len(batch) < 100:
            break
        page += 1
    print('Total recebido: {}'.format(len(tasks)))
    return tasks


# 2. Normalizacao

def _get_custom_field(task, field_name):
    for cf in task.get('custom_fields', []):
        name = cf.get('name', '').strip()
        if name.lower() == field_name.lower():
            if cf.get('type') == 'drop_down':
                opts = {o['orderindex']: o['name'] for o in cf.get('type_config', {}).get('options', [])}
                val  = cf.get('value')
                if val is not None:
                    return opts.get(val, str(val))
            val = cf.get('value')
            if val:
                return str(val).strip()
    return ''


def _ms_to_date(ms):
    if not ms:
        return None
    try:
        return datetime.utcfromtimestamp(int(ms) / 1000).strftime('%Y-%m-%d')
    except Exception:
        return None


def _resolve_status(task):
    raw    = (task.get('status', {}) or {}).get('status', '').strip().lower()
    mapped = STATUS_MAP.get(raw, '')
    if not mapped:
        for key, val in STATUS_MAP.items():
            if key in raw:
                mapped = val
                break
        if not mapped:
            mapped = ST_NAO_INICIADO

    # Regra atraso
    if mapped in (ST_EM_PROGRESSO, ST_NAO_INICIADO):
        due_ms = task.get('due_date')
        if due_ms:
            due = _ms_to_date(due_ms)
            if due and due < TODAY_STR:
                return ST_EM_ATRASO

    # Regra sem prazo
    if mapped in (ST_EM_PROGRESSO, ST_NAO_INICIADO):
        if not task.get('due_date'):
            return ST_SEM_PRAZO

    return mapped


def normalize_tasks(raw_tasks):
    tasks = []
    for t in raw_tasks:
        name     = (t.get('name') or '')[:80]
        status   = _resolve_status(t)
        praw     = (t.get('priority') or {}) if isinstance(t.get('priority'), dict) else {}
        priority = (praw.get('priority') or 'normal').lower()
        if priority not in ('urgent', 'high', 'normal', 'low'):
            priority = 'normal'
        area      = _get_custom_field(t, 'Área/Departamento')
        proc      = norm_proc(_get_custom_field(t, 'Processo'))
        date_done = None
        if status == ST_CONCLUIDO:
            date_done = _ms_to_date(t.get('date_closed') or t.get('date_updated'))
        due_date  = _ms_to_date(t.get('due_date'))
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


# 3. Historico de snapshots

def load_history():
    if os.path.exists(HIST_PATH):
        with open(HIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return list(SEEDS)


def save_history(history):
    with open(HIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def build_snapshot(tasks):
    snap = {
        'date':               TODAY_STR,
        'total':              len(tasks),
        ST_CONCLUIDO:         0,
        ST_EM_PROGRESSO:      0,
        ST_EM_ATRASO:         0,
        ST_SEM_PRAZO:         0,
        ST_CANCELADO:         0,
        ST_PAUSADO:           0,
    }
    for t in tasks:
        s = t['status']
        if s in snap:
            snap[s] += 1
    return snap


def upsert_snapshot(history, snap):
    history = [h for h in history if h['date'] != TODAY_STR]
    history.append(snap)
    history.sort(key=lambda x: x['date'])
    return history


# 4. Curvas de evolucao

def _weekly_snapshots(history, field):
    by_week = {}
    for h in history:
        if h.get(field) is None:
            continue
        d  = date.fromisoformat(h['date'])
        wk = (d.isocalendar()[0], d.isocalendar()[1])
        if wk not in by_week or h['date'] > by_week[wk]['date']:
            by_week[wk] = h
    return [[h['date'], h[field]] for h in sorted(by_week.values(), key=lambda x: x['date'])]


def build_done_global(tasks):
    by_week  = {}
    wcounts  = defaultdict(int)
    for t in tasks:
        if t['status'] == ST_CONCLUIDO and t['date_done']:
            d  = date.fromisoformat(t['date_done'])
            wk = (d.isocalendar()[0], d.isocalendar()[1])
            wcounts[wk] += 1
            if wk not in by_week or t['date_done'] > by_week[wk]:
                by_week[wk] = t['date_done']
    cum    = 0
    series = []
    for wk in sorted(wcounts.keys()):
        cum += wcounts[wk]
        series.append([by_week[wk], cum])
    return series


def build_sp_global(history):
    return _weekly_snapshots(history, ST_SEM_PRAZO)


def build_atr_global(history):
    return _weekly_snapshots(history, ST_EM_ATRASO)


def build_done_by_proc(tasks):
    by_proc = defaultdict(lambda: defaultdict(int))
    for t in tasks:
        if t['status'] == ST_CONCLUIDO and t['date_done'] and t['proc']:
            by_proc[t['proc']][t['date_done']] += 1
    result = {}
    for proc, counts in by_proc.items():
        cum = 0
        series = []
        for d in sorted(counts.keys()):
            cum += counts[d]
            series.append([d, cum])
        result[proc] = series
    return result


def build_done_by_area(tasks):
    by_area = defaultdict(lambda: defaultdict(int))
    for t in tasks:
        if t['status'] == ST_CONCLUIDO and t['date_done'] and t['area']:
            by_area[t['area']][t['date_done']] += 1
    result = {}
    for area, counts in by_area.items():
        cum = 0
        series = []
        for d in sorted(counts.keys()):
            cum += counts[d]
            series.append([d, cum])
        result[area] = series
    return result


# 5. Heatmap

def build_heatmap(tasks):
    ACTIVE = {ST_EM_PROGRESSO, ST_NAO_INICIADO, ST_SEM_PRAZO}
    MONTH_PT = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']

    def fmt_month(ym):
        y, m = ym.split('-')
        return '{}/{}'.format(MONTH_PT[int(m)-1], y[2:])

    area_month = defaultdict(lambda: defaultdict(int))
    area_sp    = defaultdict(int)
    months_seen = set()

    for t in tasks:
        if t['status'] not in ACTIVE:
            continue
        area = t['area'] or 'Sem Área'
        if t['status'] == ST_SEM_PRAZO or not t['due_date']:
            area_sp[area] += 1
        else:
            month = t['due_date'][:7]
            area_month[area][month] += 1
            months_seen.add(month)

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

    periods   = [fmt_month(m) for m in months]
    all_areas = sorted(
        set(area_month.keys()) | set(area_sp.keys()),
        key=lambda a: -(sum(area_month[a].values()) + area_sp[a])
    )

    rows           = []
    totals_cells   = [0] * len(months)
    total_sp       = 0

    for area in all_areas:
        cells     = [area_month[area].get(m, 0) for m in months]
        sem_prazo = area_sp[area]
        rows.append({'area': area, 'cells': cells, 'sem_prazo': sem_prazo})
        for i, v in enumerate(cells):
            totals_cells[i] += v
        total_sp += sem_prazo

    rows.append({'area': 'TOTAL', 'cells': totals_cells, 'sem_prazo': total_sp})
    max_val = max((v for r in rows[:-1] for v in r['cells']), default=1)
    max_sp  = max((r['sem_prazo'] for r in rows[:-1]), default=1)

    return {'periods': periods, 'rows': rows, 'max_val': max_val, 'max_sp': max_sp}


# 6. Logo base64

def load_logo_b64():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return ''


# 7. Geracao do HTML

def generate_html(tasks, done_by_proc, done_by_area, done_global, sp_global, atr_global, hm_data):
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    replacements = {
        '__DATE__':         DATE_FMT,
        '__TASKS__':        json.dumps(tasks,         ensure_ascii=False),
        '__DONE_BY_PROC__': json.dumps(done_by_proc,  ensure_ascii=False),
        '__DONE_BY_AREA__': json.dumps(done_by_area,  ensure_ascii=False),
        '__DONE_GLOBAL__':  json.dumps(done_global,   ensure_ascii=False),
        '__SP_GLOBAL__':    json.dumps(sp_global,     ensure_ascii=False),
        '__ATR_GLOBAL__':   json.dumps(atr_global,    ensure_ascii=False),
        '__HM_DATA__':      json.dumps(hm_data,       ensure_ascii=False),
    }
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    logo_b64 = load_logo_b64()
    if logo_b64:
        html = html.replace('Projeto-Next_brasao-1.png', 'data:image/png;base64,{}'.format(logo_b64))

    return html


# Main

def main():
    raw_tasks = fetch_all_tasks()
    tasks     = normalize_tasks(raw_tasks)
    print('Tarefas normalizadas: {}'.format(len(tasks)))

    history = load_history()
    print('Historico carregado: {} snapshots'.format(len(history)))

    snap    = build_snapshot(tasks)
    history = upsert_snapshot(history, snap)
    save_history(history)
    print('Snapshot: {}'.format(snap))

    done_global  = build_done_global(tasks)
    sp_global    = build_sp_global(history)
    atr_global   = build_atr_global(history)
    done_by_proc = build_done_by_proc(tasks)
    done_by_area = build_done_by_area(tasks)
    hm_data      = build_heatmap(tasks)

    html = generate_html(tasks, done_by_proc, done_by_area, done_global, sp_global, atr_global, hm_data)

    out_dated = os.path.join(BASE_DIR, 'ProjetoNext_Dashboard_{}.html'.format(TODAY.strftime('%Y%m%d')))
    for path in (OUT_LATEST, out_dated):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print('Salvo: {}'.format(path))

    print('Dashboard gerado com sucesso!')


if __name__ == '__main__':
    main()
