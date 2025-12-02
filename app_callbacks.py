# app_callbacks
import dash
import pandas as pd
import sqlite3
import logging
import locale
import re
import requests
from bs4 import BeautifulSoup
from dash import callback, Output, Input, State, ctx, html, dcc, clientside_callback
from dash.dependencies import ALL
from datetime import datetime, timedelta
from validations import *
from database import update_operation, get_transactions, get_encerradas, check_table_exists, init_database, recalculate_values, update_saldo, get_saldo_mes, get_saldo_acumulado
from calculations import calculate_operation_value, fmt_br

logging.basicConfig(level=logging.INFO)
_registered = False

def register_callbacks(app):
    app.config.suppress_callback_exceptions = True
    app.config.prevent_initial_callbacks = "initial_duplicate"
    global _registered
    if _registered:
        logging.info("[LOG] Callbacks já registrados, ignorando")
        return
    logging.info("[LOG] Registrando callbacks")
    _registered = True
    init_database()  # Garante DB criada on start
           
    app.clientside_callback(
        """
        function(is_open) {
            // Reset da flag quando fechar o modal
            if (!is_open) {
                window.hasFocusedTicker = false;
                return window.dash_clientside.no_update;
            }
            
            // Só executa quando abrir o modal
            if (is_open && !window.hasFocusedTicker) {
                setTimeout(() => {
                    const el = document.getElementById('nova-ticker');
                    if (el) {
                        el.focus();
                        el.select();
                        window.hasFocusedTicker = true;
                        console.log("Foco no ticker ativado com sucesso!");
                    }
                }, 150);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('dummy-focus-ticker', 'children'),
        Input('modal-nova-operacao', 'is_open'),
        prevent_initial_call=True  # ← ESSENCIAL!
    )

    # Novo Clientside Callback - Toggle Dark Mode (Persistente, ajustado JS)
    app.clientside_callback(
        """
        function(value) {
            const theme = value ? 'dark-theme' : 'light-theme';
            document.body.className = theme;
            localStorage.setItem('theme', theme); // Persist for reload
            return value;
        }
        """,
        Output('theme-switch', 'value'),
        Input('theme-switch', 'value'),
        prevent_initial_call=True
    )

    # Load Inicial Dark Mode (com allow_duplicate e prevent_initial_call fix)
    app.clientside_callback(
        """
        function(n) {
            const savedTheme = localStorage.getItem('theme') || 'light-theme';
            document.body.className = savedTheme;
            return savedTheme === 'dark-theme';
        }
        """,
        Output('theme-switch', 'value', allow_duplicate=True),
        Input('dummy-initial-load', 'children'),
        prevent_initial_call='initial_duplicate'
    )
    # 2º Callback - validação dinâmica
 
    @callback( 
        [Output('modal-alterar-operacao', 'is_open'), 
        Output('alterar-ticker', 'children'), 
        Output('alterar-operacao', 'children'), 
        Output('alterar-direcao', 'children'), 
        Output('alterar-quantidade', 'value'), 
        Output('alterar-valor-opcao', 'value'), 
        Output('alterar-data-op', 'value'), 
        Output('alterar-data-exerc', 'children'), 
        Output('alterar-estrutura', 'value'), 
        Output('alterar-rolagem', 'value'), 
        Output('alterar-ticker-val', 'children'), 
        Output('alterar-direcao-val', 'children'), 
        Output('alterar-quantidade-val', 'children'), 
        Output('alterar-valor-opcao-val', 'children'), 
        Output('alterar-data-op-val', 'children'), 
        Output('alterar-data-exerc-val', 'children'), 
        Output('alterar-estrutura-val', 'children'), 
        Output('modal-alterar-mensagem', 'children'), 
        Output('table-update-trigger-alterar', 'children'), 
        Output('tabela-operacoes', 'data')], 
        [Input('alterar-operacao-btn', 'n_clicks'), 
        Input('confirmar-alter-btn', 'n_clicks'), 
        Input('cancelar-alter-btn', 'n_clicks'), 
        Input('alterar-quantidade', 'value'), 
        Input('alterar-valor-opcao', 'value'), 
        Input('alterar-data-op', 'value'), 
        Input('alterar-estrutura', 'value'), 
        Input('alterar-rolagem', 'value')], 
        [State('tabela-operacoes', 'active_cell'), 
        State('tabela-operacoes', 'data'), 
        State('modal-alterar-operacao', 'is_open'), 
        State('selected-row', 'data')], 
        prevent_initial_call=True 
    ) 
    def alterar_completo(alterar_click, confirmar_click, cancelar_click, 
                        qtd, valor, data_op, estrutura, rolagem, active_cell, table_data, is_open, selected_row): 
        trigger_id = ctx.triggered_id if ctx.triggered else None 
        logging.info(f"[ALTERAR] Trigger: {trigger_id}, Active Cell: {active_cell}, Selected Row: {selected_row}, Table Data: {len(table_data) if table_data else 0} rows") 
        
        if trigger_id == 'cancelar-alter-btn': 
            return [False] + [''] * 9 + [''] * 7 + ['', '', table_data] 
        
        if trigger_id == 'alterar-operacao-btn' and not is_open: 
            if not table_data: 
                logging.error("[ALTERAR] Tabela vazia") 
                return [True, 'N/A', 'N/A', 'N/A', '', '', '', 'N/A', '', '', html.Span('×', className='validation-error'), html.Span('×', className='validation-error'), '', '', '', '', '', '   Tabela vazia', '', table_data] 
            if selected_row and 'TICKER' in selected_row: 
                row = selected_row 
                logging.info(f"[ALTERAR] Carregando linha via selected_row: {row}") 
            elif active_cell and active_cell['row'] < len(table_data): 
                row = table_data[active_cell['row']] 
                logging.info(f"[ALTERAR] Carregando linha via active_cell: {row}") 
            else: 
                logging.error("[ALTERAR] Nenhuma linha selecionada") 
                return [True, 'N/A', 'N/A', 'N/A', '', '', '', 'N/A', '', '', html.Span('×', className='validation-error'), html.Span('×', className='validation-error'), '', '', '', '', '', '   Selecione uma linha na tabela', '', table_data] 
            
            op_dir = row['OPERAÇÃO/DIREÇÃO'].split('/') 
            ticker = row['TICKER'] 
            operacao = op_dir[0] 
            direcao = op_dir[1] 
            quantidade = str(row['QUANTIDADE']).replace('R$ ', '') if isinstance(row['QUANTIDADE'], str) else str(row['QUANTIDADE']) 
            valor_opcao = row['VALOR OPÇÃO'].replace('R$ ', '').replace(',', '.') if isinstance(row['VALOR OPÇÃO'], str) else str(row['VALOR OPÇÃO']) 
            return [True, ticker, operacao, direcao, quantidade, valor_opcao, row['DATA OP'], row['DATA EXERC'], row['ESTRUTURA'], row['ROLAGEM'], 
                    html.Span('✔', className='validation-ok'), html.Span('✔', className='validation-ok'), 
                    '', '', '', '', '', '', '', table_data] 
        
        if is_open and trigger_id in ['alterar-quantidade', 'alterar-valor-opcao', 'alterar-data-op', 'alterar-estrutura', 'alterar-rolagem']: 
            return [dash.no_update] * 4 + [qtd or '', valor or '', data_op or '', dash.no_update] + [estrutura or '', rolagem or ''] + [ 
                html.Span('✔', className='validation-ok'), html.Span('✔', className='validation-ok'), 
                html.Span('✔', className='validation-ok') if validate_numeric_positive(qtd, 'qtd', max_quant=1000000.0) else html.Span('×', className='validation-error'), 
                html.Span('✔', className='validation-ok') if validate_numeric_positive(valor, 'valor', max_quant=1000000.0) else html.Span('×', className='validation-error'), 
                html.Span('✔', className='validation-ok') if validate_date(data_op) else html.Span('×', className='validation-error'), 
                html.Span('✔', className='validation-ok'),  # Data Exerc não editável 
                html.Span('✔', className='validation-ok') if estrutura else '', 
                '', '', table_data] 
        
        if trigger_id == 'confirmar-alter-btn' and is_open: 
            try: 
                if not selected_row or 'TICKER' not in selected_row: 
                    if not active_cell or not table_data or active_cell['row'] >= len(table_data): 
                        logging.error("[ALTERAR] Nenhuma linha selecionada para salvar") 
                        return [True, 'N/A', 'N/A', 'N/A', '', '', '', 'N/A', '', '', html.Span('×', className='validation-error'), html.Span('×', className='validation-error'), '', '', '', '', '', '   Linha não selecionada', '', table_data] 
                    row = table_data[active_cell['row']] 
                    row_id = active_cell['row'] + 1 
                else: 
                    row = selected_row 
                    row_id = next((i + 1 for i, r in enumerate(table_data) if r['TICKER'] == row['TICKER'] and r['DATA OP'] == row['DATA OP']), None) 
                    if not row_id: 
                        logging.error("[ALTERAR] Linha não encontrada na tabela") 
                        return [True, row['TICKER'], row['OPERAÇÃO/DIREÇÃO'].split('/')[0], row['OPERAÇÃO/DIREÇÃO'].split('/')[1], '', '', '', row['DATA EXERC'], '', '', 
                                html.Span('×', className='validation-error')] * 7 + ['   Linha não encontrada', '', table_data] 
                
                op_dir = row['OPERAÇÃO/DIREÇÃO'].split('/') 
                qtd_final = float(qtd or (str(row['QUANTIDADE']).replace('R$ ', '') if isinstance(row['QUANTIDADE'], str) else str(row['QUANTIDADE']))) 
                valor_final = float(valor or (row['VALOR OPÇÃO'].replace('R$ ', '').replace(',', '.') if isinstance(row['VALOR OPÇÃO'], str) else str(row['VALOR OPÇÃO']))) 
                valor_oper = calculate_operation_value(qtd_final, valor_final, op_dir[1]) 
                
                conn = sqlite3.connect('transacoes.db') 
                conn.execute("UPDATE transacoes SET quantidade=?, valor_opcao=?, valor_operacao=?, estrutura=?, rolagem=? WHERE id=?", 
                            (qtd_final, valor_final, valor_oper, estrutura, rolagem, row_id)) 
                conn.commit() 
                conn.close() 
                logging.info(f"[ALTERAR] Alteração salva: id={row_id}, qtd={qtd_final}, valor={valor_final}") 
                
                # Atualizar tabela 
                updated_data = table_data.copy() 
                updated_row = updated_data[row_id - 1] 
                updated_row['QUANTIDADE'] = f"R$ {qtd_final:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') 
                updated_row['VALOR OPÇÃO'] = f"R$ {valor_final:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') 
                updated_row['VALOR OPERAÇÃO'] = f"R$ {valor_oper:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') 
                updated_row['ESTRUTURA'] = estrutura or '' 
                updated_row['ROLAGEM'] = rolagem or '' 
                return [False, row['TICKER'], op_dir[0], op_dir[1], qtd, valor, data_op, row['DATA EXERC'], estrutura, rolagem, 
                        html.Span('✔', className='validation-ok'), html.Span('✔', className='validation-ok'), 
                        html.Span('✔', className='validation-ok'), html.Span('✔', className='validation-ok'), 
                        html.Span('✔', className='validation-ok'), html.Span('✔', className='validation-ok'), 
                        html.Span('✔', className='validation-ok'), '   Salvo!', 
                        datetime.now().isoformat(), updated_data] 
            
            except Exception as e: 
                logging.error(f"[ALTERAR] Erro ao salvar: {e}") 
                quantidade = str(row['QUANTIDADE']).replace('R$ ', '') if isinstance(row['QUANTIDADE'], str) else str(row['QUANTIDADE']) 
                valor_opcao = row['VALOR OPÇÃO'].replace('R$ ', '').replace(',', '.') if isinstance(row['VALOR OPÇÃO'], str) else str(row['VALOR OPÇÃO']) 
                return [True, row['TICKER'], op_dir[0], op_dir[1], quantidade, valor_opcao, row['DATA OP'], row['DATA EXERC'], row['ESTRUTURA'], row['ROLAGEM'], 
                        html.Span('×', className='validation-error')] * 7 + [f'   {e}', '', table_data] 
        
        return [dash.no_update] * 19 + [table_data] 

    # 3º Callback - toggle tema

    @callback(
        Output('main-container', 'className'),
        Input('theme-switch', 'value'),
        prevent_initial_call=True
    )
    def toggle_theme(is_dark):
        logging.info(f"[LOG] Toggle theme: is_dark={is_dark}")
        return 'dark-theme' if is_dark else 'light-theme'

    # 4º Callback - armazenar linha

    @callback(
        Output('selected-row', 'data'),
        [Input('tabela-operacoes', 'active_cell'),
         Input('periodo-date-range', 'start_date'),
         Input('periodo-date-range', 'end_date'),
         Input('busca-ticker', 'value')],
        [State('tabela-operacoes', 'data')],
        prevent_initial_call=True
    )
    def store_selected_row(active_cell, start_date, end_date, busca_ticker, table_data):
        logging.info(f"[LOG] Armazenando linha: active_cell={active_cell}")
        if not active_cell or not table_data:
            return ''
        row_id = active_cell.get('row')
        if row_id is None:
            return ''
        row = table_data[row_id]
        if 'id' not in row:
            return ''
        return str(row['id'])

    # 5º Callback - NOVA COM EXTRAÇÃO E VALIDAÇÃO CORRIGIDA

    @callback( 
        [Output('modal-nova-operacao', 'is_open'), 
        Output('nova-operacao', 'value'), 
        Output('nova-data-exerc', 'value'), 
        Output('nova-strike', 'value'), 
        Output('nova-direcao', 'value'), 
        Output('nova-quantidade', 'value'), 
        Output('nova-valor-opcao', 'value'), 
        Output('nova-data-op', 'value'), 
        Output('nova-estrutura', 'value'), 
        Output('nova-rolagem', 'value'), 
        Output('table-update-trigger-nova', 'children'), 
        Output('nova-operacao', 'disabled'), 
        Output('nova-ticker', 'value')], 
        [Input('nova-operacao-btn', 'n_clicks'), 
        Input('confirmar-nova-btn', 'n_clicks'), 
        Input('cancelar-nova-btn', 'n_clicks'), 
        Input('nova-ticker', 'value')], 
        [State('modal-nova-operacao', 'is_open'), 
        State('nova-ticker', 'value'), 
        State('nova-operacao', 'value'), 
        State('nova-data-exerc', 'value'), 
        State('nova-strike', 'value'), 
        State('nova-direcao', 'value'), 
        State('nova-quantidade', 'value'), 
        State('nova-valor-opcao', 'value'), 
        State('nova-data-op', 'value'), 
        State('nova-estrutura', 'value'), 
        State('nova-rolagem', 'value')], 
        prevent_initial_call=True 
    ) 
    def nova_operacao(nova_click, confirmar_click, cancelar_click, ticker_input, is_open, ticker, operacao, 
                    data_exerc, strike, direcao, qtd, valor, data_op, estrutura, rolagem): 
        trigger = ctx.triggered_id 
        logging.info(f"[NOVA] Trigger: {trigger}, Ticker: {ticker_input}") 
        
        # ABRIR 
        if trigger == 'nova-operacao-btn' and not is_open: 
            return [True, '', '', '', '', '', '', datetime.now().strftime('%d/%m/%Y'), '', '', str(datetime.now()), False, ''] 
        
        # EXTRAÇÃO TICKER 
        if is_open and trigger == 'nova-ticker' and ticker_input and len(ticker_input) >= 6: 
            try: 
                ticker = ticker_input.upper()  # Converter para caixa alta 
                serie = ticker[4].upper() 
                numero = ticker[5:] 
                base_numero = ''.join(filter(str.isdigit, numero)) 
                
                if not all(c.isalnum() for c in ticker) or not serie.isalpha() or not base_numero: 
                    logging.error(f"[NOVA] Ticker inválido: {ticker}") 
                    return [is_open, operacao, data_exerc, strike, direcao, qtd, valor, data_op, estrutura, rolagem, dash.no_update, False, ticker] 
                
                isWeekly = 'W' in numero.upper() 
                semana = 3 
                if isWeekly: 
                    parts = re.split('(?i)w', numero, maxsplit=1) 
                    if len(parts) > 1 and parts[1] and any(c.isdigit() for c in parts[1]): 
                        weekly_part = ''.join(filter(str.isdigit, parts[1])) 
                        if weekly_part: 
                            semana = int(weekly_part) 
                            if semana not in [1, 2, 4, 5]: 
                                semana = 3 
                
                operacao = 'Put' if serie in 'MNOPQRSTUVWX' else 'Call' 
                mes_map_calls = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8, 'I': 9, 'J': 10, 'K': 11, 'L': 12} 
                mes_map_puts = {'M': 1, 'N': 2, 'O': 3, 'P': 4, 'Q': 5, 'R': 6, 'S': 7, 'T': 8, 'U': 9, 'V': 10, 'W': 11, 'X': 12} 
                mes_map = mes_map_puts if operacao == 'Put' else mes_map_calls 
                mes = mes_map.get(serie) 
                
                if mes: 
                    ano = datetime.now().year 
                    start = datetime(ano, mes, 1) 
                    end = datetime(ano + 1, 1, 1) - timedelta(days=1) if mes == 12 else datetime(ano, mes + 1, 1) - timedelta(days=1) 
                    calendario_mes = pd.date_range(start=start, end=end, freq='W-FRI') 
                    
                    if isWeekly: 
                        semana_idx = {1: 0, 2: 1, 4: 3, 5: 4}.get(semana, 2) 
                        data_exerc = calendario_mes[semana_idx] if 0 <= semana_idx < len(calendario_mes) else calendario_mes[2] 
                    else: 
                        data_exerc = calendario_mes[2] if len(calendario_mes) >= 3 else calendario_mes[-1] 
                    
                    data_exerc_str = data_exerc.strftime('%d/%m/%Y') 
                    # Fetch API para valor_opcao 
                    try: 
                        ticker_base = ticker[:4] 
                        ticker_obj = yf.Ticker(f"{ticker_base}.SA") 
                        chain = ticker_obj.option_chain(data_exerc.strftime('%Y-%m-%d')) 
                        atual = chain.calls.loc[chain.calls['strike'] == float(base_numero), 'lastPrice'].values[0] if operacao == 'Call' else chain.puts.loc[chain.puts['strike'] == float(base_numero), 'lastPrice'].values[0] 
                        valor = atual 
                        logging.info(f"[LOG] Valor_opcao atualizado via API: {atual}") 
                    except (IndexError, ValueError): 
                        logging.warning(f"[LOG] Falha API para {ticker}; usando manual") 
                    return [is_open, operacao, data_exerc_str, base_numero, direcao, qtd, valor, data_op, estrutura, rolagem, str(datetime.now()), True, ticker] 
                return [is_open, operacao, data_exerc, strike, direcao, qtd, valor, data_op, estrutura, rolagem, dash.no_update, False, ticker] 
            except Exception as e: 
                logging.error(f"[NOVA] Erro extração: {e}") 
                return [is_open, operacao, data_exerc, strike, direcao, qtd, valor, data_op, estrutura, rolagem, dash.no_update, False, ticker] 
        
        # CANCELAR 
        if trigger == 'cancelar-nova-btn': 
            return [False, '', '', '', '', '', '', '', '', '', dash.no_update, False, ''] 
        
        # SALVAR 
        if trigger == 'confirmar-nova-btn' and is_open: 
            required_fields = [ticker, operacao, direcao, qtd, valor, data_op, data_exerc] 
            if not all(required_fields): 
                missing = [f for f, v in zip(['Ticker', 'Operação', 'Direção', 'Quantidade', 'Valor', 'Data OP', 'Data Exerc'], required_fields) if not v] 
                logging.error(f"[NOVA] Campos obrigatórios faltando: {missing}") 
                return [is_open, operacao, data_exerc, strike, direcao, qtd, valor, data_op, estrutura, rolagem, dash.no_update, True, ticker] 
            if not (validate_numeric_positive(qtd, 'qtd', max_quant=1000000.0) and validate_numeric_positive(valor, 'valor', max_quant=1000000.0) and validate_date(data_op) and validate_date(data_exerc)): 
                logging.error(f"[NOVA] Validação falhou: qtd={qtd}, valor={valor}, data_op={data_op}, data_exerc={data_exerc}") 
                return [is_open, operacao, data_exerc, strike, direcao, qtd, valor, data_op, estrutura, rolagem, dash.no_update, True, ticker] 
            
            valor_oper = calculate_operation_value(float(qtd), float(valor), direcao) 
            with sqlite3.connect('transacoes.db') as conn: 
                conn.execute("INSERT INTO transacoes (ticker, operacao, strike, quantidade, valor_opcao, data_op, data_exerc, valor_operacao, direcao, estrutura, rolagem) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                            (ticker.upper(), operacao, strike, qtd, valor, data_op, data_exerc, valor_oper, direcao, estrutura, rolagem)) 
                conn.commit() 
                logging.info(f"[NOVA] Inserção bem-sucedida: {ticker}, {operacao}, {qtd}, {valor}, {data_op}, {data_exerc}, {valor_oper}") 
            return [False, '', '', '', '', '', '', '', '', '', str(datetime.now()), False, ''] 
        
        return [dash.no_update] * 13

    # 6º Callback - Validação NOVA

    @callback(
        [Output('nova-ticker-val', 'children'),
        Output('nova-direcao-val', 'children'),
        Output('nova-strike-val', 'children'),
        Output('nova-quantidade-val', 'children'),
        Output('nova-valor-opcao-val', 'children'),
        Output('nova-data-op-val', 'children'),
        Output('nova-data-exerc-val', 'children')],
        [Input('nova-ticker', 'value'),
        Input('nova-direcao', 'value'),
        Input('nova-strike', 'value'),
        Input('nova-quantidade', 'value'),
        Input('nova-valor-opcao', 'value'),
        Input('nova-data-op', 'value'),
        Input('nova-data-exerc', 'value')],
        prevent_initial_call=False
    )
    def validar_campos_nova(ticker, direcao, strike, qtd, valor, data_op, data_exerc):
        logging.info(f"[VALIDAÇÃO] Validando: ticker={ticker}, direcao={direcao}, strike={strike}, qtd={qtd}, valor={valor}, data_op={data_op}, data_exerc={data_exerc}")
        return [
            html.Span('✔', className='validation-ok') if validate_ticker(ticker) else html.Span('×', className='validation-error'),
            html.Span('✔', className='validation-ok') if direcao else '',
            html.Span('✔', className='validation-ok') if validate_numeric_positive(strike, 'strike') else html.Span('×', className='validation-error'),
            html.Span('✔', className='validation-ok') if validate_numeric_positive(qtd, 'qtd') else html.Span('×', className='validation-error'),
            html.Span('✔', className='validation-ok') if validate_numeric_positive(valor, 'valor') else html.Span('×', className='validation-error'),
            html.Span('✔', className='validation-ok') if validate_date(data_op) else html.Span('×', className='validation-error'),
            html.Span('✔', className='validation-ok') if validate_date(data_exerc) else html.Span('×', className='validation-error')
        ]

    # 7º Callback - update_table - SELEÇÃO ATIVADA (100% FUNCIONAL — TUDO APARECE)
    @callback(
        Output('tabela-operacoes', 'data', allow_duplicate=True),
        Output('init-table-trigger', 'data'),
        Output('tabela-operacoes', 'style_data_conditional', allow_duplicate=True),
        Input('periodo-date-range', 'start_date'),
        Input('periodo-date-range', 'end_date'),
        Input('busca-ticker', 'value'),
        Input('init-table-trigger', 'data'),
        Input('table-update-trigger-nova', 'children'),
        Input('table-update-trigger-alterar', 'children'),
        Input('encerrar-operacao-btn', 'n_clicks'),
        Input('initial-load-interval', 'n_intervals'),
        Input('theme-switch', 'value'),
        Input('tabela-operacoes', 'active_cell'),
        Input('dummy-initial-load', 'children'),
        prevent_initial_call=True
    )
    def update_table(*args):
        try:
            conn = sqlite3.connect('transacoes.db')
            query = """
            SELECT ticker AS TICKER, 
                operacao AS OPERAÇÃO, 
                direcao AS DIREÇÃO, 
                strike AS STRIKE, 
                quantidade AS QUANTIDADE, 
                valor_opcao AS 'VALOR OPÇÃO', 
                valor_operacao AS 'VALOR OPERAÇÃO', 
                data_op AS 'DATA OP', 
                data_exerc AS 'DATA EXERC', 
                estrutura AS ESTRUTURA, 
                rolagem AS ROLAGEM 
            FROM transacoes
            """
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                empty_df = pd.DataFrame(columns=['TICKER', 'OPERAÇÃO/DIREÇÃO', 'STRIKE', 'QUANTIDADE', 'VALOR OPÇÃO', 'VALOR OPERAÇÃO', 'VALOR ATUAL', 'DATA OP', 'DATA EXERC', 'ESTRUTURA', 'ROLAGEM'])
                return empty_df.to_dict('records'), str(datetime.now()), []

            # Cria coluna composta
            df['OPERAÇÃO/DIREÇÃO'] = df['OPERAÇÃO'] + '/' + df['DIREÇÃO']
            
            # Formatação brasileira CORRETA (só depois de tudo pronto)
            df['STRIKE'] = df['STRIKE'].apply(lambda x: fmt_br(x, casas=2) if pd.notnull(x) else '')
            df['VALOR OPÇÃO'] = df['VALOR OPÇÃO'].apply(lambda x: fmt_br(x, casas=4) if pd.notnull(x) else '')
            df['VALOR OPERAÇÃO'] = df['VALOR OPERAÇÃO'].apply(lambda x: fmt_br(x, casas=2) if pd.notnull(x) else '')
            df['VALOR ATUAL'] = ""  # será preenchido pelo callback #15

            # Ordem final das colunas
            cols = ['TICKER', 'OPERAÇÃO/DIREÇÃO', 'STRIKE', 'QUANTIDADE', 'VALOR OPÇÃO', 'VALOR OPERAÇÃO', 'VALOR ATUAL', 'DATA OP', 'DATA EXERC', 'ESTRUTURA', 'ROLAGEM']
            df = df[cols]

            return df.to_dict('records'), str(datetime.now()), []

        except Exception as e:
            logging.error(f"[TABLE] Erro crítico: {e}")
            return [], str(datetime.now()), []

    # 8º Callback - recalcular

    @callback(
        [Output('output-recalcular', 'children', allow_duplicate=True),
         Output('table-update-trigger-alterar', 'children', allow_duplicate=True)],
        [Input('recalcular-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def recalcular(n_clicks):
        if n_clicks is None or n_clicks == 0:
            return ['', '']
        
        try:
            logging.info("[RECALCULAR] Iniciando recálculo de médias")
            recalculate_values()
            logging.info("[RECALCULAR] Médias recalculadas com sucesso")
            return [html.Div("✅ Médias recalculadas com sucesso!", style={'color': 'green', 'display': 'block'}), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        except Exception as e:
            logging.error(f"[RECALCULAR] Erro: {e}")
            return [html.Div(f"❌ Erro: {str(e)}", style={'color': 'red', 'display': 'block'}), '']

    # 9º Callback - update_calculated_values
    @callback(
        Output('compra-call-value', 'children'),
        Output('venda-call-value', 'children'),
        Output('compra-put-value', 'children'),
        Output('venda-put-value', 'children'),
        Output('g_p-estrutura-value', 'children', allow_duplicate=True),
        Output('g_p-simples-value', 'children', allow_duplicate=True),
        Output('output-recalcular', 'children', allow_duplicate=True),
        Input('periodo-date-range', 'start_date'),
        Input('periodo-date-range', 'end_date'),
        Input('table-update-trigger-nova', 'children'),
        Input('table-update-trigger-alterar', 'children'),
        Input('trigger-recalcular', 'data'),
        Input('initial-load-interval', 'n_intervals'),
        Input('dummy-initial-load', 'children'),
        prevent_initial_call=True
    )
    def update_calculated_values(*args):
        try:
            df = pd.DataFrame()
            transacoes = get_transactions()
            encerradas = get_encerradas()
            if transacoes is not None and not transacoes.empty:
                df = pd.concat([df, transacoes], ignore_index=True)
            if encerradas is not None and not encerradas.empty:
                df = pd.concat([df, encerradas], ignore_index=True)

            if df.empty:
                return ["R$ 0,00"] * 6 + [""]

            # Converte valores
            df['VALOR OPERAÇÃO'] = pd.to_numeric(df['VALOR OPERAÇÃO'], errors='coerce').fillna(0)
                        
            # Usa as colunas separadas que já vêm do banco!
            compra_call = df[(df['OPERAÇÃO'] == 'Call') & (df['VALOR OPERAÇÃO'] < 0)]['VALOR OPERAÇÃO'].sum()
            venda_call  = df[(df['OPERAÇÃO'] == 'Call') & (df['VALOR OPERAÇÃO'] > 0)]['VALOR OPERAÇÃO'].sum()
            compra_put  = df[(df['OPERAÇÃO'] == 'Put')  & (df['VALOR OPERAÇÃO'] < 0)]['VALOR OPERAÇÃO'].sum()
            venda_put   = df[(df['OPERAÇÃO'] == 'Put')  & (df['VALOR OPERAÇÃO'] > 0)]['VALOR OPERAÇÃO'].sum()

            gp_estrutura = df[df['ESTRUTURA'].notna() & (df['ESTRUTURA'] != '')]['VALOR OPERAÇÃO'].sum()
            gp_simples   = df[(df['ESTRUTURA'].isna()) | (df['ESTRUTURA'] == '')]['VALOR OPERAÇÃO'].sum()

            return [
                fmt_br(compra_call),
                fmt_br(venda_call),
                fmt_br(compra_put),
                fmt_br(venda_put),
                fmt_br(gp_estrutura),
                fmt_br(gp_simples),
                ""
            ]
        except Exception as e:
            logging.error(f"[CARDS] Erro: {e}")
            return ["R$ 0,00", "R$ 0,00", "R$ 0,00", "R$ 0,00", "R$ 0,00", "R$ 0,00", ""]

    # 10º Callback clear messages

    @callback(
        [Output('output-recalcular', 'children', allow_duplicate=True),
         Output('message-clear-interval', 'disabled')],
        Input('message-clear-interval', 'n_intervals'),
        State('output-recalcular', 'children'),
        prevent_initial_call=True
    )
    def clear_messages(n_intervals, current_message):
        if n_intervals > 0 and current_message:
            logging.info("[CLEAR] Limpando mensagem")
            return ['', True]
        return ['', True]

    # 11º Callback - update_g_p_values (CORRIGIDO)
    @callback(
        Output('g_p-estrutura-value', 'children'),
        Output('g_p-simples-value', 'children'),
        Output('output-recalcular', 'children', allow_duplicate=True),
        Output('initial-load-interval', 'disabled'),
        Input('table-update-trigger-nova', 'children'),
        Input('table-update-trigger-alterar', 'children'),
        Input('recalcular-btn', 'n_clicks'),
        Input('initial-load-interval', 'n_intervals'),
        Input('theme-switch', 'value'),
        Input('init-table-trigger', 'data'),
        Input('dummy-initial-load', 'children'),  # ← mantido só para não dar erro
        prevent_initial_call=True
    )
    def update_g_p_values(trigger_nova, trigger_alterar, recalcular_clicks, n_intervals, theme_switch, init_trigger, dummy_initial):
        # ← agora tem 7 parâmetros (o último é dummy_initial, mas não usamos)
        try:
            if not check_table_exists('encerradas'):
                init_database()
                return ["R$ 0,00", "R$ 0,00", html.Div("Banco inicializado", style={'color': '#FF0000'}), True]

            encerradas = get_encerradas()
            if encerradas is None or encerradas.empty:
                return ["R$ 0,00", "R$ 0,00", "", True]

            # Converte quantidade se necessário
            def safe_float(x):
                try:
                    return float(x)
                except:
                    return 0.0
            encerradas['g_p'] = pd.to_numeric(encerradas['g_p'], errors='coerce').fillna(0)

            g_p_estrutura = encerradas[encerradas['estrutura'].notna() & (encerradas['estrutura'] != '')]['g_p'].sum()
            g_p_simples = encerradas[(encerradas['estrutura'].isna()) | (encerradas['estrutura'] == '')]['g_p'].sum()

            def fmt(val):
                val = round(float(val), 2)
                return f"-R$ {abs(val):,.2f}".replace('.', ',') if val < 0 else f"R$ {val:,.2f}".replace('.', ',')

            return [
                html.Span(fmt(g_p_estrutura), style={'color': '#28a745' if g_p_estrutura >= 0 else '#dc3545'}),
                html.Span(fmt(g_p_simples), style={'color': '#28a745' if g_p_simples >= 0 else '#dc3545'}),
                '',
                True
            ]

        except Exception as e:
            logging.error(f"[G/P] Erro: {e}")
            return ["R$ 0,00", "R$ 0,00", html.Div(f"Erro: {str(e)}", style={'color': '#FF0000'}), True]

    # 12º Callback - ENCERRAR OPERAÇÃO

    @callback(
        [Output('modal-encerrar-operacao', 'is_open'),
        Output('encerrar-ticker', 'value'),
        Output('encerrar-operacao', 'value'),
        Output('encerrar-direcao', 'value'),
        Output('encerrar-quantidade', 'value'),
        Output('encerrar-valor-opcao', 'value'),
        Output('encerrar-data-op', 'value'),
        Output('valor-encerr', 'value'),
        Output('data-encerr', 'value'),
        Output('rolagem', 'value'),
        Output('encerrar-ticker-val', 'children'),
        Output('encerrar-operacao-val', 'children'),
        Output('encerrar-direcao-val', 'children'),
        Output('encerrar-quantidade-val', 'children'),
        Output('encerrar-valor-opcao-val', 'children'),
        Output('encerrar-data-op-val', 'children'),
        Output('valor-encerr-val', 'children'),
        Output('data-encerr-val', 'children'),
        Output('rolagem-val', 'children'),
        Output('modal-encerrar-mensagem', 'children'),
        Output('tabela-operacoes', 'data', allow_duplicate=True),
        Output('trigger-recalcular', 'data')],  # ← 22º output
        [Input('encerrar-operacao-btn', 'n_clicks'),
        Input('confirmar-encerr-btn', 'n_clicks'),
        Input('cancelar-encerr-btn', 'n_clicks'),
        Input('voltar-encerr-btn', 'n_clicks'),
        Input('valor-encerr', 'value'),
        Input('data-encerr', 'value'),
        Input('rolagem', 'value'),
        Input('encerrar-quantidade', 'value')],
        [State('tabela-operacoes', 'active_cell'),
        State('tabela-operacoes', 'data'),
        State('modal-encerrar-operacao', 'is_open'),
        State('selected-row', 'data'),
        State('trigger-recalcular', 'data')],
        prevent_initial_call=True
    )
    def encerrar_operacao(n_clicks, confirmar_click, cancelar_click, voltar_click, valor_encerr, data_encerr, rolagem, qtd,
                        active_cell, table_data, is_open, selected_row, trigger):
        trigger_id = ctx.triggered_id
        logging.info(f"[ENCERRAR] Trigger: {trigger_id}, Active Cell: {active_cell}, Selected Row: {selected_row}")

        # CANCELAR / VOLTAR
        if trigger_id in ['cancelar-encerr-btn', 'voltar-encerr-btn']:
            return [False, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', table_data, dash.no_update]

        # ABRIR MODAL
        if trigger_id == 'encerrar-operacao-btn' and not is_open:
            if not table_data:
                return [True, '', '', '', '', '', '', '', datetime.now().strftime('%d/%m/%Y'), '', 
                        html.Span('×', className='validation-error'), html.Span('×', className='validation-error'),
                        html.Span('×', className='validation-error'), '', '', '', '', '', '', '❌ Tabela vazia', table_data, dash.no_update]

            row = selected_row if selected_row and 'TICKER' in selected_row else \
                table_data[active_cell['row']] if active_cell and active_cell['row'] < len(table_data) else None

            if not row:
                return [True, '', '', '', '', '', '', '', datetime.now().strftime('%d/%m/%Y'), '',
                        html.Span('×', className='validation-error'), html.Span('×', className='validation-error'),
                        html.Span('×', className='validation-error'), '', '', '', '', '', '', '❌ Selecione uma linha', table_data, dash.no_update]

            op_dir = row['OPERAÇÃO/DIREÇÃO'].split('/')
            quantidade = str(row['QUANTIDADE'])
            valor_opcao = row['VALOR OPÇÃO'].replace('R$ ', '').replace(',', '.')
            direcao_oposta = 'Compra' if op_dir[1] == 'Venda' else 'Venda'

            return [True, row['TICKER'], op_dir[0], direcao_oposta, quantidade, valor_opcao, row['DATA OP'],
                    '', datetime.now().strftime('%d/%m/%Y'), '',
                    html.Span('✔', className='validation-ok'), html.Span('✔', className='validation-ok'),
                    html.Span('✔', className='validation-ok'), '', '', '', '', '', '', '', table_data, dash.no_update]

        # VALIDAÇÃO EM TEMPO REAL
        if is_open and trigger_id in ['valor-encerr', 'data-encerr', 'rolagem', 'encerrar-quantidade']:
            val_qtd = html.Span('✔', className='validation-ok') if validate_numeric_positive(qtd, 'qtd') else html.Span('×', className='validation-error')
            val_valor = html.Span('✔', className='validation-ok') if validate_numeric_positive(valor_encerr, 'valor_encerr') else html.Span('×', className='validation-error')
            val_data = html.Span('✔', className='validation-ok') if validate_date(data_encerr) else html.Span('×', className='validation-error')
            val_rolagem = html.Span('✔', className='validation-ok') if rolagem else ''

            return [dash.no_update] * 7 + [valor_encerr or '', data_encerr or '', rolagem or ''] + [
                dash.no_update, dash.no_update, dash.no_update, val_qtd, dash.no_update, dash.no_update,
                val_valor, val_data, val_rolagem, '', dash.no_update, dash.no_update]

        # CONFIRMAR ENCERRAMENTO
        if trigger_id == 'confirmar-encerr-btn' and is_open:
            row = selected_row if selected_row else table_data[active_cell['row']] if active_cell else None
            if not row:
                return [dash.no_update] * 20 + ['❌ Linha não selecionada', table_data, dash.no_update]

            if not all([qtd, valor_encerr, data_encerr]):
                return [dash.no_update] * 20 + ['❌ Preencha todos os campos', table_data, dash.no_update]

            try:
                qtd_final = float(qtd)
                valor_encerr_final = float(valor_encerr)
                direcao_oposta = 'Compra' if row['OPERAÇÃO/DIREÇÃO'].split('/')[1] == 'Venda' else 'Venda'
                valor_oper = calculate_operation_value(qtd_final, valor_encerr_final, direcao_oposta)
                strike = row['STRIKE'].replace('R$ ', '').replace(',', '.')

                with sqlite3.connect('transacoes.db') as conn:
                    c = conn.cursor()
                    # Busca ID
                    c.execute("SELECT id FROM transacoes WHERE ticker=? AND data_op=? AND data_exerc=?", 
                            (row['TICKER'], row['DATA OP'], row['DATA EXERC']))
                    row_id = c.fetchone()
                    if not row_id:
                        return [dash.no_update] * 20 + ['❌ Operação não encontrada', table_data, dash.no_update]

                    # Insere em encerradas
                    c.execute("""INSERT INTO encerradas 
                                (id_origem, ticker, operacao, direcao, strike, quantidade, valor_opcao, valor_operacao,
                                data_op, data_exerc, estrutura, rolagem, data_encerr, valor_encerr, valor_oper_encerr)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (row_id[0], row['TICKER'], row['OPERAÇÃO/DIREÇÃO'].split('/')[0], direcao_oposta,
                            strike, qtd_final, valor_encerr_final, valor_oper, row['DATA OP'], row['DATA EXERC'],
                            row['ESTRUTURA'], rolagem, data_encerr, valor_encerr_final, valor_oper))
                    # Remove da principal
                    c.execute("DELETE FROM transacoes WHERE id=?", (row_id[0],))
                    conn.commit()

                # Atualiza tabela
                updated_data = [r for r in table_data if r['TICKER'] != row['TICKER'] or r['DATA OP'] != row['DATA OP']]
                return [False, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '✅ Encerrado!', updated_data, trigger + 1]

            except Exception as e:
                logging.error(f"[ENCERRAR] Erro: {e}")
                return [dash.no_update] * 20 + [f'❌ {str(e)}', table_data, dash.no_update]

        return [dash.no_update] * 22

    # 13º CALLBACK ATUALIZAÇÃO TABELA

    @callback(
        Output('table-update-trigger-alterar', 'children', allow_duplicate=True),
        [Input('confirmar-alter-btn', 'n_clicks'),
        Input('confirmar-encerr-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def update_table_trigger(alterar_click, encerrar_click):
        trigger_id = ctx.triggered_id if ctx.triggered else None
        logging.info(f"[TABLE_UPDATE] Trigger: {trigger_id}")
        return str(datetime.now())

    # 14º CALLBACK DEPURAÇÃO SELEÇÃO

    @callback(
        Output('selected-row', 'data', allow_duplicate=True),
        [Input('tabela-operacoes', 'active_cell')],
        [State('tabela-operacoes', 'data')],
        prevent_initial_call=True
    )
    def update_selected_row(active_cell, table_data):
        logging.info(f"[SELEÇÃO] Active Cell: {active_cell}")
        if active_cell and table_data and active_cell['row'] < len(table_data):
            row = table_data[active_cell['row']]
            logging.info(f"[SELEÇÃO] Linha selecionada: {row}")
            return row
        logging.info("[SELEÇÃO] Nenhuma linha selecionada")
        return {}

        # 15º CALLBACK - ATUALIZAR COTAÇÕES (VERSÃO FINAL OFICIAL 26/11/2025 — 100% FUNCIONAL)
    @callback(
        Output('tabela-operacoes', 'data', allow_duplicate=True),
        Output('tabela-operacoes', 'tooltip_data', allow_duplicate=True),
        Input('atualizar-cotacoes-btn', 'n_clicks'),
        State('tabela-operacoes', 'data'),
        prevent_initial_call=True
    )
    def atualizar_cotacoes_yahoo(n_clicks, data_atual):
        if not n_clicks or not data_atual:
            return dash.no_update, dash.no_update

        df = pd.DataFrame(data_atual)
        tooltip_data = [{col: {'value': '', 'type': 'text'} for col in df.columns} for _ in range(len(df))]

        for i, row in df.iterrows():
            try:
                base = row['TICKER'][:4]  # BBAS
                strike_raw = row['STRIKE']
                strike = float(strike_raw.replace('R$', '').replace('.', '').replace(',', '.').strip())
                data_exerc_str = row['DATA EXERC']
                operacao = row['OPERAÇÃO/DIREÇÃO'].split('/')[0].strip()

                # Calcula timestamp Unix para o vencimento (Yahoo usa isso)
                vencimento = pd.to_datetime(data_exerc_str, format='%d/%m/%Y', dayfirst=True)
                timestamp = int(vencimento.timestamp())

                # URL do Yahoo para opções
                url = f"https://finance.yahoo.com/quote/{base}.SA/options?date={timestamp}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }

                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    df.at[i, 'VALOR ATUAL'] = "N/D"
                    tooltip_data[i]['VALOR ATUAL'] = {'value': "Erro HTTP", 'type': 'markdown'}
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', class_='W(100%) M(0)')
                if not table:
                    df.at[i, 'VALOR ATUAL'] = "N/D"
                    tooltip_data[i]['VALOR ATUAL'] = {'value': "Tabela não encontrada", 'type': 'markdown'}
                    continue

                rows = table.find_all('tr')[1:]  # Pula header
                for r in rows:
                    cells = r.find_all('td')
                    if len(cells) >= 2:
                        strike_cell = re.sub(r'[^\d.,]', '', cells[2].text.strip())  # Limpa strike
                        strike_cell = float(strike_cell.replace('.', '').replace(',', '.'))
                        last_price = cells[1].text.strip()  # Last Price
                        if abs(strike_cell - strike) < 0.01:
                            valor = float(last_price) if last_price != '-' and last_price != 'N/A' else None
                            valor_fmt = fmt_br(valor, casas=4) if valor else "N/D"
                            df.at[i, 'VALOR ATUAL'] = valor_fmt
                            tooltip_data[i]['VALOR ATUAL'] = {'value': f"Última: {valor_fmt}\nFonte: Yahoo Finance", 'type': 'markdown'}
                            break

                if df.at[i, 'VALOR ATUAL'] == '':  # Se não encontrou
                    df.at[i, 'VALOR ATUAL'] = "N/D"
                    tooltip_data[i]['VALOR ATUAL'] = {'value': "Strike não encontrado", 'type': 'markdown'}

            except Exception as e:
                logging.warning(f"[YAHOO] Erro {row['TICKER']}: {e}")
                df.at[i, 'VALOR ATUAL'] = "Erro"
                tooltip_data[i]['VALOR ATUAL'] = {'value': "Erro scraping", 'type': 'markdown'}

        return df.to_dict('records'), tooltip_data
    # GARANTE QUE SÓ UMA LINHA FIQUE SELECIONADA (mesmo com multi)
    @callback(
        Output('selected-row', 'data'),
        Input('tabela-operacoes', 'selected_rows'),
        State('tabela-operacoes', 'data')
    )
    def update_selected_row(selected_rows, table_data):
        if selected_rows and table_data:
            row_index = seleted_rows[0]
            return table_data[row_index]
        return None