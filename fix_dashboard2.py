# Ler o arquivo original
with open(r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Identificar e corrigir as linhas problemáticas
for i in range(len(lines)):
    # Linha 93 (índice 92): const chartData
    if i == 93 and 'const chartData' in lines[i]:
        lines[i] = '                const chartData = {{ chart_data | tojson | safe }};\r\n'
        # Remover as próximas linhas se forem continuação
        if i + 1 < len(lines) and '}}' in lines[i+1] and 'const' not in lines[i+1]:
            lines[i+1] = ''
    
    # Linha 95/96: const chartLabels  
    if i == 95 and 'const chartLabels' in lines[i]:
        lines[i] = '                const chartLabels = {{ chart_labels | tojson | safe }};\r\n'
        # Remover as próximas linhas se forem continuação
        if i + 1 < len(lines) and '}}' in lines[i+1] and 'if' not in lines[i+1]:
            lines[i+1] = ''
    
    # Corrigir indentação do if
    if 'if (typeof Chart' in lines[i] and lines[i].startswith('    if'):
        lines[i] = lines[i].replace('    if (typeof Chart', '                if (typeof Chart')
    
    # Corrigir indentação do new Chart
    if 'new Chart(ctx, {' in lines[i] and lines[i].startswith('    new'):
        lines[i] = lines[i].replace('    new Chart(ctx, {', '                new Chart(ctx, {')

# Escrever de volta
with open(r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\dashboard.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Correção aplicada!")

# Verificar
with open(r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    print("\nLinhas 93-100:")
    for i in range(92, min(100, len(lines))):
        print(f"{i+1}: {lines[i]}", end='')
