
import os

file_path = r"c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\base.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Procura a parte corrompida exata
corrupted = """                    const currentUserId = {{ current_user.id or 'null' }
                };
            const isAdmin = {{ 'true' if current_user.is_admin else 'false' }
        };

        data.users.forEach(user => {"""

fixed = """                    const currentUserId = {{ current_user.id or 'null' }};
                    const isAdmin = {{ 'true' if current_user.is_admin else 'false' }};

                    data.users.forEach(user => {"""

if corrupted in content:
    new_content = content.replace(corrupted, fixed)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Sucesso: A parte corrompida foi encontrada e corrigida.")
else:
    print("Erro: A parte corrompida não foi encontrada. Verificando alternativas...")
    # Tenta uma busca mais flexível
    import re
    pattern = r"const currentUserId = \{\{ current_user\.id or 'null' \}\s+\};\s+const isAdmin = \{\{ 'true' if current_user\.is_admin else 'false' \}\s+\};"
    # Note: O padrão acima pode estar errado se as chaves estiverem faltando no arquivo.
    
    # Busca pela versão SEM as chaves de fechamento
    pattern_corrupted = r"const currentUserId = \{\{ current_user\.id or 'null' \}\s+\};\s+const isAdmin = \{\{ 'true' if current_user\.is_admin else 'false' \}\s+\};"
    
    # Honestamente, o melhor é ler as linhas e procurar por substrings
    lines = content.splitlines()
    new_lines = []
    found = False
    skip = 0
    for i in range(len(lines)):
        if skip > 0:
            skip -= 1
            continue
        
        if "const currentUserId = {{ current_user.id or 'null' }" in lines[i] and "}}" not in lines[i]:
            new_lines.append("                    const currentUserId = {{ current_user.id or 'null' }};")
            new_lines.append("                    const isAdmin = {{ 'true' if current_user.is_admin else 'false' }};")
            new_lines.append("")
            new_lines.append("                    data.users.forEach(user => {")
            # Encontrar quantas linhas pular
            for j in range(i+1, min(i+10, len(lines))):
                if "data.users.forEach" in lines[j]:
                    skip = j - i
                    break
            found = True
            continue
        new_lines.append(lines[i])
    
    if found:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\\n".join(new_lines))
        print("Sucesso: Corrigido via busca de linhas.")
    else:
        print("Falha: Não foi possível localizar a corrupção.")
