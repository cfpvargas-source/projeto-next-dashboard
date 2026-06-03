# Projeto Next â€” Dashboard de GestÃ£o de Processos
## Resumo para Claude Code

---

## ðŸŽ¯ Objetivo

Gerar automaticamente um dashboard HTML interativo com dados do ClickUp, rodando diariamente via script Python. O HTML Ã© autossuficiente (todos os dados embutidos) e pode ser aberto por qualquer pessoa sem servidor.

---

## ðŸ”‘ Credenciais e IDs

```
CLICKUP_TOKEN = 'COLOQUE_NOVO_TOKEN_AQUI'
LIST_ID       = '8cktdwf-68413'
```

---

## ðŸ“ Arquivos do Projeto

| Arquivo | DescriÃ§Ã£o |
|---|---|
| `gerar_dashboard.py` | Script principal â€” busca API, processa, gera HTML |
| `dashboard_template.html` | Template HTML com placeholders `__TASKS__`, `__DATE__` etc. |
| `historico_snapshots.json` | HistÃ³rico diÃ¡rio acumulado (gerado automaticamente) |
| `ProjetoNext_Dashboard_LATEST.html` | HTML gerado â€” compartilhar este |
| `ProjetoNext_Dashboard_YYYYMMDD.html` | VersÃµes por data |
| `Projeto-Next_brasao-1.png` | Logo do Projeto Next (embutido como base64 no HTML) |

---

## ðŸ”„ Fluxo do Script

```
1. Busca todas as tarefas via API ClickUp (paginaÃ§Ã£o, 100/pÃ¡gina)
2. Normaliza campos (status, priority, Ã¡rea, processo, datas)
3. Carrega historico_snapshots.json (ou cria com seeds iniciais)
4. Adiciona snapshot do dia atual
5. Calcula curvas de evoluÃ§Ã£o (done, atraso, sem prazo) pelo histÃ³rico
6. Calcula curvas de concluÃ­das por processo e por Ã¡rea (Date Done)
7. Monta heatmap (aÃ§Ãµes em andamento/atraso/sem prazo x mÃªs de vencimento, a partir do mÃªs atual)
8. Injeta tudo no template HTML
9. Salva ProjetoNext_Dashboard_LATEST.html e ProjetoNext_Dashboard_YYYYMMDD.html
```

---

## ðŸ“Š Estrutura de Dados

### Tarefa normalizada
```python
{
    'name':      str,          # Nome da tarefa (max 80 chars)
    'status':    str,          # 'CONCLUÃDO', 'EM PROGRESSO', 'EM ATRASO',
                               # 'SEM PRAZO DEFINIDO', 'CANCELADO', 'PAUSADO', 'NÃƒO INICIADO'
    'priority':  str,          # 'urgent', 'high', 'normal', 'low'
    'area':      str,          # Coluna 'Ãrea/Departamento (drop down)'
    'proc':      str,          # Coluna 'Processo (text)' â€” normalizada
    'date_done': str | None,   # 'YYYY-MM-DD' ou None
    'due_date':  str | None,   # 'YYYY-MM-DD' ou None
    'assignee':  str,          # Username do responsÃ¡vel
}
```

### Snapshot diÃ¡rio
```python
{
    'date':               'YYYY-MM-DD',
    'total':              int,
    'CONCLUÃDO':          int,
    'EM PROGRESSO':       int,
    'EM ATRASO':          int,
    'SEM PRAZO DEFINIDO': int,
    'CANCELADO':          int,
    'PAUSADO':            int,
}
```

### Seeds iniciais do histÃ³rico (jÃ¡ conhecidos)
```python
[
    {'date':'2026-06-01','total':546,'CONCLUÃDO':186,'EM PROGRESSO':116,'EM ATRASO':68,'SEM PRAZO DEFINIDO':101,'CANCELADO':50,'PAUSADO':20},
    {'date':'2026-06-02','total':546,'CONCLUÃDO':188,'EM PROGRESSO':116,'EM ATRASO':66,'SEM PRAZO DEFINIDO':102,'CANCELADO':50,'PAUSADO':20},
]
```

---

## ðŸ—‚ï¸ Processos (normalizaÃ§Ã£o obrigatÃ³ria)

```python
def norm_proc(p):
    p = p.strip().rstrip('\n').strip()
    # Engenharia e GMO sÃ£o o MESMO processo
    if p in ('Engenharia', 'GMO'):
        return 'Engenharia e GMO'
    return p
```

**Processos vÃ¡lidos:**
- Novos NegÃ³cios
- IncorporaÃ§Ã£o Make It
- IncorporaÃ§Ã£o Gadens
- Engenharia e GMO â† unificado
- Suprimentos
- Financeiro

---

## ðŸŒ¡ï¸ VelocÃ­metro de Atraso â€” Regra

```
Verde   â†’ 0â€“5%   de aÃ§Ãµes em atraso sobre o total filtrado
Amarelo â†’ 5â€“10%
Vermelho â†’ >10%
```

---

## ðŸ“ˆ GrÃ¡ficos de EvoluÃ§Ã£o â€” Regras

| GrÃ¡fico | Filtro ativo? | Fonte |
|---|---|---|
| ConcluÃ­das acumulado | SEM filtro | HistÃ³rico de snapshots |
| ConcluÃ­das acumulado | COM filtro (processo OU Ã¡rea) | Calculado do Date Done das tarefas filtradas |
| ConcluÃ­das acumulado | COM ambos os filtros | **NÃ£o exibe** (sem dados) |
| Sem prazo definido | SEM filtro | HistÃ³rico de snapshots |
| Sem prazo definido | COM qualquer filtro | **NÃ£o exibe** (histÃ³rico indisponÃ­vel) |
| Em atraso | SEM filtro | HistÃ³rico de snapshots |
| Em atraso | COM qualquer filtro | **NÃ£o exibe** (histÃ³rico indisponÃ­vel) |

> âš ï¸ Regra combinada: **nunca inventar ou estimar dados. Se nÃ£o hÃ¡ histÃ³rico filtrado, esconde o grÃ¡fico.**

---

## ðŸ”¥ Heatmap

- Linhas: Ã¡reas/departamentos (ordenadas por volume total de tarefas)
- Colunas: meses de vencimento (**apenas a partir do mÃªs atual**)
- CÃ©lulas: quantidade de tarefas EM PROGRESSO + EM ATRASO + SEM PRAZO DEFINIDO com due_date naquele mÃªs
- Ãšltima coluna "Sem Prazo": tarefas EM PROGRESSO + EM ATRASO + SEM PRAZO DEFINIDO **sem** due_date
- Escala de cor: azul monocromÃ¡tico (intensidade = volume) â€” zero = fundo escuro
- Coluna "Sem Prazo": Ã¢mbar com intensidade variando
- NÃºmero branco em cÃ©lulas escuras, azul claro em cÃ©lulas claras
- Linha TOTAL no rodapÃ©

---

## ðŸ–¼ï¸ Template HTML â€” Placeholders

```
__DATE__         â†’ Data de geraÃ§Ã£o (ex: '03/06/2026')
__TASKS__        â†’ JSON array de tarefas normalizadas
__DONE_BY_PROC__ â†’ JSON dict {processo: [[date, cum_count], ...]}
__DONE_BY_AREA__ â†’ JSON dict {area: [[date, cum_count], ...]}
__DONE_GLOBAL__  â†’ JSON array [[date, cum_count], ...] â€” curva global de concluÃ­das
__SP_GLOBAL__    â†’ JSON array [[date, count], ...] â€” sem prazo (snapshot semanal)
__ATR_GLOBAL__   â†’ JSON array [[date, count], ...] â€” em atraso (snapshot semanal)
__HM_DATA__      â†’ JSON object do heatmap
```

---

## ðŸŽ¨ Design / Visual

- Fundo: `#07112b` (azul escuro)
- Header: `#0c1e3e`
- Fonte: Barlow + Barlow Condensed (Google Fonts)
- Verde acento: `#3de8b0`
- Azul barras: `#2a7acc`
- Vermelho atraso: `#e85858`
- Ã‚mbar sem prazo: `#f5a623`
- Logo: `Projeto-Next_brasao-1.png` embutido como base64 no HTML
- TÃ­tulo header: "GestÃ£o de Processos â€” Projeto Next" em **uma linha**

---

## âš™ï¸ Ãndice Geral de ImplementaÃ§Ã£o

> Sempre calculado sobre **o total geral do projeto** (ALL_TASKS), independente de filtros ativos.

---

## ðŸ“… Agendamento Sugerido

**Windows (Task Scheduler):**
```
Programa: python
Argumentos: C:\caminho\gerar_dashboard.py
Trigger: Todo dia Ã s 08:00
```

**Mac/Linux (cron):**
```bash
0 8 * * * /usr/bin/python3 /caminho/gerar_dashboard.py
```

---

## ðŸ“¦ DependÃªncias Python

```bash
pip install requests
# Python stdlib: json, os, datetime, collections
```

---

## ðŸ” PrÃ³ximos Passos no Claude Code

1. Criar `gerar_dashboard.py` com toda a lÃ³gica descrita acima
2. Testar a busca da API do ClickUp
3. Validar geraÃ§Ã£o do HTML com os placeholders do template
4. Configurar agendamento automÃ¡tico
5. (Futuro) Adicionar upload automÃ¡tico para Google Drive ou servidor

---

*Gerado em 03/06/2026 â€” Conversa Claude.ai â†’ Claude Code*

