
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.innerHTML = `
                <span style="flex-grow: 1;">${message}</span>
                <span style="margin-left: 1rem; opacity: 0.7; font-size: 1.25rem;">&times;</span>
            `;

            toast.onclick = () => {
                toast.classList.add('fade-out');
                setTimeout(() => toast.remove(), 500);
            };

            container.appendChild(toast);

            // Auto-remove after 6 seconds
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.classList.add('fade-out');
                    setTimeout(() => toast.remove(), 500);
                }
            }, 6000);
        }

        // Inicialização Principal
        document.addEventListener('DOMContentLoaded', () => {
            // Ler mensagens flash do Flask
            {% with messages = get_flashed_messages(with_categories = true) %}
            {% if messages %}
            {% for category, message in messages %}
            showToast({{ message | tojson | safe }}, {{ ('error' if category == 'error' else 'success') | tojson | safe }});
        {% endfor %}
        {% endif %}
        {% endwith %}

        // Toggle Dropdowns
        const userBtn = document.getElementById('user-menu-btn');
        const userDropdown = document.getElementById('user-dropdown');
        const notifBtn = document.getElementById('notif-btn');
        const notifDropdown = document.getElementById('notif-dropdown');

        if (userBtn && userDropdown && notifBtn && notifDropdown) {
            userBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                userDropdown.classList.toggle('show');
                notifDropdown.classList.remove('show');
            });

            notifBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                notifDropdown.classList.toggle('show');
                userDropdown.classList.remove('show');
            });

            document.addEventListener('click', () => {
                userDropdown.classList.remove('show');
                notifDropdown.classList.remove('show');
            });

            [userDropdown, notifDropdown].forEach(d => {
                d.addEventListener('click', (e) => e.stopPropagation());
            });
        }

        // Profile Modal Logic
        const profileModal = document.getElementById('profile-modal');
        const openProfileBtn = document.getElementById('open-profile-btn');
        const closeProfileBtn = document.getElementById('close-profile-btn');

        if (openProfileBtn && closeProfileBtn && profileModal) {
            openProfileBtn.addEventListener('click', (e) => {
                e.preventDefault();
                profileModal.classList.add('show');
                if (userDropdown) userDropdown.classList.remove('show');
            });

            closeProfileBtn.addEventListener('click', () => {
                profileModal.classList.remove('show');
            });
        }

        // Settings Modal Logic
        const settingsModal = document.getElementById('settings-modal');
        const openSettingsBtn = document.getElementById('open-settings-btn');
        const closeSettingsBtn = document.getElementById('close-settings-btn');

        if (openSettingsBtn && closeSettingsBtn && settingsModal) {
            openSettingsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                loadSettings();
                settingsModal.classList.add('show');
                if (userDropdown) userDropdown.classList.remove('show');
            });

            closeSettingsBtn.addEventListener('click', () => {
                settingsModal.classList.remove('show');
            });
        }

        window.addEventListener('click', (e) => {
            if (e.target === profileModal) {
                profileModal.classList.remove('show');
            }
            if (e.target === settingsModal) {
                settingsModal.classList.remove('show');
            }
            if (e.target === document.getElementById('titulo-action-modal')) {
                closeTituloActionModal();
            }
        });
        });

        // --- Lógica de Configurações ---
        function switchSettingsTab(tabId) {
            // Atualizar botões
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === tabId);
            });
            // Atualizar conteúdos
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.toggle('active', content.id === tabId);
            });

            if (tabId === 'tab-users') {
                loadUsers();
            }
        }

        function loadSettings() {
            fetch('{{ url_for("auth.manage_config") }}')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('cfg-smtp-host').value = data.SMTP_HOST || '';
                    document.getElementById('cfg-smtp-port').value = data.SMTP_PORT || '';
                    document.getElementById('cfg-smtp-user').value = data.SMTP_USER || '';
                    document.getElementById('cfg-smtp-pass').value = data.SMTP_PASS || '';
                    document.getElementById('cfg-smtp-tls').checked = !!data.SMTP_USE_TLS;
                    document.getElementById('cfg-smtp-ssl').checked = !!data.SMTP_USE_SSL;
                });
        }

        function loadUsers() {
            const tbody = document.getElementById('user-list-body');
            if (!tbody) return;
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Carregando usuários...</td></tr>';

            fetch('{{ url_for("auth.list_users") }}')
                .then(res => res.json())
                .then(data => {
                    tbody.innerHTML = '';
                    const currentUserId = {{ (current_user.id if current_user.is_authenticated else none) | tojson }};
            const isAdmin = {{ (current_user.is_admin if current_user.is_authenticated else false) | tojson }};

        data.users.forEach(user => {
            const tr = document.createElement('tr');
            const roleBadge = user.is_admin ? '<span class="badge-admin">Admin</span>' : '<span class="badge-user">Usuário</span>';

            let actionsHtml = '';
            if (isAdmin && user.id !== currentUserId) {
                actionsHtml = `<button class="btn-resend" onclick='resendPassword(${JSON.stringify(user.id)}, ${JSON.stringify(user.nome)})' title="Reenviar Senha">Reenviar Senha</button> <button class="btn-delete" onclick='deleteUser(${JSON.stringify(user.id)}, ${JSON.stringify(user.nome)})' title="Excluir Usuário">Excluir</button>`;
            } else if (user.id === currentUserId) {
                actionsHtml = '<small class="text-muted">Você</small>';
            }

            tr.innerHTML = `
                            <td>${user.nome}</td>
                            <td>${user.email}</td>
                            <td>${roleBadge}</td>
                            <td>${user.data_criacao}</td>
                            <td>${actionsHtml}</td>
                        `;
            tbody.appendChild(tr);
        });
                })
                .catch (err => {
            console.error('Erro ao buscar usuários:', err);
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #e74c3c;">Erro ao carregar usuários.</td></tr>';
        });
        }

        function resendPassword(userId, userName) {
            if (!confirm(`Deseja gerar uma nova senha temporária para ${userName} e enviar por e-mail?`)) return;

            showToast("Processando...", "info");

            fetch(`/api/users/${userId}/resend-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        showToast(data.message, "success");
                    } else {
                        showToast(data.message, "warning");
                    }
                })
                .catch(err => {
                    showToast("Erro ao processar solicitação.", "error");
                });
        }

        function deleteUser(userId, userName) {
            if (!confirm(`Tem certeza que deseja excluir o usuário "${userName}"? Esta ação não pode ser desfeita.`)) {
                return;
            }

            fetch(`/api/users/${userId}/delete`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        showToast(data.message, 'success');
                        loadUsers();
                    } else {
                        showToast(data.message, 'error');
                    }
                })
                .catch(err => showToast('Erro ao excluir usuário.', 'error'));
        }

        function toggleUserForm(show) {
            const form = document.getElementById('user-registration-form');
            form.style.display = show ? 'block' : 'none';
            if (!show) {
                document.getElementById('new-user-nome').value = '';
                document.getElementById('new-user-email').value = '';
                document.getElementById('new-user-admin').checked = false;
            }
        }

        function submitNewUser() {
            const nome = document.getElementById('new-user-nome').value;
            const email = document.getElementById('new-user-email').value;
            const is_admin = document.getElementById('new-user-admin').checked;

            if (!nome || !email) {
                showToast('Preencha Nome e E-mail.', 'error');
                return;
            }

            const data = { nome, email, is_admin };

            fetch('{{ url_for("auth.add_user") }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
                .then(res => res.json())
                .then(resData => {
                    if (resData.success) {
                        showToast(resData.message, 'success');
                        toggleUserForm(false);
                        loadUsers(); // Recarregar a lista
                    } else {
                        showToast(resData.message, 'error');
                    }
                })
                .catch(err => showToast('Erro ao cadastrar usuário.', 'error'));
        }

        function saveSettings() {
            const data = {
                SMTP_HOST: document.getElementById('cfg-smtp-host').value,
                SMTP_PORT: document.getElementById('cfg-smtp-port').value,
                SMTP_USER: document.getElementById('cfg-smtp-user').value,
                SMTP_PASS: document.getElementById('cfg-smtp-pass').value,
                SMTP_USE_TLS: document.getElementById('cfg-smtp-tls').checked,
                SMTP_USE_SSL: document.getElementById('cfg-smtp-ssl').checked
            };

            fetch('{{ url_for("auth.manage_config") }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
                .then(res => res.json())
                .then(resData => {
                    if (resData.success) {
                        showToast(resData.message, 'success');
                        document.getElementById('settings-modal').classList.remove('show');
                    } else {
                        showToast(resData.message, 'error');
                    }
                })
                .catch(err => showToast('Erro ao salvar configurações.', 'error'));
        }

        // --- Lógica de Backup ---
        function downloadBackup() {
            window.location.href = '{{ url_for("auth.export_backup") }}';
        }

        function performRestore() {
            const fileInput = document.getElementById('restore-file');
            if (fileInput.files.length === 0) {
                showToast("Selecione um arquivo CSV para restaurar.", "warning");
                return;
            }

            if (!confirm("CONFIRMAÇÃO CRÍTICA: Deseja realmente APAGAR TUDO e restaurar os dados deste arquivo? Esta ação não pode ser desfeita.")) {
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            showToast("Restaurando dados... Por favor, aguarde.", "info");

            fetch('{{ url_for("auth.restore_backup") }}', {
                method: 'POST',
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        showToast(data.message, "success");
                        setTimeout(() => window.location.reload(), 2000);
                    } else {
                        showToast(data.message, "error");
                    }
                })
                .catch(err => {
                    console.error(err);
                    showToast("Erro técnico ao restaurar dados.", "error");
                });
        }

        // --- Lógica do Modal de Ações de Título ---
        let currentTituloId = null;

        function openTituloActionModal(tituloId) {
            currentTituloId = tituloId;
            const modal = document.getElementById('titulo-action-modal');
            const dropdown = document.getElementById('notif-dropdown');

            // Fechar dropdown de notificação
            dropdown.classList.remove('show');

            // Resetar formulários
            toggleLiquidationForm(false);

            // Buscar dados via API
            fetch(`/financeiro/api/titulo/${tituloId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showToast(data.error, 'error');
                        return;
                    }

                    document.getElementById('modal-titulo-nome').innerText = data.descricao;
                    document.getElementById('modal-titulo-valor').innerText = `R$ ${data.valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
                    document.getElementById('modal-titulo-vencimento').innerText = data.data_vencimento;
                    document.getElementById('modal-titulo-entidade').innerText = data.entidade;

                    // Preencher bancos
                    const bancoSelect = document.getElementById('modal-banco-id');
                    bancoSelect.innerHTML = data.bancos.map(b => `<option value="${b.id}">${b.nome}</option>`).join('');

                    // Preencher data hoje
                    document.getElementById('modal-data-pagamento').value = new Date().toISOString().split('T')[0];

                    modal.classList.add('show');
                })
                .catch(err => {
                    console.error(err);
                    showToast('Erro ao carregar detalhes do título.', 'error');
                });
        }

        function closeTituloActionModal() {
            document.getElementById('titulo-action-modal').classList.remove('show');
            currentTituloId = null;
        }

        function toggleLiquidationForm(show) {
            document.getElementById('liquidation-form').style.display = show ? 'block' : 'none';
            document.getElementById('modal-actions-standard').style.display = show ? 'none' : 'flex';
        }

        function confirmLiquidar() {
            const bancoId = document.getElementById('modal-banco-id').value;
            const dataPagamento = document.getElementById('modal-data-pagamento').value;

            if (!bancoId || !dataPagamento) {
                showToast('Preencha todos os campos para liquidar.', 'error');
                return;
            }

            fetch(`/financeiro/api/liquidar/${currentTituloId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ banco_id: bancoId, data_pagamento: dataPagamento })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        showToast(data.message, 'success');
                        closeTituloActionModal();
                        // Opcional: recarregar a página para atualizar os dados gerais
                        setTimeout(() => window.location.reload(), 1500);
                    } else {
                        showToast(data.message, 'error');
                    }
                })
                .catch(err => showToast('Erro na requisição de liquidação.', 'error'));
        }

        function confirmEstornar() {
            if (!confirm('Tem certeza que deseja estornar este título? Esta ação reverterá os lançamentos contábeis.')) {
                return;
            }

            fetch(`/financeiro/api/estornar/${currentTituloId}`, {
                method: 'POST'
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        showToast(data.message, 'success');
                        closeTituloActionModal();
                        setTimeout(() => window.location.reload(), 1500);
                    } else {
                        showToast(data.message, 'error');
                    }
                })
                .catch(err => showToast('Erro na requisição de estorno.', 'error'));
        }

        // --- Lógica de Tema (Modo Escuro / Claro) ---
        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';

            // Aplicar Visualmente
            html.setAttribute('data-theme', newTheme);
            const btn = document.getElementById('theme-toggle');
            if (btn) btn.innerHTML = newTheme === 'dark' ? '<span>🌙</span>' : '<span>☀️</span>';

            // Persistir via API
            fetch('{{ url_for("auth.update_theme") }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tema: newTheme })
            })
                .then(res => res.json())
                .then(data => {
                    if (!data.success) {
                        showToast('Erro ao salvar preferência de tema.', 'warning');
                    }
                })
                .catch(err => console.error('Erro ao chamar API de tema:', err));
        }
    