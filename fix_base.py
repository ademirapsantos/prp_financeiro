
import os

file_path = r"c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\base.html"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = 0
for i in range(len(lines)):
    if skip > 0:
        skip -= 1
        continue
    
    line = lines[i]
    
    # Corrigir o bloco loadUsers quebrado
    if "const currentUserId = {{ current_user.id or 'null' }" in line:
        new_lines.append("                    const currentUserId = {{ current_user.id or 'null' }};\n")
        # Verificar se as próximas linhas são o lixo que queremos remover
        if i + 3 < len(lines) and "isAdmin =" in lines[i+2]:
            new_lines.append("                    const isAdmin = {{ 'true' if current_user.is_admin else 'false' }};\n")
            skip = 3 # pular as linhas de lixo }; e const isAdmin incompleto };
        continue
    
    # Corrigir o bloco DOMContentLoaded se estiver errado
    if "document.addEventListener('DOMContentLoaded', () => {" in line:
        # Pega as próximas linhas até achar o endwith
        found_endwith = False
        temp_block = [line]
        for j in range(i+1, min(i+10, len(lines))):
            temp_block.append(lines[j])
            if "{% endwith %}" in lines[j]:
                found_endwith = True
                # Verificar se o fechamento }); ja existe
                if j+1 < len(lines) and "});" in lines[j+1]:
                    pass # Ja esta certo
                else:
                    temp_block.append("        });\n")
                skip = j - i
                break
        if found_endwith:
            new_lines.extend(temp_block)
            continue

    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Reparo concluído com sucesso.")
