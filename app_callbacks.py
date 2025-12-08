# app_callbacks.py
from dash import Input, Output, State, no_update, ctx
from database import add_operation

def register_callbacks(app):
    # -----------------------------
    # Seleção na tabela -> Store selected-row-id
    # -----------------------------
    @app.callback(
        Output('selected-row-id', 'data'),
        Input('tabela-operacoes', 'active_cell'),
        Input('tabela-operacoes', 'selected_rows'),
        State('tabela-operacoes', 'data'),
        prevent_initial_call=True
    )
    def set_selected_row(active_cell, selected_rows, rows):
        if not rows:
            return no_update

        # Prioriza active_cell; fallback para selected_rows
        if active_cell and isinstance(active_cell, dict) and active_cell.get('row') is not None:
            idx = active_cell['row']
        elif selected_rows and len(selected_rows) > 0:
            idx = selected_rows[0]
        else:
            return no_update

        try:
            row = rows[idx]
            return row.get('id', no_update)
        except Exception:
            return no_update

    # -----------------------------
    # Modal Nova: abrir/fechar (somente toggle visual)
    # -----------------------------
    @app.callback(
        Output('modal-nova-operacao', 'is_open', allow_duplicate=True),
        Input('nova-operacao-btn', 'n_clicks'),
        Input('cancelar-nova-btn', 'n_clicks'),
        Input('voltar-nova-btn', 'n_clicks'),
        State('modal-nova-operacao', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_modal_nova(n_open, n_cancel, n_back, is_open):
        trig = ctx.triggered_id
        if trig == 'nova-operacao-btn':
            return True
        if trig in ('cancelar-nova-btn', 'voltar-nova-btn'):
            return False
        return is_open


    # -----------------------------
    # Modal Nova: confirmar (valida, grava e fecha/permanece)
    # -----------------------------
    @app.callback(
        Output('modal-nova-mensagem', 'children'),
        Output('modal-nova-operacao', 'is_open', allow_duplicate=True),
        Input('confirmar-nova-btn', 'n_clicks'),
        State('nova-ticker', 'value'),
        State('nova-operacao', 'value'),
        State('nova-direcao', 'value'),
        State('nova-strike', 'value'),
        State('nova-quantidade', 'value'),
        State('nova-valor-opcao', 'value'),
        State('nova-data-exerc', 'value'),
        State('nova-estrutura', 'value'),
        State('nova-rolagem', 'value'),
        prevent_initial_call=True
    )
    def confirmar_nova(n_clicks, ticker, operacao, direcao, strike, qtd, val_opcao, data_exerc, estrutura, rolagem):
        try:
            # validações mínimas
            if not ticker or not operacao or not direcao or not qtd or not val_opcao or not data_exerc:
                return ("Preencha os campos obrigatórios.", True)

            # conversões seguras
            ticker = ticker.strip().upper()
            qtd_int = abs(int(qtd))
            val_opc = abs(float(val_opcao))
            strike_val = float(strike) if strike not in (None, '') else None

            # gravação
            add_operation(
                ticker=ticker,
                operacao=operacao,
                direcao=direcao,
                strike=strike_val,
                quantidade=qtd_int,
                valor_opcao=val_opc,
                data_exerc=data_exerc,
                estrutura=estrutura,
                rolagem=rolagem
            )
            return ("Operação incluída com sucesso.", False)
        except Exception as e:
            return (f"Erro ao incluir: {e}", True)

    # -----------------------------
    # Modal Alterar: abrir/fechar (abre somente com selected-row-id)
    # -----------------------------
    @app.callback(
        Output('modal-alterar-operacao', 'is_open'),
        Input('alterar-operacao-btn', 'n_clicks'),
        Input('cancelar-alter-btn', 'n_clicks'),
        State('modal-alterar-operacao', 'is_open'),
        State('selected-row-id', 'data'),
        prevent_initial_call=True
    )
    def toggle_modal_alterar(n_open, n_cancel, is_open, row_id):
        trig = ctx.triggered_id
        if trig == 'alterar-operacao-btn':
            return bool(row_id)
        if trig == 'cancelar-alter-btn':
            return False
        return is_open

    # -----------------------------
    # Modal Alterar: preload de campos ao abrir (usa dados atuais da tabela)
    # -----------------------------
    @app.callback(
        Output('alterar-ticker', 'children'),
        Output('alterar-operacao', 'children'),
        Output('alterar-direcao', 'children'),
        Output('alterar-quantidade', 'value'),
        Output('alterar-valor-opcao', 'children'),
        Output('alterar-data-op', 'children'),
        Output('alterar-data-exerc', 'children'),
        Output('alterar-estrutura', 'value'),
        Output('alterar-rolagem', 'value'),
        Input('modal-alterar-operacao', 'is_open'),
        State('selected-row-id', 'data'),
        State('tabela-operacoes', 'data'),
        prevent_initial_call=True
    )
    def preload_modal_alterar(is_open, row_id, rows):
        if not is_open or not row_id or not rows:
            return (no_update,) * 9

        # Encontra a linha pelo id oculto
        row = next((r for r in rows if r.get('id') == row_id), None)
        if not row:
            return ("", "", "", None, "", "", "", "", "")

        # Safe casts
        def _abs_int(v):
            try:
                return abs(int(v))
            except Exception:
                return None

        return (
            str(row.get('TICKER', "")),
            str(row.get('OPERAÇÃO', "")),
            str(row.get('DIREÇÃO', "")),
            _abs_int(row.get('QUANTIDADE')),
            str(row.get('VALOR OPÇÃO', "")),
            str(row.get('DATA OP', "")),
            str(row.get('DATA EXERC', "")),
            row.get('ESTRUTURA', "") or "",
            row.get('ROLAGEM', "") or ""
        )

    # -----------------------------
    # Modal Encerrar: abrir/fechar (inclui voltar-encerr-btn para fechar)
    # -----------------------------
    @app.callback(
        Output('modal-encerrar-operacao', 'is_open'),
        Input('encerrar-operacao-btn', 'n_clicks'),
        Input('cancelar-encerr-btn', 'n_clicks'),
        Input('voltar-encerr-btn', 'n_clicks'),
        State('modal-encerrar-operacao', 'is_open'),
        State('selected-row-id', 'data'),
        prevent_initial_call=True
    )
    def toggle_modal_encerrar(n_open, n_cancel, n_back, is_open, row_id):
        trig = ctx.triggered_id
        if trig == 'encerrar-operacao-btn':
            return bool(row_id)
        if trig in ('cancelar-encerr-btn', 'voltar-encerr-btn'):
            return False
        return is_open

    # -----------------------------
    # Modal Encerrar: preload de campos ao abrir (usa dados atuais da tabela)
    # -----------------------------
    @app.callback(
        Output('encerrar-ticker', 'value'),
        Output('encerrar-operacao', 'value'),
        Output('encerrar-direcao', 'value'),
        Output('encerrar-valor-opcao', 'value'),
        Output('encerrar-data-op', 'value'),
        Output('encerrar-quantidade', 'value'),
        Output('rolagem', 'value'),
        Input('modal-encerrar-operacao', 'is_open'),
        State('selected-row-id', 'data'),
        State('tabela-operacoes', 'data'),
        prevent_initial_call=True
    )
    def preload_modal_encerrar(is_open, row_id, rows):
        if not is_open or not row_id or not rows:
            return (no_update,) * 7

        row = next((r for r in rows if r.get('id') == row_id), None)
        if not row:
            return ("", "", "", None, "", None, "")

        def _abs_int(v):
            try:
                return abs(int(v))
            except Exception:
                return None

        def _float_or_none(v):
            try:
                return float(v)
            except Exception:
                return None

        return (
            str(row.get('TICKER', "")),
            str(row.get('OPERAÇÃO', "")),
            str(row.get('DIREÇÃO', "")),
            _float_or_none(row.get('VALOR OPÇÃO')),
            str(row.get('DATA OP', "")),
            _abs_int(row.get('QUANTIDADE')),
            row.get('ROLAGEM', "") or ""
        )
def register_callbacks_ui_extras(app):
    # 1) Store: manter selected-row-id em sincronia com a DataTable
    @app.callback(
        Output('selected-row-id', 'data'),
        Input('tabela-operacoes', 'selected_rows'),
        State('tabela-operacoes', 'data'),
        prevent_initial_call=True
    )
    def _store_selected_row(selected_rows, data):
        if not selected_rows or not data:
            return None
        idx = selected_rows[0]
        try:
            return data[idx].get('id')
        except Exception:
            return None

    # 2) Modal Nova: abrir no botão, fechar no cancelar/voltar
    @app.callback(
        Output('modal-nova-operacao', 'is_open'),
        Input('nova-operacao-btn', 'n_clicks'),
        Input('cancelar-nova-btn', 'n_clicks'),
        Input('voltar-nova-btn', 'n_clicks'),
        State('modal-nova-operacao', 'is_open'),
        prevent_initial_call=True
    )
    def _toggle_modal_nova(n_open, n_cancel, n_back, is_open):
        trig = ctx.triggered_id
        if trig == 'nova-operacao-btn':
            # reset flag de foco clientside
            try:
                # pequena flag via clientStorage não necessária; foco é idempotente
                pass
            except Exception:
                pass
            return True
        if trig in ('cancelar-nova-btn', 'voltar-nova-btn'):
            return False
        return is_open

    # 3) Modal Alterar: abrir apenas com selected-row-id; fechar no cancelar
    @app.callback(
        Output('modal-alterar-operacao', 'is_open'),
        Input('alterar-operacao-btn', 'n_clicks'),
        Input('cancelar-alter-btn', 'n_clicks'),
        State('modal-alterar-operacao', 'is_open'),
        State('selected-row-id', 'data'),
        prevent_initial_call=True
    )
    def _toggle_modal_alterar(n_open, n_cancel, is_open, row_id):
        trig = ctx.triggered_id
        if trig == 'alterar-operacao-btn':
            return bool(row_id)
        if trig == 'cancelar-alter-btn':
            return False
        return is_open

    # 4) Preload do Modal Alterar a partir da DataTable
    @app.callback(
        Output('alterar-ticker', 'children'),
        Output('alterar-operacao', 'children'),
        Output('alterar-direcao', 'children'),
        Output('alterar-quantidade', 'value'),
        Output('alterar-valor-opcao', 'children'),
        Output('alterar-data-op', 'children'),
        Output('alterar-data-exerc', 'children'),
        Output('alterar-estrutura', 'value'),
        Output('alterar-rolagem', 'value'),
        Input('modal-alterar-operacao', 'is_open'),
        State('selected-row-id', 'data'),
        State('tabela-operacoes', 'data'),
        prevent_initial_call=True
    )
    def _preload_alterar(is_open, row_id, table_data):
        if not is_open or not row_id or not table_data:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        row = next((r for r in table_data if str(r.get('id')) == str(row_id)), None)
        if not row:
            return "", "", "", None, "", "", "", "", ""

        def safe_str(v): return "" if v is None else str(v)
        def safe_int_abs(v):
            try:
                return abs(int(float(v)))
            except Exception:
                return None

        return (
            safe_str(row.get('TICKER')),
            safe_str(row.get('OPERAÇÃO')),
            safe_str(row.get('DIREÇÃO')),
            safe_int_abs(row.get('QUANTIDADE')),
            safe_str(row.get('VALOR OPÇÃO')),
            safe_str(row.get('DATA OP')),
            safe_str(row.get('DATA EXERC')),
            row.get('ESTRUTURA') or "",
            row.get('ROLAGEM') or ""
        )

    # 5) Modal Encerrar: abrir apenas com selected-row-id; fechar no cancelar
    @app.callback(
        Output('modal-encerrar-operacao', 'is_open'),
        Input('encerrar-operacao-btn', 'n_clicks'),
        Input('cancelar-encerr-btn', 'n_clicks'),
        State('modal-encerrar-operacao', 'is_open'),
        State('selected-row-id', 'data'),
        prevent_initial_call=True
    )
    def _toggle_modal_encerrar(n_open, n_cancel, is_open, row_id):
        trig = ctx.triggered_id
        if trig == 'encerrar-operacao-btn':
            return bool(row_id)
        if trig == 'cancelar-encerr-btn':
            return False
        return is_open

    # 6) Preload do Modal Encerrar a partir da DataTable
    @app.callback(
        Output('encerrar-ticker', 'value'),
        Output('encerrar-operacao', 'value'),
        Output('encerrar-direcao', 'value'),
        Output('encerrar-valor-opcao', 'value'),
        Output('encerrar-data-op', 'value'),
        Output('encerrar-quantidade', 'value'),
        Output('rolagem', 'value'),
        Input('modal-encerrar-operacao', 'is_open'),
        State('selected-row-id', 'data'),
        State('tabela-operacoes', 'data'),
        prevent_initial_call=True
    )
    def _preload_encerrar(is_open, row_id, table_data):
        if not is_open or not row_id or not table_data:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

        row = next((r for r in table_data if str(r.get('id')) == str(row_id)), None)
        if not row:
            return "", "", "", None, "", None, ""

        def num_or_none(v):
            try:
                f = float(v)
                return f
            except Exception:
                return None

        def qty_abs(v):
            try:
                return abs(int(float(v)))
            except Exception:
                return None

        return (
            str(row.get('TICKER') or ""),
            str(row.get('OPERAÇÃO') or ""),
            str(row.get('DIREÇÃO') or ""),
            num_or_none(row.get('VALOR OPÇÃO')),
            str(row.get('DATA OP') or ""),
            qty_abs(row.get('QUANTIDADE')),
            row.get('ROLAGEM') or ""
        )

    # 7) Clientside callbacks (foco no ticker e extração de campos)
    app.clientside_callback(
        "window.dash_clientside.clientside.focusTicker",
        Output('nova-ticker', 'value'),
        Input('modal-nova-operacao', 'is_open'),
        prevent_initial_call=True
    )
    app.clientside_callback(
        "window.dash_clientside.clientside.extractInfo",
        Output('nova-operacao', 'value'),
        Output('nova-data-exerc', 'value'),
        Output('nova-strike', 'value'),
        Input('modal-nova-operacao', 'is_open'),
        Input('nova-ticker', 'value'),
        prevent_initial_call=True
    )
