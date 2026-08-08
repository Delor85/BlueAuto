(() => {
    'use strict';

    const TERMINAL = new Set(['SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED']);
    const stateLabels = {
        PENDING: 'En attente', LEASED: 'Réservée au Robot', DIALING: 'Composition USSD',
        AWAITING_PIN: 'Vérification du pop-up', PIN_SUBMITTED: 'PIN validé',
        AWAITING_RESULT: 'Confirmation Camtel', SUCCEEDED: 'Réussie', FAILED: 'Échec',
        UNKNOWN: 'À vérifier', BLOCKED: 'Robot bloqué — PIN'
    };
    let configuration = {};
    let commands = [];

    const $ = id => document.getElementById(id);
    const bridgeAvailable = () => typeof window.AndroidBridge !== 'undefined';

    window.BlueMagicNative = {
        onCommandCreated(data) {
            setBusy(false);
            if (data.error) return showToast(data.message || 'Création impossible.');
            const command = data.command || {};
            if (!command.public_id) return showToast('Réponse de commande incomplète.');
            upsertCommand(command);
            showToast(data.duplicate ? 'Cette demande existait déjà.' : 'Commande sécurisée créée.');
            renderCommands();
        },
        onCommandStatus(data) {
            if (data.error) return;
            if (data.command) {
                upsertCommand(data.command);
                renderCommands();
            }
        }
    };

    function initialize() {
        if (!bridgeAvailable()) {
            $('nativeBadge').textContent = 'NAVIGATEUR SEUL';
            $('browserNotice').classList.remove('hidden');
            document.querySelectorAll('button[data-action]').forEach(button => button.disabled = true);
            renderCommands();
            return;
        }
        try {
            configuration = JSON.parse(window.AndroidBridge.getConfiguration() || '{}');
        } catch (_) {
            configuration = {};
        }
        commands = loadCommands();
        $('nativeBadge').textContent = 'PONT NATIF ACTIF';
        $('nativeBadge').className = 'badge badge-ok';
        $('browserNotice').classList.add('hidden');
        $('nodeCode').textContent = configuration.node_code || 'Nœud non configuré';
        const simSlot = configuration.sim_slot == null ? 0 : configuration.sim_slot;
        $('nodeMeta').textContent = `${configuration.role || '—'} • ${configuration.mode || '—'} • SIM ${simSlot + 1}`;
        $('robotState').textContent = configuration.robot_enabled ? 'ROBOT ACTIF' : 'ROBOT ARRÊTÉ';
        if (configuration.pin_blocked) {
            $('fatalNotice').textContent = 'ARRÊT D’URGENCE : le réseau a signalé un PIN incorrect. Corrigez le PIN dans la zone native avant toute reprise.';
            $('fatalNotice').classList.remove('hidden');
        }
        if (['DSM', 'POS'].includes(configuration.role)) $('requestSupplyCard').classList.remove('hidden');
        if (['DAE', 'DSM'].includes(configuration.role)) $('supplyChildCard').classList.remove('hidden');
        if (configuration.role === 'POS') $('retailCard').classList.remove('hidden');
        bindActions();
        renderCommands();
        refreshCommands();
        window.setInterval(() => {
            if (document.visibilityState === 'visible') refreshCommands();
        }, 15000);
    }

    function bindActions() {
        document.querySelectorAll('button[data-action]').forEach(button => {
            button.addEventListener('click', () => execute(button.dataset.action));
        });
        $('refreshCommands').addEventListener('click', refreshCommands);
    }

    function execute(action) {
        if (!bridgeAvailable() || configuration.pin_blocked) return;
        let requestType = '', targetNode = '', targetPhone = '', amount = '';
        if (action === 'request-supply') {
            requestType = 'REQUEST_SUPPLY';
            amount = $('requestSupplyAmount').value.trim();
        } else if (action === 'supply-child') {
            requestType = 'SUPPLY_CHILD';
            targetNode = $('childNode').value.trim().toUpperCase();
            amount = $('childAmount').value.trim();
        } else if (action === 'retail-sale') {
            requestType = 'RETAIL_SALE';
            targetPhone = $('retailPhone').value.replace(/\D/g, '');
            amount = $('retailAmount').value.trim();
        } else if (action === 'test-number') {
            requestType = 'TEST_NUMBER';
        }
        if (requestType !== 'TEST_NUMBER' && !/^[1-9]\d{0,8}$/.test(amount)) {
            return showToast('Saisissez un montant entier valide.');
        }
        if (requestType === 'SUPPLY_CHILD' && !targetNode) return showToast('Saisissez le code nœud enfant.');
        if (requestType === 'RETAIL_SALE' && !/^\d{9}$/.test(targetPhone)) return showToast('Le numéro client doit avoir 9 chiffres.');

        setBusy(true);
        window.AndroidBridge.createCommand(requestType, targetNode, targetPhone, amount, requestId());
    }

    function refreshCommands() {
        if (!bridgeAvailable()) return;
        commands.filter(command => !TERMINAL.has(command.state)).forEach(command => {
            window.AndroidBridge.getCommandStatus(command.public_id);
        });
    }

    function upsertCommand(command) {
        const index = commands.findIndex(item => item.public_id === command.public_id);
        if (index >= 0) commands[index] = {...commands[index], ...command};
        else commands.unshift(command);
        commands = commands.slice(0, 20);
        localStorage.setItem(commandStorageKey(), JSON.stringify(commands));
    }

    function loadCommands() {
        try {
            const value = JSON.parse(localStorage.getItem(commandStorageKey()) || '[]');
            return Array.isArray(value) ? value : [];
        } catch (_) {
            return [];
        }
    }

    function commandStorageKey() {
        return `blue_magic_recent_commands_v3_${configuration.profile_id || configuration.node_code || 'default'}`;
    }

    function renderCommands() {
        if (!commands.length) {
            $('commandList').innerHTML = '<p class="muted">Aucune commande sur ce téléphone.</p>';
            return;
        }
        $('commandList').innerHTML = commands.map(command => {
            const state = escapeHtml(command.state || 'PENDING');
            const detail = escapeHtml(command.result_message || command.operation || 'Commande sécurisée');
            return `<article class="command-item"><div class="command-item-top">`
                + `<span class="command-id">${escapeHtml(command.public_id || '')}</span>`
                + `<span class="command-state state-${state}">${escapeHtml(stateLabels[command.state] || command.state || '—')}</span>`
                + `</div><div class="command-detail">${detail}</div></article>`;
        }).join('');
    }

    function requestId() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') return window.crypto.randomUUID();
        return `req_${Date.now()}_${Math.random().toString(36).slice(2, 14)}`;
    }

    function setBusy(value) {
        document.querySelectorAll('button[data-action]').forEach(button => button.disabled = value);
    }

    function showToast(message) {
        const toast = $('toast');
        toast.textContent = message;
        toast.classList.remove('hidden');
        window.setTimeout(() => toast.classList.add('hidden'), 3500);
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>'"]/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[character]));
    }

    document.addEventListener('DOMContentLoaded', initialize);
    if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js'));
})();
