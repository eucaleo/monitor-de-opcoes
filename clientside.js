// Clientside.js

// Namespace do Dash (seguro)
if (!window.dash_clientside) {
  window.dash_clientside = {};
}
if (typeof window.dash_clientside.no_update === 'undefined') {
  window.dash_clientside.no_update = {};
}

console.log('Tentativa de carregar Clientside.js');
console.log('dash_clientside encontrado:', window.dash_clientside);
console.log('Clientside.js loaded');

// Estado interno seguro
let hasFocusedTicker = false;

// Funções expostas a clientside_callback
window.dash_clientside.clientside = {
  // Foca o campo TICKER quando o modal Nova abre
  focusTicker: function (is_open) {
    try {
      if (is_open && !hasFocusedTicker) {
        let attempts = 0;
        const iv = setInterval(() => {
          const el = document.getElementById('nova-ticker');
          if (el) {
            el.focus();
            hasFocusedTicker = true;
            clearInterval(iv);
          } else if (attempts > 10) {
            clearInterval(iv);
          }
          attempts++;
        }, 60);
      }
    } catch (e) {
      console.error('Erro em focusTicker:', e);
    }
    return window.dash_clientside.no_update;
  },

  // Extrai operação, data de exercício e strike a partir do TICKER
  extractInfo: function (is_open, ticker) {
    if (!is_open || !ticker || ticker.length < 6) {
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
          return window.dash_clientside.no_update;
        }
      }

      const mesMap = {
        A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7, H: 8, I: 9, J: 10, K: 11, L: 12,
        M: 1, N: 2, O: 3, P: 4, Q: 5, R: 6, S: 7, T: 8, U: 9, V: 10, W: 11, X: 12
      };
      const mes = mesMap[serie];
      if (!mes) return window.dash_clientside.no_update;

      const operacao = 'MNOPQRSTUVWX'.includes(serie) ? 'Put' : 'Call';
      const strike = parseFloat(numero) > 0 ? parseFloat(numero) : '';

      // Data de exercício (heurística simples)
      const ano = new Date().getFullYear();
      const primeiroDiaMes = new Date(ano, mes - 1, 1);
      let dataExerc = new Date(primeiroDiaMes.getTime() + (semana - 1) * 7 * 24 * 60 * 60 * 1000);
      if (isWeekly) {
        while (dataExerc.getDay() !== 5) {
          dataExerc = new Date(dataExerc.getTime() + 24 * 60 * 60 * 1000);
        }
      }
      const dataExercStr = dataExerc.toLocaleDateString('pt-BR');

      return [operacao, dataExercStr, strike];
    } catch (e) {
      console.error('extractInfo error:', e);
      return ['', '', ''];
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
