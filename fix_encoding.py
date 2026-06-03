path = r'C:\Users\carlos.vargas\OneDrive - Grupo Gadens\Processos - Projeto Next\ProjetoNext_Dashboard\gerar_dashboard.py'

with open(path, encoding='utf-8') as f:
    c = f.read()

replacements = [
    ('CONCLUÃDO',   'CONCLUÍDO'),
    ('concluÃ­do',  'concluído'),
    ('NÃO',         'NÃO'),
    ('revisÃ£o',    'revisão'),
    ('NÃƒO',        'NÃO'),
    ('Ã³',          'ó'),
    ('Ã§Ã£o',       'ção'),
    ('Ã£o',         'ão'),
    ('Ã¡',          'á'),
    ('Ã©',          'é'),
    ('Ãª',          'ê'),
    ('Ã­',          'í'),
    ('Ãµ',          'õ'),
    ('Ã¼',          'ü'),
]

for bad, good in replacements:
    c = c.replace(bad, good)

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

# Verificar
ok = all(x in c for x in ['CONCLUÍDO', 'NÃO INICIADO'])
print('OK!' if ok else 'AINDA COM PROBLEMA')
print('CONCLUÍDO:', 'CONCLUÍDO' in c)
print('NÃO INICIADO:', 'NÃO INICIADO' in c)
