
import os

file_path = r"c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\base.html"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = 0

# 1. Encontrar o bloco loadUsers e consertar
# 2. Garantir que o DOMContentLoaded está fechado corretamente

for i in range(len(lines)):
    if skip > 0:
        skip -= 1
        continue
    
    line = lines[i]
    
    # Conserto do loadUsers (linhas 591-594 aproximadamente)
    if "const currentUserId = {{ current_user.id or 'null' }" in line and "}}" not in line:
        new_lines.append("                    const currentUserId = {{ current_user.id or 'null' }};\n")
        new_lines.append("                    const isAdmin = {{ 'true' if current_user.is_admin else 'false' }};\n")
        new_lines.append("\n")
        new_lines.append("                    data.users.forEach(user => {\n")
        # Pular até encontrar o loop
        for j in range(i+1, min(i+10, len(lines))):
            if "data.users.forEach" in lines[j]:
                skip = j - i
                break
        continue

    # Garantir que o closure do DOMContentLoaded está certo
    # O DOMContentLoaded começa por volta da 473.
    # O closure deve estar apos o window.addEventListener click
    if "window.addEventListener('click', (e) => {" in line:
        # Pega todo o bloco ate o fechamento
        found_end = False
        temp_block = []
        for j in range(i, len(lines)):
            temp_block.append(lines[j])
            if "        });" in lines[j] and j > i: # Encontrou um });
                # Verifica se a proxima linha ja e um });
                if j+1 < len(lines) and "        });" in lines[j+1]:
                    # Ja tem dois fechamentos, esta certo.
                    new_lines.extend(temp_block)
                    skip = j - i
                else:
                    # Adiciona o fechamento que falta
                    temp_block.append("        });\n")
                    new_lines.extend(temp_block)
                    skip = j - i
                found_end = True
                break
        if found_end:
            continue

    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Reparo total concluído.")
