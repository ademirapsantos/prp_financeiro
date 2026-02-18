import re

# Ler o arquivo
with open(r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Corrigir o primeiro problema (chart_data)
content = re.sub(
    r'const chartData = \{\{ chart_data \| tojson \| safe\s*\}\};',
    'const chartData = {{ chart_data | tojson | safe }};',
    content,
    flags=re.DOTALL
)

# Corrigir o segundo problema (chart_labels)  
content = re.sub(
    r'const chartLabels = \{\{ chart_labels \| tojson \| safe\s*\}\};',
    'const chartLabels = {{ chart_labels | tojson | safe }};',
    content,
    flags=re.DOTALL
)

# Corrigir indentação do if
content = content.replace('    if (typeof Chart', '                if (typeof Chart')

# Corrigir indentação do new Chart
content = content.replace('    new Chart(ctx, {', '                new Chart(ctx, {')

# Escrever de volta
with open(r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Arquivo corrigido com sucesso!")
