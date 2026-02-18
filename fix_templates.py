import os

def fix_file(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Clean up any mess from previous attempts
    new_content = content.replace('{% raw %}', '').replace('{% endraw %}', '')
    
    # Normalize double braces (remove spaces)
    new_content = new_content.replace('{ {', '{{').replace('} }', '}}')
    
    # Fix the triple brace issue created by the previous run
    new_content = new_content.replace('}}}', '}}')
    
    # Ensure proper closing for specific tags (idempotent)
    if '{{ current_user.id }}' not in new_content and '{{ current_user.id }' in new_content:
        new_content = new_content.replace('{{ current_user.id }', '{{ current_user.id }}')
    
    if "{{ 'true' if current_user.is_admin else 'false' }}" not in new_content and "{{ 'true' if current_user.is_admin else 'false' }" in new_content:
        new_content = new_content.replace("{{ 'true' if current_user.is_admin else 'false' }", "{{ 'true' if current_user.is_admin else 'false' }}")

    # Remove double semicolons if any
    new_content = new_content.replace(';;', ';')
    
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed: {path}")
    else:
        print(f"No changes needed: {path}")

if __name__ == "__main__":
    base_path = r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\base.html'
    dash_path = r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\dashboard.html'
    
    fix_file(base_path)
    fix_file(dash_path)
