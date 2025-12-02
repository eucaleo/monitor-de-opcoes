import dash
from dash import Dash, html, dcc, dash_table, Input, Output, State
from datetime import date, timedelta, datetime as dt_now
import dash_bootstrap_components as dbc
import logging
from logging.handlers import RotatingFileHandler

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('gizmo.log', maxBytes=1000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# App
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    external_scripts=['/assets/clientside.js'],
    suppress_callback_exceptions=True
)

app.layout = dbc.Container([
    html.H1("Monitor de Opções", className="text-center my-4"),

    # Switch Dark Mode
    dbc.Row([
        dbc.Col(dbc.Switch(id='theme-switch', label='Dark Mode', value=False), width=2)
    ], className="mb-3", justify="end"),

    # DatePickerRange + Botões
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

    # Cards
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
    ], className="g-3 mb-4", justify="center"),

    # Busca + Export
    dbc.Row([
        dbc.Col(dbc.Input(id='busca-ticker', type='text', placeholder='Buscar Ticker', className="form-control form-control-sm"), width=2),
        dbc.Col(dcc.Dropdown(id='export-format', options=[{'label': 'Excel', 'value': 'excel'}, {'label': 'CSV', 'value': 'csv'}],
                            value='excel', clearable=False), width=2),
        dbc.Col(html.Div(id='output-recalcular', className="text-danger text-center"), width=2)
    ], justify="center", className="mb-4"),

    # TABELA — SELEÇÃO DE LINHA COM CLIQUE EM QUALQUER LUGAR
    dbc.Row([
        dbc.Col(dash_table.DataTable(
            id='tabela-operacoes',
            columns=[
                {'name': 'TICKER', 'id': 'TICKER'},
                {'name': 'OPERAÇÃO/DIREÇÃO', 'id': 'OPERAÇÃO/DIREÇÃO'},
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
            row_selectable='multi',
            selected_rows=[],
            persistence=True,
            persistence_type='session'
        ), width=12)
    ]),

    # TODOS OS STORES E INTERVALS
    dcc.Interval(id='initial-load-interval', interval=1000, n_intervals=0, disabled=True),
    dcc.Interval(id='message-clear-interval', interval=3000, n_intervals=0, disabled=True),
    dcc.Store(id='init-table-trigger', data=''),
    dcc.Store(id='trigger-recalcular', data=0),
    dcc.Store(id='selected-row', data=None),
    html.Div(id='table-update-trigger-nova', style={'display': 'none'}),
    html.Div(id='table-update-trigger-alterar', style={'display': 'none'}),
    html.Div(id='dummy-focus-ticker', style={'display': 'none'}),
    html.Div(id='dummy-initial-load', style={'display': 'none'}),    
# Modal de Nova Operação
    dbc.Modal(
        [
            dbc.ModalHeader("Nova Operação", close_button=True),
            dbc.ModalBody([
                dbc.Form(className="form-group", style={'padding': '15px'}, children=[
                    # TICKER
                    dbc.Row([
                        dbc.Col(html.Label("TICKER", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-ticker', type='text', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-ticker-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # OPERAÇÃO - DESABILITADO após extração
                    dbc.Row([
                        dbc.Col(html.Label("OPERAÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Dropdown(
                            id='nova-operacao',
                            options=[{'label': 'Call', 'value': 'Call'}, {'label': 'Put', 'value': 'Put'}],
                            disabled=False,
                            clearable=False,
                            className="form-control",
                            style={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
                        ), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-operacao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # DIREÇÃO
                    dbc.Row([
                        dbc.Col(html.Label("DIREÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Dropdown(id='nova-direcao', options=[{'label': 'Compra', 'value': 'Compra'}, {'label': 'Venda', 'value': 'Venda'}], className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-direcao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # STRIKE - VAZIO após extração
                    dbc.Row([
                        dbc.Col(html.Label("STRIKE", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-strike', type='number', step=0.0001, className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-strike-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # QUANTIDADE
                    dbc.Row([
                        dbc.Col(html.Label("QUANTIDADE", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-quantidade', type='number', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-quantidade-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # VALOR OPÇÃO
                    dbc.Row([
                        dbc.Col(html.Label("VALOR OPÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-valor-opcao', type='number', step=0.0001, className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-valor-opcao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # DATA OP
                    dbc.Row([
                        dbc.Col(html.Label("DATA OP", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-data-op', placeholder="DD/MM/YYYY", type='text', className="form-control", value=dt_now.now().strftime('%d/%m/%Y')), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-data-op-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # DATA EXERC - EXTRAÍDA AUTOMATICAMENTE
                    dbc.Row([
                        dbc.Col(html.Label("DATA EXERC", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-data-exerc', placeholder="DD/MM/YYYY", type='text', className="form-control", readOnly=True), width=6, style={'padding': '5px', 'maxWidth': '100%', 'backgroundColor': '#e9ecef'}),
                        dbc.Col(html.Div(id='nova-data-exerc-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # ESTRUTURA
                    dbc.Row([
                        dbc.Col(html.Label("ESTRUTURA", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-estrutura', type='text', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-estrutura-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    # ROLAGEM
                    dbc.Row([
                        dbc.Col(html.Label("ROLAGEM", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='nova-rolagem', type='text', className="form-control"), width=6, style={'padding': '5px', 'maxWidth': '100%'}),
                        dbc.Col(html.Div(id='nova-rolagem-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
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
                        dbc.Col(html.Label("TICKER", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(html.Span(id='alterar-ticker', className="form-control", style={'backgroundColor': '#e9ecef', 'padding': '6px'}), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-ticker-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("OPERAÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(html.Span(id='alterar-operacao', className="form-control", style={'backgroundColor': '#e9ecef', 'padding': '6px'}), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-operacao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DIREÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(html.Span(id='alterar-direcao', className="form-control", style={'backgroundColor': '#e9ecef', 'padding': '6px'}), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-direcao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("QUANTIDADE", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='alterar-quantidade', type='number', className="form-control"), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-quantidade-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("VALOR OPÇÃO", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='alterar-valor-opcao', type='number', step='0.01', className="form-control"), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-valor-opcao-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DATA OP", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='alterar-data-op', type='text', placeholder='DD/MM/YYYY', className="form-control"), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-data-op-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("DATA EXERC", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(html.Span(id='alterar-data-exerc', className="form-control", style={'backgroundColor': '#e9ecef', 'padding': '6px'}), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-data-exerc-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("ESTRUTURA", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='alterar-estrutura', type='text', className="form-control"), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-estrutura-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    dbc.Row([
                        dbc.Col(html.Label("ROLAGEM", className="label"), width=4, style={'padding': '5px'}),
                        dbc.Col(dcc.Input(id='alterar-rolagem', type='text', className="form-control"), width=6, style={'padding': '5px'}),
                        dbc.Col(html.Div(id='alterar-rolagem-val', className="validation-col text-center"), width=2, style={'padding': '5px'}),
                    ], style={'marginBottom': '15px', 'alignItems': 'center'}),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col(html.Div(id='modal-alterar-mensagem', className="alert alert-info"), width=12)
                    ])
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
    # Modal para Encerrar Operação
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
    )
], fluid=True, className="px-4")

if __name__ == '__main__':
    from app_callbacks import register_callbacks
    register_callbacks(app)
    app.run(debug=True)