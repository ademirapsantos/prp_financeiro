
        async function checkUpdate() {
            const currentVersion = "{{ app_version }}";
            const ignoredVersion = localStorage.getItem('ignored_version');

            try {
                const response = await fetch('/api/system/latest');
                const data = await response.json();

                if (data.maintenance) {
                    window.location.reload();
                    return;
                }

                if (data.is_new && data.latest_version !== ignoredVersion) {
                    document.getElementById('new-version-tag').innerText = 'v' + data.latest_version;
                    document.getElementById('update-modal').classList.add('show');

                    // Guardar payload globalmente para "Mais Tarde"
                    window.latestUpdate = data;
                }
            } catch (e) {
                console.error('Falha ao checar atualização', e);
            }
        }

        async function ignoreUpdate() {
            const version = document.getElementById('new-version-tag').innerText.replace('v', '');

            // Persistir no DB como notificação se clicar em "Mais Tarde"
            if (window.latestUpdate) {
                try {
                    const res = await fetch('/api/notifications', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            tipo: 'UPDATE_AVAILABLE',
                            titulo: 'Atualização Disponível',
                            mensagem: `A versão v${window.latestUpdate.latest_version} está disponível. Clique para atualizar.`,
                            payload: window.latestUpdate
                        })
                    });
                    const data = await res.json();

                    if (data.status === 'success') {
                        // Atualizar sino em real-time
                        const notifList = document.querySelector('.notification-list');
                        const emptyItem = notifList.querySelector('.empty-notif');
                        if (emptyItem) emptyItem.remove();

                        const newItem = document.createElement('li');
                        newItem.id = `notif-item-${data.id}`;
                        newItem.style.cursor = 'pointer';

                        // Usar event listener para evitar problemas de aspas com JSON.stringify
                        const currentUpdate = { ...window.latestUpdate };
                        newItem.addEventListener('click', () => {
                            handleSystemNotif(data.id, 'UPDATE_AVAILABLE', currentUpdate);
                        });

                        newItem.innerHTML = `
                            <div class="notif-item">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                    <strong>Atualização Disponível</strong>
                                    <small>agora</small>
                                </div>
                                <small>A versão v${currentUpdate.latest_version} está disponível. Clique para atualizar.</small>
                            </div>
                        `;

                        // Inserir no topo (seção sistema)
                        notifList.prepend(newItem);

                        // Atualizar badge
                        const badgeCountEl = document.querySelector('.notification-badge');
                        if (badgeCountEl) {
                            badgeCountEl.innerText = parseInt(badgeCountEl.innerText) + 1;
                        } else {
                            const wrapper = document.querySelector('.notification-wrapper button');
                            const newBadge = document.createElement('span');
                            newBadge.className = 'notification-badge';
                            newBadge.innerText = '1';
                            wrapper.appendChild(newBadge);
                        }
                    }
                } catch (e) { console.error('Erro ao salvar notificação', e); }
            }

            localStorage.setItem('ignored_version', version);
            document.getElementById('update-modal').classList.remove('show');
            showToast('Lembrete salvo nas notificações.', 'info');
        }

        let updateProgressValue = 8;
        let updateProgressPulse = null;
        let updateProgressPoll = null;

        function setUpdateProgress(value, message) {
            updateProgressValue = Math.max(0, Math.min(100, value));
            const bar = document.getElementById('update-progress-bar');
            const pct = document.getElementById('update-progress-percent');
            const log = document.getElementById('update-progress-log');
            if (bar) bar.style.width = `${updateProgressValue}%`;
            if (pct) pct.innerText = `${Math.round(updateProgressValue)}%`;
            if (message && log) log.innerText = message;
        }

        function openUpdateProgressModal(initialMessage = 'Iniciando atualização...') {
            const modal = document.getElementById('update-progress-modal');
            setUpdateProgress(8, initialMessage);
            if (modal) modal.classList.add('show');

            if (updateProgressPulse) clearInterval(updateProgressPulse);
            updateProgressPulse = setInterval(() => {
                // Progresso visual até 95% enquanto aguardamos confirmação final.
                if (updateProgressValue < 95) {
                    setUpdateProgress(updateProgressValue + 2);
                }
            }, 1800);
        }

        function closeUpdateProgressModal() {
            const modal = document.getElementById('update-progress-modal');
            if (modal) modal.classList.remove('show');
            if (updateProgressPulse) clearInterval(updateProgressPulse);
            if (updateProgressPoll) clearInterval(updateProgressPoll);
            updateProgressPulse = null;
            updateProgressPoll = null;
        }

        function startUpdatePolling() {
            if (updateProgressPoll) clearInterval(updateProgressPoll);

            const check = async () => {
                try {
                    const res = await fetch('/api/system/update/status', { cache: 'no-store' });
                    if (!res.ok) return;
                    const data = await res.json();

                    if (data.last_error && !data.in_progress) {
                        setUpdateProgress(updateProgressValue, `Falha: ${data.last_error}`);
                        showToast('A atualização falhou. Verifique os logs.', 'error');
                        if (updateProgressPulse) clearInterval(updateProgressPulse);
                        return;
                    }

                    if (data.in_progress || data.maintenance) {
                        setUpdateProgress(updateProgressValue, 'Aplicando atualização no ambiente HMG...');
                        return;
                    }

                    // Finalizou com sucesso
                    setUpdateProgress(100, 'Atualização concluída! Redirecionando para o Dashboard...');
                    if (updateProgressPulse) clearInterval(updateProgressPulse);
                    if (updateProgressPoll) clearInterval(updateProgressPoll);
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1200);
                } catch (e) {
                    // Durante restart é esperado ter falha intermitente de conexão.
                    setUpdateProgress(updateProgressValue, 'Reconectando ao servidor...');
                }
            };

            check();
            updateProgressPoll = setInterval(check, 2500);
        }

        async function requestUpdate(event) {
            if (!confirm('O sistema entrará em modo manutenção e será reiniciado. Deseja continuar?')) return;

            const btn = event ? event.target.closest('button') : document.querySelector('#update-modal .btn-primary');
            const originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="status-dot warning" style="display:inline-block; vertical-align:middle; margin-right:8px;"></span> Atualizando...';
            document.getElementById('update-modal').classList.remove('show');
            openUpdateProgressModal('Solicitação enviada. Entrando em modo manutenção...');

            try {
                const res = await fetch('/api/system/update/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const result = await res.json();

                if (result.status === 'success' || result.status === 'pending') {
                    setUpdateProgress(18, 'Atualização em andamento. Aguarde...');
                    startUpdatePolling();
                } else {
                    closeUpdateProgressModal();
                    showToast('Erro na atualização: ' + (result.error || result.message), 'error');
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                }
            } catch (e) {
                // Em restart do serviço a conexão pode cair. Continuamos monitorando status.
                setUpdateProgress(18, 'Servidor reiniciando... monitorando progresso.');
                startUpdatePolling();
                showToast('Atualização iniciada. Aguarde a finalização automática.', 'info');
            }
        }

        function handleSystemNotif(id, tipo, payload) {
            if (tipo === 'UPDATE_AVAILABLE') {
                // Se recebemos payload (item real-time ou do DB), usamos ele
                if (payload) {
                    localStorage.removeItem('ignored_version');
                    document.getElementById('new-version-tag').innerText = 'v' + (payload.version || payload.latest_version);
                    document.getElementById('update-modal').classList.add('show');
                    window.latestUpdate = payload;
                } else {
                    // Fallback para comportamento de force-check
                    localStorage.removeItem('ignored_version');
                    checkUpdate();
                }
            }
            // Marcar como lida
            fetch(`/api/notifications/${id}/read`, { method: 'POST' })
                .then(() => {
                    const item = document.getElementById(`notif-item-${id}`) || document.querySelector(`li[onclick*="'${id}'"]`);
                    if (item) {
                        item.remove();
                        // Decrementar badge
                        const badge = document.querySelector('.notification-badge');
                        if (badge) {
                            const newCount = parseInt(badge.innerText) - 1;
                            if (newCount > 0) badge.innerText = newCount;
                            else badge.remove();
                        }
                    }
                });
        }

        // Check no load
        document.addEventListener('DOMContentLoaded', () => {
            checkUpdate();
        });
    