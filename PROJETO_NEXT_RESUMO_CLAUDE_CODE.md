# Projeto Next — Dashboard de Gestão de Processos
## Resumo para Claude Code

---

## 🎯 Objetivo

Gerar automaticamente um dashboard HTML interativo com dados do ClickUp, rodando diariamente via script Python. O HTML é autossuficiente (todos os dados embutidos) e pode ser aberto por qualquer pessoa sem servidor.

---

## 🔑 Credenciais e IDs

```
CLICKUP_TOKEN = 'pk_106059012_QLRKVG2H9W4FW459I0LE0Q1S6DR8ZDF4'
LIST_ID       = '8cktdwf-68413'
```

---

## 📁 Arquivos do Projeto

| Arquivo | Descrição |
|---|---|
| `gerar_dashboard.py` | Script principal — busca API, processa, gera HTML |
| `dashboard_template.html` | Template HTML com placeholders `__TASKS__`, `__DATE__` etc. |
| `historico_snapshots.json` | Histórico diário acumulado (gerado automaticamente) |
| `ProjetoNext_Dashboard_LATEST.html` | HTML gerado — compartilhar este |
| `ProjetoNext_Dashboard_YYYYMMDD.html` | Versões por data |
| `Projeto-Next_brasao-1.png` | Logo do Projeto Next (embutido como base64 no HTML) |

---

## 🔄 Fluxo do Script

```
1. Busca todas as tarefas via API ClickUp (paginação, 100/página)
2. Normaliza campos (status, priority, área, processo, datas)
3. Carrega historico_snapshots.json (ou cria com seeds iniciais)
4. Adiciona snapshot do dia atual
5. Calcula curvas de evolução (done, atraso, sem prazo) pelo histórico
6. Calcula curvas de concluídas por processo e por área (Date Done)
7. Monta heatmap (ações em andamento/atraso/sem prazo x mês de vencimento, a partir do mês atual)
8. Injeta tudo no template HTML
9. Salva ProjetoNext_Dashboard_LATEST.html e ProjetoNext_Dashboard_YYYYMMDD.html
```

---

## 📊 Estrutura de Dados

### Tarefa normalizada
```python
{
    'name':      str,          # Nome da tarefa (max 80 chars)
    'status':    str,          # 'CONCLUÍDO', 'EM PROGRESSO', 'EM ATRASO',
                               # 'SEM PRAZO DEFINIDO', 'CANCELADO', 'PAUSADO', 'NÃO INICIADO'
    'priority':  str,          # 'urgent', 'high', 'normal', 'low'
    'area':      str,          # Coluna 'Área/Departamento (drop down)'
    'proc':      str,          # Coluna 'Processo (text)' — normalizada
    'date_done': str | None,   # 'YYYY-MM-DD' ou None
    'due_date':  str | None,   # 'YYYY-MM-DD' ou None
    'assignee':  str,          # Username do responsável
}
```

### Snapshot diário
```python
{
    'date':               'YYYY-MM-DD',
    'total':              int,
    'CONCLUÍDO':          int,
    'EM PROGRESSO':       int,
    'EM ATRASO':          int,
    'SEM PRAZO DEFINIDO': int,
    'CANCELADO':          int,
    'PAUSADO':            int,
}
```

### Seeds iniciais do histórico (já conhecidos)
```python
[
    {'date':'2026-06-01','total':546,'CONCLUÍDO':186,'EM PROGRESSO':116,'EM ATRASO':68,'SEM PRAZO DEFINIDO':101,'CANCELADO':50,'PAUSADO':20},
    {'date':'2026-06-02','total':546,'CONCLUÍDO':188,'EM PROGRESSO':116,'EM ATRASO':66,'SEM PRAZO DEFINIDO':102,'CANCELADO':50,'PAUSADO':20},
]
```

---

## 🗂️ Processos (normalização obrigatória)

```python
def norm_proc(p):
    p = p.strip().rstrip('\n').strip()
    # Engenharia e GMO são o MESMO processo
    if p in ('Engenharia', 'GMO'):
        return 'Engenharia e GMO'
    return p
```

**Processos válidos:**
- Novos Negócios
- Incorporação Make It
- Incorporação Gadens
- Engenharia e GMO ← unificado
- Suprimentos
- Financeiro

---

## 🌡️ Velocímetro de Atraso — Regra

```
Verde   → 0–5%   de ações em atraso sobre o total filtrado
Amarelo → 5–10%
Vermelho → >10%
```

---

## 📈 Gráficos de Evolução — Regras

| Gráfico | Filtro ativo? | Fonte |
|---|---|---|
| Concluídas acumulado | SEM filtro | Histórico de snapshots |
| Concluídas acumulado | COM filtro (processo OU área) | Calculado do Date Done das tarefas filtradas |
| Concluídas acumulado | COM ambos os filtros | **Não exibe** (sem dados) |
| Sem prazo definido | SEM filtro | Histórico de snapshots |
| Sem prazo definido | COM qualquer filtro | **Não exibe** (histórico indisponível) |
| Em atraso | SEM filtro | Histórico de snapshots |
| Em atraso | COM qualquer filtro | **Não exibe** (histórico indisponível) |

> ⚠️ Regra combinada: **nunca inventar ou estimar dados. Se não há histórico filtrado, esconde o gráfico.**

---

## 🔥 Heatmap

- Linhas: áreas/departamentos (ordenadas por volume total de tarefas)
- Colunas: meses de vencimento (**apenas a partir do mês atual**)
- Células: quantidade de tarefas EM PROGRESSO + EM ATRASO + SEM PRAZO DEFINIDO com due_date naquele mês
- Última coluna "Sem Prazo": tarefas EM PROGRESSO + EM ATRASO + SEM PRAZO DEFINIDO **sem** due_date
- Escala de cor: azul monocromático (intensidade = volume) — zero = fundo escuro
- Coluna "Sem Prazo": âmbar com intensidade variando
- Número branco em células escuras, azul claro em células claras
- Linha TOTAL no rodapé

---

## 🖼️ Template HTML — Placeholders

```
__DATE__         → Data de geração (ex: '03/06/2026')
__TASKS__        → JSON array de tarefas normalizadas
__DONE_BY_PROC__ → JSON dict {processo: [[date, cum_count], ...]}
__DONE_BY_AREA__ → JSON dict {area: [[date, cum_count], ...]}
__DONE_GLOBAL__  → JSON array [[date, cum_count], ...] — curva global de concluídas
__SP_GLOBAL__    → JSON array [[date, count], ...] — sem prazo (snapshot semanal)
__ATR_GLOBAL__   → JSON array [[date, count], ...] — em atraso (snapshot semanal)
__HM_DATA__      → JSON object do heatmap
```

---

## 🎨 Design / Visual

- Fundo: `#07112b` (azul escuro)
- Header: `#0c1e3e`
- Fonte: Barlow + Barlow Condensed (Google Fonts)
- Verde acento: `#3de8b0`
- Azul barras: `#2a7acc`
- Vermelho atraso: `#e85858`
- Âmbar sem prazo: `#f5a623`
- Logo: `Projeto-Next_brasao-1.png` embutido como base64 no HTML
- Título header: "Gestão de Processos — Projeto Next" em **uma linha**

---

## ⚙️ Índice Geral de Implementação

> Sempre calculado sobre **o total geral do projeto** (ALL_TASKS), independente de filtros ativos.

---

## 📅 Agendamento Sugerido

**Windows (Task Scheduler):**
```
Programa: python
Argumentos: C:\caminho\gerar_dashboard.py
Trigger: Todo dia às 08:00
```

**Mac/Linux (cron):**
```bash
0 8 * * * /usr/bin/python3 /caminho/gerar_dashboard.py
```

---

## 📦 Dependências Python

```bash
pip install requests
# Python stdlib: json, os, datetime, collections
```

---

## 🔁 Próximos Passos no Claude Code

1. Criar `gerar_dashboard.py` com toda a lógica descrita acima
2. Testar a busca da API do ClickUp
3. Validar geração do HTML com os placeholders do template
4. Configurar agendamento automático
5. (Futuro) Adicionar upload automático para Google Drive ou servidor

---

*Gerado em 03/06/2026 — Conversa Claude.ai → Claude Code*
