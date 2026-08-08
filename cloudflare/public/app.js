(function () {
    'use strict';

    var TERMINAL = {SUCCEEDED: true, FAILED: true, UNKNOWN: true, BLOCKED: true};
    var stateLabels = {
        PENDING: 'En attente', LEASED: 'Réservée au Robot', DIALING: 'Composition USSD',
        AWAITING_PIN: 'Vérification du pop-up', PIN_SUBMITTED: 'PIN validé',
        AWAITING_RESULT: 'Confirmation Camtel', SUCCEEDED: 'Réussie', FAILED: 'Échec',
        UNKNOWN: 'À vérifier', BLOCKED: 'Robot bloqué — PIN'
    };
    var configuration = {};
    var commands = [];

    function byId(id) {
        return document.getElementById(id);
    }

    function bridgeAvailable() {
        return typeof window.AndroidBridge !== 'undefined';
    }

    function each(selector, callback) {
        var values = document.querySelectorAll(selector);
        for (var index = 0; index < values.length; index += 1) callback(values[index], index);
    }

    window.BlueMagicNative = {
        onCommandCreated: function (data) {
            setBusy(false);
            if (data.error) return showToast(data.message || 'Création impossible.');
            var command = data.command || {};
            if (!command.public_id) return showToast('Réponse de commande incomplète.');
            upsertCommand(command);
            showToast(data.duplicate ? 'Cette demande existait déjà.' : 'Commande sécurisée créée.');
            renderCommands();
        },
        onCommandStatus: function (data) {
            if (data.error) return;
            if (data.command) {
                upsertCommand(data.command);
                renderCommands();
            }
        }
    };

    function initialize() {
        if (!bridgeAvailable()) {
            byId('nativeBadge').textContent = 'NAVIGATEUR SEUL';
            byId('browserNotice').classList.remove('hidden');
            each('button[data-action]', function (button) { button.disabled = true; });
            renderCommands();
            return;
        }
        try {
            configuration = JSON.parse(window.AndroidBridge.getConfiguration() || '{}');
        } catch (ignored) {
            configuration = {};
        }
        commands = loadCommands();
        byId('nativeBadge').textContent = 'PONT NATIF ACTIF';
        byId('nativeBadge').className = 'badge badge-ok';
        byId('browserNotice').classList.add('hidden');
        byId('nodeCode').textContent = configuration.node_code || 'Nœud non configuré';
        var simSlot = configuration.sim_slot == null ? 0 : configuration.sim_slot;
        byId('nodeMeta').textContent = (configuration.role || '—') + ' • '
            + (configuration.mode || '—') + ' • SIM ' + (simSlot + 1);
        byId('robotState').textContent = configuration.robot_enabled ? 'ROBOT ACTIF' : 'ROBOT ARRÊTÉ';
        if (configuration.pin_blocked) {
            byId('fatalNotice').textContent = 'ARRÊT D’URGENCE : le réseau a signalé un PIN incorrect. Corrigez le PIN dans la zone native avant toute reprise.';
            byId('fatalNotice').classList.remove('hidden');
        }
        if (configuration.role === 'DSM' || configuration.role === 'POS') {
            byId('requestSupplyCard').classList.remove('hidden');
        }
        if (configuration.role === 'DAE' || configuration.role === 'DSM') {
            byId('supplyChildCard').classList.remove('hidden');
        }
        if (configuration.role === 'POS') byId('retailCard').classList.remove('hidden');
        bindActions();
        renderCommands();
        refreshCommands();
        window.setInterval(function () {
            if (document.visibilityState === 'visible') refreshCommands();
        }, 15000);
    }

    function bindActions() {
        each('button[data-action]', function (button) {
            button.addEventListener('click', function () {
                execute(button.getAttribute('data-action'));
            });
        });
        byId('refreshCommands').addEventListener('click', refreshCommands);
    }

    function execute(action) {
        if (!bridgeAvailable() || configuration.pin_blocked) return;
        var requestType = '';
        var targetNode = '';
        var targetPhone = '';
        var amount = '';
        if (action === 'request-supply') {
            requestType = 'REQUEST_SUPPLY';
            amount = byId('requestSupplyAmount').value.trim();
        } else if (action === 'supply-child') {
            requestType = 'SUPPLY_CHILD';
            targetNode = byId('childNode').value.trim().toUpperCase();
            amount = byId('childAmount').value.trim();
        } else if (action === 'retail-sale') {
            requestType = 'RETAIL_SALE';
            targetPhone = byId('retailPhone').value.replace(/\D/g, '');
            amount = byId('retailAmount').value.trim();
        } else if (action === 'test-number') {
            requestType = 'TEST_NUMBER';
        }
        if (requestType !== 'TEST_NUMBER' && !/^[1-9]\d{0,8}$/.test(amount)) {
            return showToast('Saisissez un montant entier valide.');
        }
        if (requestType === 'SUPPLY_CHILD' && !targetNode) {
            return showToast('Saisissez le code nœud enfant.');
        }
        if (requestType === 'RETAIL_SALE' && !/^\d{9}$/.test(targetPhone)) {
            return showToast('Le numéro client doit avoir 9 chiffres.');
        }
        setBusy(true);
        window.AndroidBridge.createCommand(requestType, targetNode, targetPhone, amount, requestId());
    }

    function refreshCommands() {
        if (!bridgeAvailable()) return;
        for (var index = 0; index < commands.length; index += 1) {
            if (!TERMINAL[commands[index].state]) {
                window.AndroidBridge.getCommandStatus(commands[index].public_id);
            }
        }
    }

    function upsertCommand(command) {
        var index = -1;
        for (var position = 0; position < commands.length; position += 1) {
            if (commands[position].public_id === command.public_id) {
                index = position;
                break;
            }
        }
        if (index >= 0) {
            for (var key in command) {
                if (Object.prototype.hasOwnProperty.call(command, key)) commands[index][key] = command[key];
            }
        } else {
            commands.unshift(command);
        }
        commands = commands.slice(0, 20);
        localStorage.setItem(commandStorageKey(), JSON.stringify(commands));
    }

    function loadCommands() {
        try {
            var value = JSON.parse(localStorage.getItem(commandStorageKey()) || '[]');
            return Object.prototype.toString.call(value) === '[object Array]' ? value : [];
        } catch (ignored) {
            return [];
        }
    }

    function commandStorageKey() {
        return 'blue_magic_recent_commands_v4_'
            + (configuration.profile_id || configuration.node_code || 'default');
    }

    function renderCommands() {
        if (!commands.length) {
            byId('commandList').innerHTML = '<p class="muted">Aucune commande sur ce téléphone.</p>';
            return;
        }
        var html = '';
        for (var index = 0; index < commands.length; index += 1) {
            var command = commands[index];
            var state = escapeHtml(command.state || 'PENDING');
            var detail = escapeHtml(command.result_message || command.operation || 'Commande sécurisée');
            var timestamp = command.updated_at || command.created_at || '';
            html += '<article class="command-item"><div class="command-item-top">'
                + '<span class="command-id">' + escapeHtml(command.public_id || '') + '</span>'
                + '<span class="command-state state-' + state + '">'
                + escapeHtml(stateLabels[command.state] || command.state || '—') + '</span>'
                + '</div><div class="command-detail">' + detail + '</div>'
                + (timestamp ? '<div class="command-time">Horodatage : '
                    + escapeHtml(formatTimestamp(timestamp)) + '</div>' : '')
                + '</article>';
        }
        byId('commandList').innerHTML = html;
    }

    function formatTimestamp(value) {
        var date = new Date(value);
        if (isNaN(date.getTime())) return String(value);
        return two(date.getDate()) + '/' + two(date.getMonth() + 1) + '/' + date.getFullYear()
            + ' à ' + two(date.getHours()) + ':' + two(date.getMinutes()) + ':' + two(date.getSeconds());
    }

    function two(value) {
        return value < 10 ? '0' + value : String(value);
    }

    function requestId() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') return window.crypto.randomUUID();
        return 'req_' + Date.now() + '_' + Math.random().toString(36).slice(2, 14);
    }

    function setBusy(value) {
        each('button[data-action]', function (button) { button.disabled = value; });
    }

    function showToast(message) {
        var toast = byId('toast');
        toast.textContent = message;
        toast.classList.remove('hidden');
        window.setTimeout(function () { toast.classList.add('hidden'); }, 3500);
    }

    function escapeHtml(value) {
        var entities = {'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'};
        return String(value).replace(/[&<>'"]/g, function (character) { return entities[character]; });
    }

    document.addEventListener('DOMContentLoaded', initialize);
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () { navigator.serviceWorker.register('sw.js'); });
    }
}());
