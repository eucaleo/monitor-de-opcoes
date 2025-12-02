# calculations.py

import pandas as pd
import datetime as dt
import logging
import locale
from decimal import Decimal, ROUND_HALF_UP
from database import get_encerradas

logging.basicConfig(level=logging.INFO)

def calculate_operation_value(quantidade, valor_opcao, direcao):
    if quantidade and valor_opcao and direcao:  # Corrigido: calcular apenas se todos os parâmetros existirem
        quant = Decimal(str(quantidade).replace(',', '.'))
        val_op = Decimal(str(valor_opcao).replace(',', '.'))
        value = quant * val_op
        logging.info(f"[LOG] calculate_operation_value: quantidade={quant}, valor_opcao={val_op}, direcao={direcao}, value={value}")
        if direcao == 'Compra':
            return -value
        else:
            return value
    else:
        logging.warning("[LOG] Parâmetros ausentes em calculate_operation_value")
        return Decimal('0.0')  # Retorno padrão para evitar erros

def calculate_saldo_abertas(transacoes):
    if transacoes is None or transacoes.empty:
        return Decimal('0.0')
    transacoes = transacoes.fillna({'VALOR OPERAÇÃO': Decimal('0.0')})  # Preenche NaNs na coluna crítica para evitar somas inválidas
    return Decimal(str(transacoes['VALOR OPERAÇÃO'].sum()))

def calculate_resultado_mes(transacoes, mes_ano):
    if transacoes is None or transacoes.empty:
        return Decimal('0.0')
    # Lógica adicional assumida das páginas restantes; adicione aqui se necessário
    transacoes['DATA OP'] = pd.to_datetime(transacoes['DATA OP'], format='%d/%m/%Y', errors='coerce')
    mes, ano = map(int, mes_ano.split('/'))
    mes_str = f"{mes:02d}/{ano}"
    transacoes_abertas = transacoes[transacoes['DATA OP'].dt.strftime('%m/%Y') == mes_str]
    saldo_abertas = Decimal(str(transacoes_abertas['VALOR OPERAÇÃO'].sum())) if not transacoes_abertas.empty else Decimal('0.0')
    
    encerradas = get_encerradas()
    if encerradas is not None and not encerradas.empty:
        encerradas['data_encerr'] = pd.to_datetime(encerradas['data_encerr'], format='%d/%m/%Y', errors='coerce')
        encerradas_mes = encerradas[encerradas['data_encerr'].dt.strftime('%m/%Y') == mes_str]
        saldo_encerradas_valor = Decimal(str(encerradas_mes['valor_encerr'].sum() or Decimal('0.0')))
        ganho_prejuizo_encerradas = Decimal(str(encerradas_mes['g_p'].sum() or Decimal('0.0')))
    else:
        saldo_encerradas_valor = Decimal('0.0')
        ganho_prejuizo_encerradas = Decimal('0.0')
    
    return saldo_abertas + saldo_encerradas_valor + ganho_prejuizo_encerradas

def calculate_saldo_encerradas():
    encerradas = get_encerradas()
    if encerradas is not None and not encerradas.empty:
        return Decimal(str(encerradas['valor_encerr'].sum() or Decimal('0.0')))
    return Decimal('0.0')  # Placeholder para completude

def calculate_estruturas(transacoes):
    if transacoes is None or transacoes.empty:
        return {}
    saldo_por_estrutura = transacoes.groupby('ESTRUTURA').agg({'VALOR OPERAÇÃO': 'sum', 'ROLAGEM': 'sum'}).sum(axis=1).to_dict()
    total_estruturas = sum(Decimal(str(v)) for v in saldo_por_estrutura.values()) if saldo_por_estrutura else Decimal('0.0')
    saldo_por_estrutura['Total Estruturas'] = total_estruturas
    return {k: Decimal(str(v)) for k, v in saldo_por_estrutura.items() if Decimal(str(v)) != Decimal('0') or k == 'Total Estruturas'}

def calculate_profit_loss(valor_opcao, valor_encerr, quantidade, operacao):
    if not all([valor_opcao, valor_encerr, quantidade]):
        return Decimal('0.0')
    abs_quant = abs(Decimal(str(quantidade)))
    if 'Compra' in operacao:
        return (Decimal(str(valor_encerr)) - Decimal(str(valor_opcao))) * abs_quant
    else:
        return (Decimal(str(valor_opcao)) - Decimal(str(valor_encerr))) * abs_quant

def calculate_structure_net(df):
    if df.empty:
        return {}
    return df.groupby('ESTRUTURA').apply(lambda x: (x['VALOR OPERAÇÃO'] + x['ROLAGEM']).sum()).to_dict()

def calculate_by_type(periodo, status, operacao, direcao):
    from database import get_transactions, get_encerradas
    df_open = get_transactions()
    df_closed = get_encerradas()
    today = dt.datetime.now()
    if periodo == 'Dia':
        start = today - dt.timedelta(days=1)
    elif periodo == 'Semana':
        start = today - dt.timedelta(days=7)
    elif periodo == 'Mês':
        start = dt.datetime(today.year, today.month, 1)
    elif periodo == 'Ano':
        start = dt.datetime(today.year, 1, 1)
    else:
        start = dt.datetime.min
    
    if status == 'Aberto':
        if df_open.empty:
            return Decimal('0.0'), "Sem operações"
        df_open['DATA OP'] = pd.to_datetime(df_open['DATA OP'], format='%d/%m/%Y', errors='coerce')
        df = df_open[(df_open['DATA OP'] >= start) & (df_open['OPERAÇÃO'] == operacao) & (df_open['DIREÇÃO'] == direcao)]
        valor = Decimal(str(df['VALOR OPERAÇÃO'].sum())) if not df.empty else Decimal('0.0')
        msg = f"R$ {valor:.2f}" if valor != Decimal('0') else "Sem operações"
        return valor, msg
    elif status == 'Encerrado':
        if df_closed.empty:
            return Decimal('0.0'), "Sem operações"
        df_closed['data_encerr'] = pd.to_datetime(df_closed['data_encerr'], format='%d/%m/%Y', errors='coerce')
        df = df_closed[(df_closed['data_encerr'] >= start) & (df_closed['operacao'] == operacao) & (df_closed['direcao'] == direcao)]
        valor = Decimal(str(df['g_p'].sum())) if not df.empty else Decimal('0.0')
        msg = f"R$ {valor:.2f}" if valor != Decimal('0') else "Sem operações"
        return valor, msg
    elif status == 'Todos':
        open_val, _ = calculate_by_type(periodo, 'Aberto', operacao, direcao)
        closed_val, _ = calculate_by_type(periodo, 'Encerrado', operacao, direcao)
        total = open_val + closed_val
        msg = f"R$ {total:.2f}" if total != Decimal('0') else "Sem operações"
        return total, msg
    return Decimal('0.0'), "Sem operações"
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass  # fallback manual

def fmt_br(valor, casas=2, moeda=True):
    """
    Formata qualquer número (float, int, str, Decimal) no padrão brasileiro
    Ex: 1234567.89 → "R$ 1.234.567,89" ou "1.234.567,89"
    """
    if valor is None or valor == '':
        return "R$ 0,00" if moeda else "0,00"
    
    # Converte tudo pra Decimal (segurança total)
    try:
        v = Decimal(str(valor))
    except:
        v = Decimal('0')
    
    # Arredonda corretamente
    if casas == 0:
        v = v.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    else:
        v = v.quantize(Decimal(f'0.{"0"*casas}'), rounding=ROUND_HALF_UP)
    
    # Formata com separadores brasileiros
    valor_str = f"{v:,.{casas}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    if moeda:
        sinal = "-" if v < 0 else ""
        valor_str = valor_str.replace('-', '')
        return f"{sinal}R$ {valor_str}"
    else:
        return f"-{valor_str}" if v < 0 else valor_str