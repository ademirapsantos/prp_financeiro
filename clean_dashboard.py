# Ler o arquivo
with open(r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Encontrar a posição do primeiro </script> após o gráfico
first_script_end = content.find('</script>', content.find('Chart.js'))

# Encontrar {% endblock %} após o primeiro </script>
first_endblock = content.find('{% endblock %}', first_script_end)

# Pegar tudo até o primeiro {% endblock %} (incluindo)
clean_content = content[:first_endblock + len('{% endblock %}')]

# Escrever de volta
with open(r'c:\Users\Ademir Santos\.gemini\antigravity\scratch\prp_financeiro\app\templates\dashboard.html', 'w', encoding='utf-8') as f:
    f.write(clean_content)

print("Arquivo limpo!")
print(f"Tamanho final: {len(clean_content)} bytes")
