# calculations.py

import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple, Optional
import logging
from datetime import datetime

from database import get_transactions, get_encerradas

logging.basicConfig(level=logging.INFO)

def fmt_br(valor, casas=2, moeda=True) -> str:
    if valor is None or valor == '':
        return "R$ 0,00" if moeda else "0,00"
    try:
        v = Decimal(str(valor))
    except Exception:
        v = Decimal('0')
    if casas == 0:
        v = v.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    else:
        v = v.quantize(Decimal('0.' + '0'*casas), rounding=ROUND_HALF_UP)
    s = f"{v:,.{casas}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if moeda:
        sinal = "-" if v < 0 else ""
        s = s.replace('-', '')
        return f"{sinal}R$ {s}"
    return f"-{s}" if v < 0 else s

def _to_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, '%d/%m/%Y')
    except Exception:
        return None

def calculate_operation_value(direcao: str, quantidade: int, valor_opcao: float) -> float:
    """
    - valor_opcao: unitário positivo
    - quantidade: absoluto (input do form)
    Retorna cash flow da abertura (neg compra, pos venda)
    """
    q = abs(int(quantidade))
    p = abs(float(valor_opcao))
    if direcao == 'Compra':
        return -q * p
    return q * p

def _filter_periodo(df: pd.DataFrame, col_data: str, start_iso: Optional[str], end_iso: Optional[str]) -> pd.DataFrame:
    if df.empty:
        return df
    # DatePickerRange envia ISO YYYY-MM-DD
    start_dt = datetime.fromisoformat(start_iso) if start_iso else None
    end_dt = datetime.fromisoformat(end_iso) if end_iso else None
    dcol = df[col_data].apply(_to_dt)
    mask = pd.Series(True, index=df.index)
    if start_dt:
        mask &= dcol >= start_dt
    if end_dt:
        mask &= dcol <= end_dt
    return df[mask]

def cards_aberturas(periodo_start_iso: Optional[str], periodo_end_iso: Optional[str]) -> Tuple[str, str, str, str]:
    tx = get_transactions()
    if tx.empty:
        return ("R$ 0,00",) * 4
    txp = _filter_periodo(tx.copy(), 'DATA OP', periodo_start_iso, periodo_end_iso)
    def soma(oper, direc):
        df = txp[(txp['OPERAÇÃO'] == oper) & (txp['DIREÇÃO'] == direc)]
        return float(df['VALOR OPERAÇÃO'].sum()) if not df.empty else 0.0
    return (
        fmt_br(soma('Call', 'Compra')),
        fmt_br(soma('Call', 'Venda')),
        fmt_br(soma('Put', 'Compra')),
        fmt_br(soma('Put', 'Venda')),
    )

def cards_gp(periodo_start_iso: Optional[str], periodo_end_iso: Optional[str]) -> Tuple[str, str]:
    enc = get_encerradas()
    if enc.empty:
        return ("R$ 0,00", "R$ 0,00")
    enc = enc.copy()
    enc.rename(columns={'data_encerr': 'DATA ENCERR'}, inplace=True)
    encp = _filter_periodo(enc, 'DATA ENCERR', periodo_start_iso, periodo_end_iso)
    if encp.empty:
        return ("R$ 0,00", "R$ 0,00")
    encp['ESTRUTURA'] = encp['estrutura'].fillna('')
    gp_estrut = encp[encp['ESTRUTURA'] != '']['g_p'].sum() if 'g_p' in encp.columns else 0.0
    gp_simples = encp[encp['ESTRUTURA'] == '']['g_p'].sum() if 'g_p' in encp.columns else 0.0
    return (fmt_br(gp_estrut), fmt_br(gp_simples))

def card_fluxo(periodo_start_iso: Optional[str], periodo_end_iso: Optional[str]) -> str:
    tx = get_transactions()
    enc = get_encerradas()
    total = 0.0
    if not tx.empty:
        txp = _filter_periodo(tx, 'DATA OP', periodo_start_iso, periodo_end_iso)
        total += float(txp['VALOR OPERAÇÃO'].sum()) if not txp.empty else 0.0
    if not enc.empty:
        enc = enc.copy()
        enc.rename(columns={'data_encerr': 'DATA ENCERR'}, inplace=True)
        encp = _filter_periodo(enc, 'DATA ENCERR', periodo_start_iso, periodo_end_iso)
        if not encp.empty and 'valor_oper_encerr' in encp.columns:
            total += float(encp['valor_oper_encerr'].sum())
    return fmt_br(total)

def card_posicao_aberta() -> str:
    tx = get_transactions()
    if tx.empty:
        return "R$ 0,00"
    return fmt_br(float(tx['VALOR OPERAÇÃO'].sum()))
