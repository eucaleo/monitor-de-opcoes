# app_layout.py
import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from datetime import date, timedelta, datetime as dt_now

from database import init_database

#init_database()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
server = app.server

app.layout = dbc.Container([
    html.H1("Monitor de Opções", className="text-center my-4"),

    dbc.Row([
        dbc.Col(dbc.Switch(id='theme-switch', label='Dark Mode', value=False), width=2)
    ], className="mb-3", justify="end"),

    dbc.Row([
        dbc.Col([
            html.Label("Período", className="form-label mb-1"),
            dcc.DatePickerRange(
                id='periodo-date-range',
                start_date=date.today() - timedelta(days=90),
                end_date=date.today(),
                display_format='DD/MM/YYYY',
                first_day_of_week=1,
                clearable=True,
                className="form-control form-control-sm",
                style={"height": "38px", "borderRadius": "6px"}
            )
        ], width=3),

        dbc.Col(dbc.Button("Nova", id="nova-operacao-btn", color='success', size="sm"), width=1),
        dbc.Col(dbc.Button("Alterar", id="alterar-operacao-btn", color='primary', size="sm"), width=1),
        dbc.Col(dbc.Button("Encerrar", id="encerrar-operacao-btn", color='warning', size="sm"), width=1),
        dbc.Col(dbc.Button("Recalcular", id="recalcular-btn", color='info', size="sm"), width=1),
        dbc.Col(dbc.Button("Exportar", id="export-btn", color='secondary', size="sm"), width=1),
        dbc.Col(dbc.Button("Atualizar Cotações", id="atualizar-cotacoes-btn", color='info', size="sm"), width=2),
    ], className="g-2 mb-4", justify="center", align="center"),

    dbc.Row([
        dbc.Col([html.Small("Compra Call", className="text-muted text-center d-block mb-1"),
                 html.Div(id='compra-call-value', className="card p-2 text-center fw-bold", style={'fontSize': '14px'})], width=1),
        dbc.Col([html.Small("Venda Call", className="text-muted text-center d-block mb-1"),
                 html.Div(id='venda-call-value', className="card p-2 text-center fw-bold", style={'fontSize': '14px'})], width=1),
        dbc.Col([html.Small("Compra Put", className="text-muted text-center d-block mb-1"),
                 html.Div(id='compra-put-value', className="card p-2 text-center fw-bold", style={'fontSize': '14px'})], width=1),
        dbc.Col([html.Small("Venda Put", className="text-muted text-center d-block mb-1"),
                 html.Div(id='venda-put-value', className="card p-2 text-center fw-bold", style={'fontSize': '14px'})], width=1),
        dbc.Col([html.Small("G/P Estruturas", className="text-muted text-center d-block mb-1"),
                 html.Div(id='g_p-estrutura-value', className="card p-2 text-center fw-bold", style={'fontSize': '14px'})], width=2),
        dbc.Col([html.Small("G/P Simples", className="text-muted text-center d-block mb-1"),
                 html.Div(id='g_p-simples-value', className="card p-2 text-center fw-bold", style={'fontSize': '14px'})], width=2),
    ], className="g-3 mb-3", justify="center"),

    dbc.Row([
        dbc.Col([html.Small("Fluxo (período)", className="text-muted text-center d-block mb-1"),
                 html.Div(id='fluxo-periodo-value', className="card p-2 text-center fw-bold", style={'fontSize': '14px'})], width=2),
        dbc.Col([html.Small("Posição Aberta (agora)", className="text-muted text-center d-block mb-1"),
                 html.Div(id='posicao-aberta-value', className="card p-2 text-center fw-bold", style={'fontSize': '14px'})], width=2),
    ], className="g-3 mb-4", justify="center"),

    dbc.Row([
        dbc.Col(dbc.Input(id='busca-ticker', type='text', placeholder='Buscar Ticker', className="form-control form-control-sm"), width=2),
        dbc.Col(dcc.Dropdown(
            id='export-format',
            options=[{'label': 'Excel', 'value': 'excel'}, {'label': 'CSV', 'value': 'csv'}],
            value='excel',
            clearable=False
        ), width=2),
        dbc.Col(html.Div(id='output-recalcular', className="text-danger text-center"), width=3)
    ], justify="center", className="mb-3"),

    dbc.Row([
        dbc.Col(dash_table.DataTable(
            id='tabela-operacoes',
            columns=[
                {'name': 'id', 'id': 'id'},
                {'name': 'TICKER', 'id': 'TICKER'},
                {'name': 'OPERAÇÃO', 'id': 'OPERAÇÃO'},
                {'name': 'DIREÇÃO', 'id': 'DIREÇÃO'},
                {'name': 'STRIKE', 'id': 'STRIKE'},
                {'name': 'QUANTIDADE', 'id': 'QUANTIDADE'},
                {'name': 'VALOR OPÇÃO', 'id': 'VALOR OPÇÃO'},
                {'name': 'VALOR OPERAÇÃO', 'id': 'VALOR OPERAÇÃO'},
                {'name': 'VALOR ATUAL', 'id': 'VALOR ATUAL'},
                {'name': 'DATA OP', 'id': 'DATA OP'},
                {'name': 'DATA EXERC', 'id': 'DATA EXERC'},
                {'name': 'ESTRUTURA', 'id': 'ESTRUTURA'},
                {'name': 'ROLAGEM', 'id': 'ROLAGEM'}
            ],
            hidden_columns=['id'],
            style_table={'overflowY': 'auto', 'height': '330px'},
            fixed_rows={'headers': True},
            style_cell={'textAlign': 'center', 'padding': '5px', 'fontSize': '13px'},
            style_header={'backgroundColor': 'rgb(230, 240, 250)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
                {'if': {'state': 'selected'}, 'backgroundColor': '#007bff', 'color': 'white', 'fontWeight': 'bold'}
            ],
            page_size=10,
            sort_action='native',
            row_selectable='single',
            selected_rows=[],
            persistence=True,
            persistence_type='session'
        ), width=12)
    ]),

    # Stores
    dcc.Store(id='selected-row-id', data=None),
    dcc.Store(id='table-refresh-seq', data=0),
    dcc.Store(id='focus-ticker-pulse', data=0),  # para clientside focus

    # Modal de Nova Operação
    dbc.Modal(
        [
            dbc.ModalHeader("Nova Operação", close_button=True),
            dbc.ModalBody([
                dbc.Form(className="form-group", style={'padding': '15px'}, children=[
                    dbc.Row([
                        dbc.Col(html.Label("TICKER", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-ticker', type='text', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-ticker-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("OPERAÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Dropdown(
                            id='nova-operacao',
                            options=[{'label': 'Call', 'value': 'Call'}, {'label': 'Put', 'value': 'Put'}],
                            disabled=False,
                            clearable=False,
                            className="form-control",
                            style={'fontWeight': 'bold'}
                        ), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-operacao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DIREÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Dropdown(
                            id='nova-direcao',
                            options=[{'label': 'Compra', 'value': 'Compra'}, {'label': 'Venda', 'value': 'Venda'}],
                            className="form-control",
                            value=None  # inicia em branco (usuário escolhe)
                        ), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-direcao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("STRIKE", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-strike', type='number', step=0.0001, className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-strike-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("QUANTIDADE", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-quantidade', type='number', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-quantidade-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("VALOR OPÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-valor-opcao', type='number', step=0.0001, className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-valor-opcao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DATA OP", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-data-op', placeholder="DD/MM/YYYY", type='text', className="form-control", value=dt_now.now().strftime('%d/%m/%Y')), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-data-op-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DATA EXERC", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-data-exerc', placeholder="DD/MM/YYYY", type='text', className="form-control", readOnly=True), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-data-exerc-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("ESTRUTURA", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-estrutura', type='text', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-estrutura-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("ROLAGEM", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-rolagem', type='text', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-rolagem-val', className='validation-col text-center'), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                ]),
                html.Div(id='modal-nova-mensagem', style={'color': 'red', 'textAlign': 'center', 'marginTop': '10px'}),
            ]),
            dbc.ModalFooter([
                dbc.Button("Confirmar Nova", id="confirmar-nova-btn", color='success', className='me-2'),
                dbc.Button("Cancelar", id="cancelar-nova-btn", color='secondary', className='me-2'),
                dbc.Button("Voltar", id="voltar-nova-btn", color='secondary'),
            ]),
        ],
        id='modal-nova-operacao',
        is_open=False,
        size="md",
    ),

    # Modal Alterar Operação
    dbc.Modal(
        [
            dbc.ModalHeader("Alterar Operação", close_button=True),
            dbc.ModalBody([
                dbc.Form(className="form-group", style={'padding': '15px'}, children=[
                    dbc.Row([
                        dbc.Col(html.Label("TICKER", className="label"), width=4),
                        dbc.Col(html.Span(id='alterar-ticker', className="form-control readonly-display"), width=6),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Col(html.Label("OPERAÇÃO", className="label"), width=4),
                        dbc.Col(html.Span(id='alterar-operacao', className="form-control readonly-display"), width=6),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Col(html.Label("DIREÇÃO", className="label"), width=4),
                        dbc.Col(html.Span(id='alterar-direcao', className="form-control readonly-display"), width=6),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Col(html.Label("QUANTIDADE", className="label"), width=4),
                        dbc.Col(dcc.Input(id='alterar-quantidade', type='number', className="form-control"), width=6),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Col(html.Label("VALOR OPÇÃO (abertura)", className="label"), width=4),
                        dbc.Col(html.Span(id='alterar-valor-opcao', className="form-control readonly-display"), width=6),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Col(html.Label("DATA OP (abertura)", className="label"), width=4),
                        dbc.Col(html.Span(id='alterar-data-op', className="form-control readonly-display"), width=6),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Col(html.Label("DATA EXERC", className="label"), width=4),
                        dbc.Col(html.Span(id='alterar-data-exerc', className="form-control readonly-display"), width=6),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Col(html.Label("ESTRUTURA", className="label"), width=4),
                        dbc.Col(dcc.Input(id='alterar-estrutura', type='text', className="form-control"), width=6),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Col(html.Label("ROLAGEM", className="label"), width=4),
                        dbc.Col(dcc.Input(id='alterar-rolagem', type='text', className="form-control"), width=6),
                    ]),
                    html.Hr(),
                    dbc.Row([dbc.Col(html.Div(id='modal-alterar-mensagem', className="alert alert-info"), width=12)])
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Confirmar", id='confirmar-alter-btn', color='success'),
                dbc.Button("Cancelar", id='cancelar-alter-btn', color='secondary'),
            ])
        ],
        id='modal-alterar-operacao',
        is_open=False,
        size="md",
    ),

    # Modal Encerrar Operação
    dbc.Modal(
        [
            dbc.ModalHeader("Encerrar Operação", close_button=True),
            dbc.ModalBody([
                dbc.Form(className="form-group", style={'padding': '15px'}, children=[
                    dbc.Row([
                        dbc.Col(html.Label("TICKER", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='encerrar-ticker', type='text', className="form-control", readOnly=True), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='encerrar-ticker-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("OPERAÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='encerrar-operacao', type='text', className="form-control", readOnly=True), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='encerrar-operacao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DIREÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='encerrar-direcao', type='text', className="form-control", readOnly=True), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='encerrar-direcao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("QUANTIDADE", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='encerrar-quantidade', type='number', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='encerrar-quantidade-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("VALOR OPÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='encerrar-valor-opcao', type='number', step=0.01, className="form-control", readOnly=True), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='encerrar-valor-opcao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DATA OP", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='encerrar-data-op', type='text', className="form-control", readOnly=True), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='encerrar-data-op-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("VALOR ENCERRAMENTO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='valor-encerr', type='number', step=0.01, className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='valor-encerr-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DATA ENCERRAMENTO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='data-encerr', placeholder="DD/MM/YYYY", type='text', className="form-control", value=dt_now.now().strftime('%d/%m/%Y')), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='data-encerr-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("ROLAGEM", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='rolagem', type='text', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='rolagem-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                                        dbc.Row([
                        dbc.Col(html.Label("MOTIVO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Dropdown(
                            id='motivo-encerr',
                            options=[
                                {'label': 'Target', 'value': 'target'},
                                {'label': 'Stop', 'value': 'stop'},
                                {'label': 'Rolagem', 'value': 'rolagem'},
                                {'label': 'Margem', 'value': 'margem'},
                                {'label': 'Outro', 'value': 'outro'},
                            ],
                            placeholder="(opcional)",
                            clearable=True,
                            className="form-control"
                        ), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='motivo-encerr-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),

                    html.Div(id='modal-encerrar-mensagem', style={'color': 'red', 'textAlign': 'center', 'marginTop': '10px'}),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Confirmar Encerramento", id="confirmar-encerr-btn", color='danger', className='me-2'),
                dbc.Button("Cancelar", id="cancelar-encerr-btn", color='secondary', className='me-2'),
                dbc.Button("Voltar", id="voltar-encerr-btn", color='secondary'),
            ]),
        ],
        id='modal-encerrar-operacao',
        is_open=False,
        size="md",
    ),
    # === Relatórios: Sintético e Analítico ===
    html.Hr(className="my-4"),
    html.H2("Relatórios", className="text-center my-3"),

    dbc.Tabs(id="rel-tabs", active_tab="tab-sint", children=[
        dbc.Tab(label="Sintético", tab_id="tab-sint", children=[
            dbc.Row([
                dbc.Col([
                    html.Label("Período (Encerradas)", className="form-label mb-1"),
                    dcc.DatePickerRange(
                        id='e-date-range',
                        start_date=date.today().replace(day=1),
                        end_date=date.today(),
                        display_format='DD/MM/YYYY',
                        first_day_of_week=1,
                        clearable=True,
                        className="form-control form-control-sm",
                        style={"height": "38px", "borderRadius": "6px"}
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Tipo", className="form-label mb-1"),
                    dcc.Dropdown(
                        id="e-tipo",
                        options=[{"label": "Todos", "value": ""}, {"label": "Simples", "value": "Simples"}, {"label": "Estrutura", "value": "Estrutura"}],
                        value="",
                        clearable=False
                    )
                ], width=2),
                dbc.Col([
                    html.Label("Estrutura", className="form-label mb-1"),
                    dcc.Dropdown(id="e-estrutura", options=[], value="", placeholder="Todas", clearable=True)
                ], width=3),
                dbc.Col([
                    html.Label("Bundle", className="form-label mb-1"),
                    dcc.Dropdown(id="e-bundle", options=[], value="", placeholder="Todos", clearable=True)
                ], width=2),
                dbc.Col([
                    html.Label("Ticker", className="form-label mb-1"),
                    dcc.Input(id="e-ticker", type="text", placeholder="Filtro", className="form-control form-control-sm")
                ], width=2),
            ], className="g-2 mb-3", justify="center"),

            dbc.Row([
                dbc.Col([html.Small("G/P Realizado (R$)", className="text-muted d-block text-center mb-1"),
                         html.Div(id="kpi-gp-real", className="card p-2 text-center fw-bold")], width=2),
                dbc.Col([html.Small("Nº Encerramentos", className="text-muted d-block text-center mb-1"),
                         html.Div(id="kpi-n-enc", className="card p-2 text-center fw-bold")], width=2),
                dbc.Col([html.Small("Ticket Médio (R$/enc)", className="text-muted d-block text-center mb-1"),
                         html.Div(id="kpi-ticket", className="card p-2 text-center fw-bold")], width=2),
                dbc.Col([html.Small("% Positivos", className="text-muted d-block text-center mb-1"),
                         html.Div(id="kpi-hit", className="card p-2 text-center fw-bold")], width=2),
                dbc.Col([html.Small("Melhor/Pior", className="text-muted d-block text-center mb-1"),
                         html.Div(id="kpi-topbot", className="card p-2 text-center fw-bold")], width=4),
            ], className="g-2 mb-3", justify="center"),

            dbc.Row([
                dbc.Col(dcc.Graph(id="graf-gp-mensal", config={"displayModeBar": False}), width=6),
                dbc.Col(dcc.Graph(id="graf-simples-vs-estrutura", config={"displayModeBar": False}), width=6),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    html.H5("Estruturas/Bundles (G/P e Nº Encerr.)", className="mb-2"),
                    dash_table.DataTable(
                        id="sint-table",
                        columns=[
                            {"name": "Estrutura", "id": "ESTRUTURA"},
                            {"name": "Bundle", "id": "BUNDLE"},
                            {"name": "G/P (R$)", "id": "GP"},
                            {"name": "Encerramentos", "id": "N_ENC"}
                        ],
                        style_table={"overflowY": "auto", "height": "260px"},
                        style_cell={'textAlign': 'center', 'padding': '5px', 'fontSize': '13px'},
                        style_header={'backgroundColor': 'rgb(230, 240, 250)', 'fontWeight': 'bold'},
                        page_size=10
                    ),
                ], width=8),
                dbc.Col([
                    html.H5("Top 10 Ganhos/Perdas", className="mb-2"),
                    dash_table.DataTable(
                        id="sint-top10",
                        columns=[
                            {"name": "ID Enc.", "id": "ID_ENC"},
                            {"name": "Ticker", "id": "TICKER"},
                            {"name": "Estrutura", "id": "ESTRUTURA"},
                            {"name": "G/P (R$)", "id": "GP"}
                        ],
                        style_table={"overflowY": "auto", "height": "260px"},
                        style_cell={'textAlign': 'center', 'padding': '5px', 'fontSize': '13px'},
                        style_header={'backgroundColor': 'rgb(230, 240, 250)', 'fontWeight': 'bold'},
                        page_size=10
                    ),
                    dbc.Button("Exportar Sintético", id="export-sint-btn", color="secondary", size="sm", className="mt-2"),
                    dcc.Download(id="download-sint"),
                ], width=4),
            ])
        ]),
        dbc.Tab(label="Analítico", tab_id="tab-analit", children=[
            dbc.Row([
                dbc.Col([
                    html.Label("Período (Encerradas)", className="form-label mb-1"),
                    dcc.DatePickerRange(
                        id='a-date-range',
                        start_date=date.today().replace(day=1),
                        end_date=date.today(),
                        display_format='DD/MM/YYYY',
                        first_day_of_week=1,
                        clearable=True,
                        className="form-control form-control-sm",
                        style={"height": "38px", "borderRadius": "6px"}
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Tipo", className="form-label mb-1"),
                    dcc.Dropdown(
                        id="a-tipo",
                        options=[{"label": "Todos", "value": ""}, {"label": "Simples", "value": "Simples"}, {"label": "Estrutura", "value": "Estrutura"}],
                        value="",
                        clearable=False
                    )
                ], width=2),
                dbc.Col([
                    html.Label("Estrutura", className="form-label mb-1"),
                    dcc.Dropdown(id="a-estrutura", options=[], value="", placeholder="Todas", clearable=True)
                ], width=3),
                dbc.Col([
                    html.Label("Bundle", className="form-label mb-1"),
                    dcc.Dropdown(id="a-bundle", options=[], value="", placeholder="Todos", clearable=True)
                ], width=2),
                dbc.Col([
                    html.Label("Visão", className="form-label mb-1"),
                    dcc.RadioItems(
                        id="a-view-mode",
                        options=[{"label": "Linhas", "value": "linhas"}, {"label": "Grupos", "value": "grupos"}],
                        value="linhas",
                        inline=True
                    )
                ], width=2),
            ], className="g-2 mb-3", justify="center"),

            dash_table.DataTable(
                id="analitico-table",
                columns=[
                    {"name": "ID Enc.", "id": "ID_ENC"},
                    {"name": "ID Origem", "id": "ID_ORIGEM"},
                    {"name": "Ticker", "id": "TICKER"},
                    {"name": "Operação", "id": "OPERACAO"},
                    {"name": "Direção", "id": "DIRECAO"},
                    {"name": "Estrutura", "id": "ESTRUTURA"},
                    {"name": "Bundle", "id": "BUNDLE"},
                    {"name": "Perna", "id": "PERNA"},
                    {"name": "Rolagem", "id": "ROLAGEM"},
                    {"name": "Qtd Enc.", "id": "QTD_ENC"},
                    {"name": "Preço Abert.", "id": "PRECO_ABERT"},
                    {"name": "Preço Enc.", "id": "PRECO_ENC"},
                    {"name": "CF Abert.", "id": "CF_ABERT"},
                    {"name": "CF Enc.", "id": "CF_ENC"},
                    {"name": "G/P (R$)", "id": "GP"},
                    {"name": "% Ret", "id": "RET_PCT"},
                    {"name": "Data OP", "id": "DATA_OP"},
                    {"name": "Data Enc.", "id": "DATA_ENC"},
                    {"name": "Dias", "id": "DIAS_POS"},
                    {"name": "Motivo", "id": "MOTIVO"},
                ],
                style_table={"overflowY": "auto", "height": "420px"},
                style_cell={'textAlign': 'center', 'padding': '5px', 'fontSize': '13px'},
                style_header={'backgroundColor': 'rgb(230, 240, 250)', 'fontWeight': 'bold'},
                page_size=15
            ),

            dbc.Button("Exportar Analítico", id="export-analit-btn", color="secondary", size="sm", className="mt-2"),
            dcc.Download(id="download-analit"),
        ]),
    ]),

], fluid=True, className="px-4")

# Registra callbacks
from app_callbacks import register_callbacks
register_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True)
