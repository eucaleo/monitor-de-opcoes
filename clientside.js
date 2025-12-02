if (!window.dash_clientside) {
    window.dash_clientside = {};
}
console.log("Tentativa de carregar Clientside.js");
if (typeof window.dash_clientside === 'undefined') {
    console.warn("dash_clientside não encontrado, criando fallback");
    window.dash_clientside = { no_update: {} };
} else {
    console.log("dash_clientside encontrado:", window.dash_clientside);
}
console.log("Clientside.js loaded");

window.dash_clientside.clientside = {
    focusTicker: function(is_open) {
        console.log("focusTicker iniciado: is_open=" + is_open);
        if (is_open && !window.clientside.hasFocusedTicker) {
            let attempts = 0;
            const interval = setInterval(() => {
                const element = document.getElementById('nova-ticker');
                if (element) {
                    element.focus();
                    console.log("Foco em TICKER ativado");
                    window.clientside.hasFocusedTicker = true;
                    clearInterval(interval);
                } else if (attempts > 5) {
                    console.error("Elemento nova-ticker não encontrado após 5 tentativas");
                    clearInterval(interval);
                }
                attempts++;
            }, 50);
        }
        console.log("focusTicker finalizado");
        return window.dash_clientside.no_update;
    },

    force_selection: function(active_cell, selected_rows) {
        console.log('force_selection iniciado:', active_cell, selected_rows);
        if (active_cell && active_cell.row !== undefined) {
            console.log('Seleção forçada via active_cell:', active_cell);
            return active_cell;
        }
        if (selected_rows && selected_rows.length > 0) {
            console.log('Seleção forçada via selected_rows:', selected_rows[0]);
            return { row: selected_rows[0], column: 0 }; // Índice 0 para a primeira coluna (TICKER)
        }
        console.log('Nenhuma seleção detectada');
        return null;
    },

    extractInfo: function(is_open, ticker) {
        console.log("extractInfo iniciado: is_open=" + is_open + ", ticker=" + ticker);
        if (!is_open || !ticker || ticker.length < 6) {
            console.log("Condições não atendidas para extração");
            return window.dash_clientside.no_update;
        }
        try {
            const empresa = ticker.slice(0, 4).toUpperCase();
            const serie = ticker.charAt(4).toUpperCase();
            let numero = ticker.slice(5);
            let semana = 3;
            let isWeekly = false;
            if (numero.includes('W')) {
                const parts = numero.split('W');
                numero = parts[0];
                semana = parseInt(parts[1], 10);
                isWeekly = true;
                if (![1, 2, 4, 5].includes(semana)) {
                    console.warn("Semana inválida (somente W1, W2, W4, W5): " + semana);
                    return window.dash_clientside.no_update;
                }
            }
            const mesMap = {
                'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8, 'I': 9, 'J': 10, 'K': 11, 'L': 12,
                'M': 1, 'N': 2, 'O': 3, 'P': 4, 'Q': 5, 'R': 6, 'S': 7, 'T': 8, 'U': 9, 'V': 10, 'X': 11, 'W': 12
            };
            const mes = mesMap[serie];
            if (!mes) {
                console.error("Série inválida: " + serie);
                return window.dash_clientside.no_update;
            }
            const operacao = 'MNOPQRSTUVWX'.includes(serie) ? 'Put' : 'Call';
            const ano = new Date().getFullYear();
            const primeiroDiaMes = new Date(ano, mes - 1, 1);
            let dataExerc = new Date(primeiroDiaMes.getTime() + (semana - 1) * 7 * 24 * 60 * 60 * 1000);
            if (isWeekly) {
                while (dataExerc.getDay() !== 5) {
                    dataExerc = new Date(dataExerc.getTime() + 24 * 60 * 60 * 1000);
                }
            }
            const dataExercStr = dataExerc.toLocaleDateString('pt-BR');
            const strike = parseFloat(numero) > 0 ? parseFloat(numero) : null;
            console.log(`Extração: operacao=${operacao}, data_exerc=${dataExercStr}, strike=${strike}`);
            return [operacao, dataExercStr, strike || ''];
        } catch (e) {
            console.error(`Erro na extração de ticker ${ticker}: ${e}`);
            return ['', '', ''];
        }
    }
};