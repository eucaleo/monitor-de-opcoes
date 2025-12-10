// assets/clientside.js

if (!window.dash_clientside) {
  window.dash_clientside = {};
}

console.log('Tentativa de carregar Clientside.js');
console.log('dash_clientside encontrado:', window.dash_clientside);
console.log('Clientside.js loaded');

function NO_UPDATE_N(n) {
  const nu = window.dash_clientside.no_update;
  return Array.from({ length: n }, () => nu);
}

let hasFocusedTicker = false;

window.dash_clientside.clientside = {
  // Dá foco no campo TICKER ao abrir o modal Nova
  focusTicker: function (is_open) {
    try {
      if (is_open) {
        if (!hasFocusedTicker) {
          let attempts = 0;
          const iv = setInterval(() => {
            const el = document.getElementById('nova-ticker');
            if (el) {
              el.focus();
              hasFocusedTicker = true;
              clearInterval(iv);
            } else if (attempts > 20) {
              clearInterval(iv);
            }
            attempts++;
          }, 60);
        }
      } else {
        hasFocusedTicker = false;
      }
    } catch (e) {
      console.error('Erro em focusTicker:', e);
    }
    return Date.now(); // pulso para Store
  },

  // Extrai OPERAÇÃO e DATA EXERC a partir do TICKER
  // 2 outputs: nova-operacao.value, nova-data-exerc.value
  extractInfo: function (is_open, ticker) {
    if (!is_open) return NO_UPDATE_N(2);

    if (!ticker || String(ticker).trim().length < 6) {
      return ["", ""]; // limpa visualmente
    }

    try {
      const t = String(ticker).toUpperCase().trim();
      const serie = t.charAt(4);
      let sufixo = t.slice(5);

      // Semanais W1/W2/W4/W5
      let semana = null, isWeekly = false;
      if (sufixo.includes("W")) {
        const parts = sufixo.split("W");
        sufixo = parts[0];
        const w = parseInt(parts[1], 10);
        if ([1, 2, 4, 5].includes(w)) { semana = w; isWeekly = true; }
        else { return ["", ""]; }
      }

      // A-L (1..12), M-X (1..12)
      const mesMap = {
        A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7, H: 8, I: 9, J: 10, K: 11, L: 12,
        M: 1, N: 2, O: 3, P: 4, Q: 5, R: 6, S: 7, T: 8, U: 9, V: 10, W: 11, X: 12
      };
      const mes = mesMap[serie];
      if (!mes) return ["", ""];

      // OPERAÇÃO: Call ou Put
      const operacao = "MNOPQRSTUVWX".includes(serie) ? "Put" : "Call";

      // Ano: até 12 meses à frente
      const hoje = new Date();
      const mesAtual = hoje.getMonth() + 1;
      let ano = hoje.getFullYear();
      if (mes < mesAtual) ano += 1;

      function terceiraSexta(y, m) {
        const d = new Date(y, m - 1, 1);
        while (d.getDay() !== 5) d.setDate(d.getDate() + 1);
        d.setDate(d.getDate() + 14);
        return d;
      }
      function sextaDaSemana(y, m, w) {
        const d = new Date(y, m - 1, 1);
        while (d.getDay() !== 5) d.setDate(d.getDate() + 1);
        d.setDate(d.getDate() + (w - 1) * 7);
        return d;
      }

      let dataExerc = isWeekly ? sextaDaSemana(ano, mes, semana) : terceiraSexta(ano, mes);
      if (dataExerc < hoje && mes === mesAtual) dataExerc.setFullYear(dataExerc.getFullYear() + 1);

      const dataExercStr = dataExerc.toLocaleDateString("pt-BR");
      return [operacao, dataExercStr];
    } catch (e) {
      console.error("extractInfo error:", e);
      return NO_UPDATE_N(2);
    }
  }
};

// -------------------------
// Dark Mode via Bootstrap 5.3 (data-bs-theme)
// -------------------------
(function () {
  const STORAGE_KEY = 'theme-preference';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    console.log('[Theme] Aplicado:', theme);
  }

  function setSwitchChecked(checked) {
    const sw = document.getElementById('theme-switch');
    if (sw && sw.checked !== checked) {
      sw.checked = checked;
    }
  }

  function initThemeFromStorage() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const theme = saved === 'dark' ? 'dark' : 'light';
      applyTheme(theme);
      setSwitchChecked(theme === 'dark');
    } catch (e) {
      applyTheme('light');
      setSwitchChecked(false);
    }
  }

  function attachSwitchHandler() {
    const sw = document.getElementById('theme-switch');
    if (!sw) return false;
    sw.addEventListener('change', function () {
      const theme = sw.checked ? 'dark' : 'light';
      applyTheme(theme);
      try { localStorage.setItem(STORAGE_KEY, theme); } catch (_) {}
    });
    return true;
  }

  function waitForSwitchAndBind() {
    if (attachSwitchHandler()) return;
    const iv = setInterval(() => { if (attachSwitchHandler()) clearInterval(iv); }, 300);
    setTimeout(() => clearInterval(iv), 10000);
  }

  document.addEventListener('DOMContentLoaded', function () {
    console.log('Clientside.js (theme) init');
    initThemeFromStorage();
    waitForSwitchAndBind();
  });
})();
