# app_callbacks.py
from dash import Input, Output, State, no_update, ctx, dcc
from datetime import datetime
import pandas as pd

from database import (
    init_database,
    add_operation,
    update_operation,
    close_operation,
    get_transactions,
    get_encerradas,
)
from calculations import (
    cards_aberturas,
    cards_gp,
    card_fluxo,
    card_posicao_aberta,
)
from validations import (
    validate_ticker,
    validate_date,
    validate_numeric_positive,
)


def _parse_ddmmyyyy(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except Exception:
        return None


def register_callbacks(app):
    # Inicialização defensiva do banco
    init_database()

    # Tabela: dados + filtros
    @app.callback(
        Output("tabela-operacoes", "data"),
        Input("table-refresh-seq", "data"),
        Input("periodo-date-range", "start_date"),
        Input("periodo-date-range", "end_date"),
        Input("busca-ticker", "value"),
        prevent_initial_call=False,
    )
    def load_table(seq, start_iso, end_iso, busca):
        df = get_transactions()
        if df is None or df.empty:
            return []

        # Filtro por período (DATA OP)
        if start_iso or end_iso:
            start_dt = datetime.fromisoformat(start_iso) if start_iso else None
            end_dt = datetime.fromisoformat(end_iso) if end_iso else None
            dcol = df["DATA OP"].apply(_parse_ddmmyyyy)
            mask = pd.Series(True, index=df.index)
            if start_dt:
                mask &= dcol >= start_dt
            if end_dt:
                mask &= dcol <= end_dt
            df = df[mask]

        # Filtro por busca (ticker)
        if busca and isinstance(busca, str):
            b = busca.strip().upper()
            if b:
                df = df[df["TICKER"].astype(str).str.upper().str.contains(b, na=False)]

        return df.to_dict("records")

    # Cards: Aberturas (Compra/Venda x Call/Put)
    @app.callback(
        Output("compra-call-value", "children"),
        Output("venda-call-value", "children"),
        Output("compra-put-value", "children"),
        Output("venda-put-value", "children"),
        Input("periodo-date-range", "start_date"),
        Input("periodo-date-range", "end_date"),
        Input("table-refresh-seq", "data"),
        prevent_initial_call=False,
    )
    def cards_aberturas_cb(start_iso, end_iso, _seq):
        ccall, vcall, cput, vput = cards_aberturas(start_iso, end_iso)
        return ccall, vcall, cput, vput

    # Cards: G/P (Estruturas e Simples)
    @app.callback(
        Output("g_p-estrutura-value", "children"),
        Output("g_p-simples-value", "children"),
        Input("periodo-date-range", "start_date"),
        Input("periodo-date-range", "end_date"),
        Input("table-refresh-seq", "data"),
        prevent_initial_call=False,
    )
    def cards_gp_cb(start_iso, end_iso, _seq):
        gp_estr, gp_simp = cards_gp(start_iso, end_iso)
        return gp_estr, gp_simp

    # Card: Fluxo (período)
    @app.callback(
        Output("fluxo-periodo-value", "children"),
        Input("periodo-date-range", "start_date"),
        Input("periodo-date-range", "end_date"),
        Input("table-refresh-seq", "data"),
        prevent_initial_call=False,
    )
    def card_fluxo_cb(start_iso, end_iso, _seq):
        return card_fluxo(start_iso, end_iso)

    # Card: Posição Aberta (agora)
    @app.callback(
        Output("posicao-aberta-value", "children"),
        Input("table-refresh-seq", "data"),
        prevent_initial_call=False,
    )
    def card_posicao_cb(_seq):
        return card_posicao_aberta()

    # Store: ID da linha selecionada
    @app.callback(
        Output("selected-row-id", "data"),
        Input("tabela-operacoes", "active_cell"),
        Input("tabela-operacoes", "selected_rows"),
        State("tabela-operacoes", "data"),
        prevent_initial_call=True,
    )
    def set_selected_row(active_cell, selected_rows, rows):
        if not rows:
            return no_update
        if active_cell and isinstance(active_cell, dict) and active_cell.get("row") is not None:
            idx = active_cell["row"]
        elif selected_rows and len(selected_rows) > 0:
            idx = selected_rows[0]
        else:
            return no_update
        try:
            row = rows[idx]
            return row.get("id", no_update)
        except Exception:
            return no_update

    # Nova: abrir/fechar
    @app.callback(
        Output("modal-nova-operacao", "is_open", allow_duplicate=True),
        Input("nova-operacao-btn", "n_clicks"),
        Input("cancelar-nova-btn", "n_clicks"),
        Input("voltar-nova-btn", "n_clicks"),
        State("modal-nova-operacao", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_modal_nova(n_open, n_cancel, n_back, is_open):
        trig = ctx.triggered_id
        if trig == "nova-operacao-btn":
            return True
        if trig in ("cancelar-nova-btn", "voltar-nova-btn"):
            return False
        return is_open

    # Nova: resetar campos ao abrir (OPERAÇÃO/DATA EXERC ficam para o client-side)
    @app.callback(
        Output("nova-ticker", "value"),
        Output("nova-direcao", "value"),
        Output("nova-quantidade", "value"),
        Output("nova-valor-opcao", "value"),
        Output("nova-data-op", "value"),
        Output("nova-estrutura", "value"),
        Output("nova-rolagem", "value"),
        Output("nova-strike", "value"),
        Input("modal-nova-operacao", "is_open"),
        prevent_initial_call=True,
    )
    def reset_nova_fields(is_open):
        if not is_open:
            return (no_update,) * 8
        today = datetime.now().strftime("%d/%m/%Y")
        return ("", None, None, None, today, "", "", None)

    # Nova: confirmar inclusão
    @app.callback(
        Output("modal-nova-mensagem", "children"),
        Output("modal-nova-operacao", "is_open", allow_duplicate=True),
        Output("table-refresh-seq", "data", allow_duplicate=True),
        Input("confirmar-nova-btn", "n_clicks"),
        State("nova-ticker", "value"),
        State("nova-operacao", "value"),
        State("nova-direcao", "value"),
        State("nova-strike", "value"),
        State("nova-quantidade", "value"),
        State("nova-valor-opcao", "value"),
        State("nova-data-op", "value"),
        State("nova-data-exerc", "value"),
        State("nova-estrutura", "value"),
        State("nova-rolagem", "value"),
        State("table-refresh-seq", "data"),
        prevent_initial_call=True,
    )
    def confirmar_nova(n_clicks, ticker, operacao, direcao, strike, qtd, val_opcao,
                       data_op, data_exerc, estrutura, rolagem, seq):
        if not n_clicks:
            return no_update, no_update, no_update
        try:
            if not validate_ticker(ticker):
                return ("Ticker inválido.", True, no_update)
            if not operacao:
                return ("OPERAÇÃO não definida (preenchida automaticamente pelo ticker).", True, no_update)
            if not direcao:
                return ("Selecione a DIREÇÃO (Compra/Venda).", True, no_update)

            # Campos obrigatórios: quantidade e valor unitário
            if qtd is None or str(qtd).strip() == "" or not validate_numeric_positive(qtd, "quantidade"):
                return ("Quantidade inválida.", True, no_update)
            if val_opcao is None or str(val_opcao).strip() == "" or not validate_numeric_positive(val_opcao, "valor_opcao"):
                return ("Valor da opção inválido.", True, no_update)

            if not validate_date(data_exerc):
                return ("Data de exercício inválida (é preenchida automaticamente pela extração).", True, no_update)

            ticker = str(ticker).strip().upper()
            qtd_int = abs(int(float(qtd)))
            val_opc = abs(float(val_opcao))
            strike_val = float(strike) if strike not in (None, "") else None

            add_operation(
                ticker=ticker,
                operacao=operacao,
                direcao=direcao,
                strike=strike_val,
                quantidade=qtd_int,
                valor_opcao=val_opc,
                data_exerc=data_exerc,
                estrutura=estrutura or "",
                rolagem=rolagem or "",
                data_op=data_op if validate_date(data_op) else None
            )
            new_seq = int(seq or 0) + 1
            return ("Operação incluída com sucesso.", False, new_seq)
        except Exception as e:
            return (f"Erro ao incluir: {e}", True, no_update)

    # Alterar: abrir/fechar
    @app.callback(
        Output("modal-alterar-operacao", "is_open", allow_duplicate=True),
        Input("alterar-operacao-btn", "n_clicks"),
        Input("cancelar-alter-btn", "n_clicks"),
        State("modal-alterar-operacao", "is_open"),
        State("selected-row-id", "data"),
        prevent_initial_call=True,
    )
    def toggle_modal_alterar(n_open, n_cancel, is_open, row_id):
        trig = ctx.triggered_id
        if trig == "alterar-operacao-btn":
            return bool(row_id)
        if trig == "cancelar-alter-btn":
            return False
        return is_open

    # Alterar: preload
    @app.callback(
        Output("alterar-ticker", "children"),
        Output("alterar-operacao", "children"),
        Output("alterar-direcao", "children"),
        Output("alterar-quantidade", "value"),
        Output("alterar-valor-opcao", "children"),
        Output("alterar-data-op", "children"),
        Output("alterar-data-exerc", "children"),
        Output("alterar-estrutura", "value"),
        Output("alterar-rolagem", "value"),
        Input("modal-alterar-operacao", "is_open"),
        State("selected-row-id", "data"),
        State("tabela-operacoes", "data"),
        prevent_initial_call=True,
    )
    def preload_modal_alterar(is_open, row_id, rows):
        if not is_open or not row_id or not rows:
            return (no_update,) * 9
        row = next((r for r in rows if str(r.get("id")) == str(row_id)), None)
        if not row:
            return ("", "", "", None, "", "", "", "", "")
        def s(v): return "" if v is None else str(v)
        def qty(v):
            try: return abs(int(float(v)))
            except Exception: return None
        return (
            s(row.get("TICKER")),
            s(row.get("OPERAÇÃO")),
            s(row.get("DIREÇÃO")),
            qty(row.get("QUANTIDADE")),
            s(row.get("VALOR OPÇÃO")),
            s(row.get("DATA OP")),
            s(row.get("DATA EXERC")),
            row.get("ESTRUTURA") or "",
            row.get("ROLAGEM") or "",
        )

    # Alterar: confirmar
    @app.callback(
        Output("modal-alterar-mensagem", "children"),
        Output("modal-alterar-operacao", "is_open", allow_duplicate=True),
        Output("table-refresh-seq", "data", allow_duplicate=True),
        Input("confirmar-alter-btn", "n_clicks"),
        State("selected-row-id", "data"),
        State("alterar-quantidade", "value"),
        State("alterar-estrutura", "value"),
        State("alterar-rolagem", "value"),
        State("table-refresh-seq", "data"),
        prevent_initial_call=True,
    )
    def confirmar_alter(n_clicks, row_id, qtd, estrutura, rolagem, seq):
        if not n_clicks:
            return no_update, no_update, no_update
        try:
            if not row_id:
                return ("Nenhuma linha selecionada.", no_update, no_update)
            qtd_norm = None
            if qtd is not None and str(qtd).strip() != "":
                if not validate_numeric_positive(qtd, "quantidade"):
                    return ("Quantidade inválida.", no_update, no_update)
                qtd_norm = abs(int(float(qtd)))

            update_operation(
                operacao_id=int(row_id),
                quantidade=qtd_norm,
                estrutura=estrutura,
                rolagem=rolagem,
            )
            new_seq = int(seq or 0) + 1
            return ("Operação alterada com sucesso.", False, new_seq)
        except Exception as e:
            return (f"Erro ao alterar: {e}", no_update, no_update)

    # Encerrar: abrir/fechar
    @app.callback(
        Output("modal-encerrar-operacao", "is_open", allow_duplicate=True),
        Input("encerrar-operacao-btn", "n_clicks"),
        Input("cancelar-encerr-btn", "n_clicks"),
        Input("voltar-encerr-btn", "n_clicks"),
        State("modal-encerrar-operacao", "is_open"),
        State("selected-row-id", "data"),
        prevent_initial_call=True,
    )
    def toggle_modal_encerrar(n_open, n_cancel, n_back, is_open, row_id):
        trig = ctx.triggered_id
        if trig == "encerrar-operacao-btn":
            return bool(row_id)
        if trig in ("cancelar-encerr-btn", "voltar-encerr-btn"):
            return False
        return is_open

    # Encerrar: preload
    @app.callback(
        Output("encerrar-ticker", "value"),
        Output("encerrar-operacao", "value"),
        Output("encerrar-direcao", "value"),
        Output("encerrar-valor-opcao", "value"),
        Output("encerrar-data-op", "value"),
        Output("encerrar-quantidade", "value"),
        Output("rolagem", "value"),
        Input("modal-encerrar-operacao", "is_open"),
        State("selected-row-id", "data"),
        State("tabela-operacoes", "data"),
        prevent_initial_call=True,
    )
    def preload_modal_encerrar(is_open, row_id, rows):
        if not is_open or not row_id or not rows:
            return (no_update,) * 7
        row = next((r for r in rows if str(r.get("id")) == str(row_id)), None)
        if not row:
            return ("", "", "", None, "", None, "")
        def num_or_none(v):
            try: return float(v)
            except Exception: return None
        def qty_abs(v):
            try: return abs(int(float(v)))
            except Exception: return None
        return (
            str(row.get("TICKER") or ""),
            str(row.get("OPERAÇÃO") or ""),
            str(row.get("DIREÇÃO") or ""),
            num_or_none(row.get("VALOR OPÇÃO")),
            str(row.get("DATA OP") or ""),
            qty_abs(row.get("QUANTIDADE")),
            row.get("ROLAGEM") or "",
        )

    # Encerrar: confirmar
    @app.callback(
        Output("modal-encerrar-mensagem", "children"),
        Output("modal-encerrar-operacao", "is_open", allow_duplicate=True),
        Output("table-refresh-seq", "data", allow_duplicate=True),
        Input("confirmar-encerr-btn", "n_clicks"),
        State("selected-row-id", "data"),
        State("encerrar-quantidade", "value"),
        State("valor-encerr", "value"),
        State("data-encerr", "value"),
        State("rolagem", "value"),
        State("motivo-encerr", "value"),
        State("table-refresh-seq", "data"),
        prevent_initial_call=True,
    )
    def confirmar_encerrar(n_clicks, row_id, qtd_encerr, valor_encerr, data_encerr, rolagem_texto, motivo_encerr, seq):
        if not n_clicks:
            return no_update, no_update, no_update
        try:
            if not row_id:
                return ("Nenhuma linha selecionada.", no_update, no_update)

            # Campos obrigatórios: quantidade e valor de encerramento
            if qtd_encerr is None or str(qtd_encerr).strip() == "" or not validate_numeric_positive(qtd_encerr, "quantidade encerrada"):
                return ("Quantidade encerrada inválida.", no_update, no_update)
            if valor_encerr is None or str(valor_encerr).strip() == "" or not validate_numeric_positive(valor_encerr, "valor encerramento"):
                return ("Valor de encerramento inválido.", no_update, no_update)
            if not validate_date(data_encerr):
                return ("Data de encerramento inválida.", no_update, no_update)

            close_operation(
                row_id=int(row_id),
                qtd_encerrada=abs(int(float(qtd_encerr))),
                valor_encerr_unit=abs(float(valor_encerr)),
                data_encerr=data_encerr,
                rolagem_texto=rolagem_texto,
                motivo_encerr=motivo_encerr
            )
            new_seq = int(seq or 0) + 1
            return ("Encerramento registrado com sucesso.", False, new_seq)
        except Exception as e:
            return (f"Erro ao encerrar: {e}", no_update, no_update)

 # -------------------------------
    # Relatórios: opções dinâmicas (Estrutura/Bundle) a partir de Encerradas
    # -------------------------------
    @app.callback(
        Output("e-estrutura", "options"),
        Output("a-estrutura", "options"),
        Output("e-bundle", "options"),
        Output("a-bundle", "options"),
        Input("rel-tabs", "active_tab"),
        prevent_initial_call=False,
    )
    def rel_populate_options(_tab):
        df = get_encerradas()
        if df is None or df.empty:
            estr = [{"label": "Todas", "value": ""}]
            bund = [{"label": "Todos", "value": ""}]
            return estr, estr, bund, bund

        # Estrutura vem minúscula do DB
        estr_vals = [e for e in df["estrutura"].dropna().unique() if str(e).strip()]
        estr_opts = sorted(estr_vals)
        estr = [{"label": "Todas", "value": ""}] + [{"label": v, "value": v} for v in estr_opts]

        # Bundle ainda não está persistido em 'encerradas' (fase futura)
        bund = [{"label": "Todos", "value": ""}]
        return estr, estr, bund, bund

    # -------------------------------
    # Relatório Sintético: KPIs, gráficos, tabelas
    # -------------------------------
    @app.callback(
        Output("kpi-gp-real", "children"),
        Output("kpi-n-enc", "children"),
        Output("kpi-ticket", "children"),
        Output("kpi-hit", "children"),
        Output("kpi-topbot", "children"),
        Output("graf-gp-mensal", "figure"),
        Output("graf-simples-vs-estrutura", "figure"),
        Output("sint-table", "data"),
        Output("sint-top10", "data"),
        Input("e-date-range", "start_date"),
        Input("e-date-range", "end_date"),
        Input("e-tipo", "value"),
        Input("e-estrutura", "value"),
        Input("e-bundle", "value"),
        Input("e-ticker", "value"),
        prevent_initial_call=False,
    )
    def rel_sintetico(start_iso, end_iso, tipo, estrutura, bundle, ticker):
        import plotly.express as px

        df_raw = get_encerradas()
        if df_raw is None or df_raw.empty:
            # figuras vazias
            fig_empty1 = px.bar(title="G/P por Mês")
            fig_empty2 = px.bar(title="Simples vs Estrutura")
            return ("0,00", "0", "0,00", "0.0%", "Melhor: - | Pior: -",
                    fig_empty1, fig_empty2, [], [])

        # Normalização para padrão do UI
        dfn = df_raw.rename(columns={
            "id": "ID_ENC",
            "id_origem": "ID_ORIGEM",
            "ticker": "TICKER",
            "operacao": "OPERACAO",
            "direcao": "DIRECAO",
            "strike": "STRIKE",
            "quantidade": "QTD_ENC",
            "valor_opcao": "PRECO_ABERT",
            "valor_encerr": "PRECO_ENC",
            "valor_operacao": "CF_ABERT",
            "valor_oper_encerr": "CF_ENC",
            "g_p": "GP",
            "data_op": "DATA_OP",
            "data_encerr": "DATA_ENC",
            "estrutura": "ESTRUTURA",
            "rolagem": "ROLAGEM",
            "motivo": "MOTIVO",
        }).copy()

        # Derivados mínimos
        if "BUNDLE" not in dfn.columns:
            dfn["BUNDLE"] = ""  # placeholder até persistirmos em 'encerradas'
        dfn["ESTRUTURA"] = dfn["ESTRUTURA"].fillna("")
        dfn["TIPO"] = dfn["ESTRUTURA"].apply(lambda s: "Estrutura" if str(s).strip() else "Simples")

        # Filtro por período (DATA_ENC)
        if start_iso or end_iso:
            start_dt = datetime.fromisoformat(start_iso) if start_iso else None
            end_dt = datetime.fromisoformat(end_iso) if end_iso else None
            dcol = dfn["DATA_ENC"].apply(_parse_ddmmyyyy)
            mask = pd.Series(True, index=dfn.index)
            if start_dt:
                mask &= dcol >= start_dt
            if end_dt:
                mask &= dcol <= end_dt
            dfn = dfn[mask]

        # Filtros adicionais
        if (tipo or "") != "":
            dfn = dfn[dfn["TIPO"] == tipo]
        if (estrutura or "") != "":
            dfn = dfn[dfn["ESTRUTURA"] == estrutura]
        if (bundle or "") != "":
            dfn = dfn[dfn["BUNDLE"] == bundle]
        if ticker and str(ticker).strip():
            b = str(ticker).strip().upper()
            dfn = dfn[dfn["TICKER"].astype(str).str.upper().str.contains(b, na=False)]

        # KPIs
        if dfn.empty:
            fig_empty1 = px.bar(title="G/P por Mês")
            fig_empty2 = px.bar(title="Simples vs Estrutura")
            return ("0,00", "0", "0,00", "0.0%", "Melhor: - | Pior: -",
                    fig_empty1, fig_empty2, [], [])

        gp_total = float(dfn["GP"].sum())
        n_enc = int(dfn.shape[0])
        ticket = (gp_total / n_enc) if n_enc else 0.0
        hit = (100.0 * (dfn["GP"] > 0).mean()) if n_enc else 0.0
        top = dfn.nlargest(1, "GP")[["ID_ENC", "GP"]].values.tolist() if n_enc else []
        bot = dfn.nsmallest(1, "GP")[["ID_ENC", "GP"]].values.tolist() if n_enc else []
        top_str = f"Melhor: {top[0][0]} ({top[0][1]:.2f})" if top else "Melhor: -"
        bot_str = f"Pior: {bot[0][0]} ({bot[0][1]:.2f})" if bot else "Pior: -"

        # Gráfico G/P por mês
        def _to_month(s):
            try:
                dtv = datetime.strptime(s, "%d/%m/%Y")
                return dtv.strftime("%Y-%m")
            except Exception:
                return None

        dfn["_MES"] = dfn["DATA_ENC"].apply(_to_month)
        g_mes = dfn.groupby("_MES", dropna=True)["GP"].sum().reset_index()
        fig_mes = px.bar(g_mes, x="_MES", y="GP", title="G/P por Mês")

        # Simples vs Estrutura
        g_tipo = dfn.groupby("TIPO")["GP"].sum().reset_index()
        fig_tipo = px.bar(g_tipo, x="TIPO", y="GP", title="Simples vs Estrutura")

        # Tabela por Estrutura/Bundle
        tbl = dfn.groupby(["ESTRUTURA", "BUNDLE"], dropna=False).agg(GP=("GP", "sum"), N_ENC=("ID_ENC", "count")).reset_index()

        # Top10
        top10 = dfn.sort_values("GP", ascending=False).head(10)[["ID_ENC", "TICKER", "ESTRUTURA", "GP"]]

        return (
            f"{gp_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"{n_enc}",
            f"{ticket:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"{hit:.1f}%",
            f"{top_str} | {bot_str}",
            fig_mes,
            fig_tipo,
            tbl.to_dict("records"),
            top10.to_dict("records")
        )

    # Drill-down: clicar na linha do Sintético aplica filtro no Analítico
    @app.callback(
        Output("a-estrutura", "value", allow_duplicate=True),
        Output("a-bundle", "value", allow_duplicate=True),
        Input("sint-table", "active_cell"),
        State("sint-table", "data"),
        prevent_initial_call=True,
    )
    def rel_drilldown_sint_to_analit(active_cell, data):
        if not active_cell or not data:
            return no_update, no_update
        r = data[active_cell["row"]]
        return r.get("ESTRUTURA") or "", r.get("BUNDLE") or ""

    # -------------------------------
    # Relatório Analítico: Linhas vs Grupos
    # -------------------------------
    @app.callback(
        Output("analitico-table", "data"),
        Output("analitico-table", "style_data_conditional"),
        Input("a-date-range", "start_date"),
        Input("a-date-range", "end_date"),
        Input("a-tipo", "value"),
        Input("a-estrutura", "value"),
        Input("a-bundle", "value"),
        Input("a-view-mode", "value"),
        prevent_initial_call=False,
    )
    def rel_analitico(start_iso, end_iso, tipo, estrutura, bundle, view_mode):
        df_raw = get_encerradas()

        # Normalização
        df = df_raw.rename(columns={
            "id": "ID_ENC",
            "id_origem": "ID_ORIGEM",
            "ticker": "TICKER",
            "operacao": "OPERACAO",
            "direcao": "DIRECAO",
            "strike": "STRIKE",
            "quantidade": "QTD_ENC",
            "valor_opcao": "PRECO_ABERT",
            "valor_encerr": "PRECO_ENC",
            "valor_operacao": "CF_ABERT",
            "valor_oper_encerr": "CF_ENC",
            "g_p": "GP",
            "data_op": "DATA_OP",
            "data_encerr": "DATA_ENC",
            "estrutura": "ESTRUTURA",
            "rolagem": "ROLAGEM",
            "motivo": "MOTIVO",
        }).copy()

        if df.empty:
            sdc = []
            return [], sdc

        if "BUNDLE" not in df.columns:
            df["BUNDLE"] = ""  # placeholder até persistirmos em 'encerradas'
        df["ESTRUTURA"] = df["ESTRUTURA"].fillna("")
        df["TIPO"] = df["ESTRUTURA"].apply(lambda s: "Estrutura" if str(s).strip() else "Simples")

        # Derivados úteis (opcional)
        def _dt(s):
            try:
                return datetime.strptime(s, "%d/%m/%Y")
            except Exception:
                return None
        df["__DT_OP"] = df["DATA_OP"].apply(_dt)
        df["__DT_ENC"] = df["DATA_ENC"].apply(_dt)
        def _dias(row):
            try:
                if row["__DT_OP"] and row["__DT_ENC"]:
                    return (row["__DT_ENC"] - row["__DT_OP"]).days
            except Exception:
                pass
            return None
        df["DIAS_POS"] = df.apply(_dias, axis=1)
        def _ret(row):
            try:
                cf = float(row["CF_ABERT"])
                gp = float(row["GP"])
                denom = abs(cf)
                return (gp / denom) if denom else None
            except Exception:
                return None
        df["RET_PCT"] = df.apply(_ret, axis=1)

        # Filtros
        if start_iso or end_iso:
            start_dt = datetime.fromisoformat(start_iso) if start_iso else None
            end_dt = datetime.fromisoformat(end_iso) if end_iso else None
            mask = pd.Series(True, index=df.index)
            if start_dt:
                mask &= df["__DT_ENC"] >= start_dt
            if end_dt:
                mask &= df["__DT_ENC"] <= end_dt
            df = df[mask]

        if (tipo or "") != "":
            df = df[df["TIPO"] == tipo]
        if (estrutura or "") != "":
            df = df[df["ESTRUTURA"] == estrutura]
        if (bundle or "") != "":
            df = df[df["BUNDLE"] == bundle]

        # Limpa colunas auxiliares
        if "__DT_OP" in df.columns: df.drop(columns=["__DT_OP"], inplace=True)
        if "__DT_ENC" in df.columns: df.drop(columns=["__DT_ENC"], inplace=True)

        if view_mode == "linhas":
            sdc = []
            return df.to_dict("records"), sdc

        # visão "grupos": agrega por Estrutura/Bundle e intercala linhas header
        rows = []
        sdc = [{
            "if": {"filter_query": "{__GROUP__} = 1"},
            "backgroundColor": "#333",
            "color": "white",
            "fontWeight": "bold",
        }]
        if df.empty:
            return [], sdc

        g = df.groupby(["ESTRUTURA", "BUNDLE"], dropna=False)
        for (estr, bund), dfg in g:
            gp_sum = float(dfg["GP"].sum())
            n_enc = int(dfg.shape[0])
            header = {
                "ID_ENC": "", "ID_ORIGEM": "",
                "TICKER": "", "OPERACAO": "", "DIRECAO": "",
                "ESTRUTURA": estr or "", "BUNDLE": bund or "",
                "PERNA": "", "ROLAGEM": "",
                "QTD_ENC": "", "PRECO_ABERT": "", "PRECO_ENC": "",
                "CF_ABERT": "", "CF_ENC": "",
                "GP": gp_sum, "RET_PCT": "", "DATA_OP": "", "DATA_ENC": "",
                "DIAS_POS": "", "MOTIVO": "",
                "__GROUP__": 1
            }
            rows.append(header)
            for _, r in dfg.iterrows():
                rec = r.to_dict()
                rec["__GROUP__"] = 0
                rows.append(rec)

        return rows, sdc

    # Exportar Sintético
    @app.callback(
        Output("download-sint", "data"),
        Input("export-sint-btn", "n_clicks"),
        State("sint-table", "data"),
        prevent_initial_call=True,
    )
    def export_sint(n, data):
        if not n or not data:
            return no_update
        import pandas as pd
        df = pd.DataFrame(data)
        fname = f"sintetico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return dcc.send_data_frame(df.to_excel, fname, index=False)

    # Exportar Analítico
    @app.callback(
        Output("download-analit", "data"),
        Input("export-analit-btn", "n_clicks"),
        State("analitico-table", "data"),
        prevent_initial_call=True,
    )
    def export_analit(n, data):
        if not n or not data:
            return no_update
        import pandas as pd
        df = pd.DataFrame(data)
        fname = f"analitico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return dcc.send_data_frame(df.to_excel, fname, index=False)


    # Clientside callbacks
    app.clientside_callback(
        "window.dash_clientside.clientside.focusTicker",
        Output("focus-ticker-pulse", "data"),
        Input("modal-nova-operacao", "is_open"),
        prevent_initial_call=False,
    )

    app.clientside_callback(
        "window.dash_clientside.clientside.extractInfo",
        Output("nova-operacao", "value"),
        Output("nova-data-exerc", "value"),
        Input("modal-nova-operacao", "is_open"),
        Input("nova-ticker", "value"),
        prevent_initial_call=True,
    )
