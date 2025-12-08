# database.py

import sqlite3
import pandas as pd
import datetime as dt
import logging
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO)
DB_PATH = 'transacoes.db'

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, timeout=5.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA foreign_keys=OFF;")  # simples/local
    except Exception as e:
        logging.warning(f"[DB] PRAGMA falhou: {e}")
    return conn

def init_database() -> None:
    logging.info("[DB] Inicializando banco e migrações")
    with _connect() as conn:
        c = conn.cursor()
        # transacoes
        c.execute('''CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            operacao TEXT,          -- 'Call'/'Put'
            strike REAL,
            quantidade INTEGER,     -- com sinal (+ compra, - venda)
            valor_opcao REAL,       -- unitário positivo
            data_exerc TEXT,        -- 'DD/MM/YYYY'
            data_op TEXT,           -- data da inclusão
            valor_operacao REAL,    -- cash flow de abertura (neg compra, pos venda)
            estrutura TEXT,
            rolagem TEXT,           -- texto livre
            vinculo_prejuizo INTEGER,
            direcao TEXT,           -- 'Compra'/'Venda' (histórico)
            valor_atual REAL        -- preço unitário atual via Provider (opcional)
        )''')

        # garante colunas novas em transacoes
        c.execute("PRAGMA table_info(transacoes)")
        cols = [row[1] for row in c.fetchall()]
        if 'rolagem' not in cols:
            c.execute("ALTER TABLE transacoes ADD COLUMN rolagem TEXT")
        if 'valor_atual' not in cols:
            c.execute("ALTER TABLE transacoes ADD COLUMN valor_atual REAL")

        # índices úteis
        c.execute("CREATE INDEX IF NOT EXISTS idx_tx_ticker ON transacoes (ticker)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tx_dataop ON transacoes (data_op)")

        # log_alteracoes
        c.execute('''CREATE TABLE IF NOT EXISTS log_alteracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transacao_id INTEGER,
            campo_alterado TEXT,
            valor_antigo TEXT,
            valor_novo TEXT,
            tipo_alteracao TEXT,
            data_alteracao TEXT
        )''')

        # encerradas
        c.execute('''CREATE TABLE IF NOT EXISTS encerradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_origem INTEGER,
            ticker TEXT NOT NULL,
            operacao TEXT,
            direcao TEXT,
            strike REAL,
            quantidade INTEGER,         -- quantidade encerrada (sempre positiva)
            valor_opcao REAL,           -- unitário abertura
            valor_operacao REAL,        -- cash flow abertura da parte encerrada
            data_op TEXT,
            data_exerc TEXT,
            estrutura TEXT,
            rolagem TEXT,
            data_encerr TEXT,
            valor_encerr REAL,          -- unitário encerramento
            valor_oper_encerr REAL,     -- cash flow do encerramento
            g_p REAL,                   -- P&L realizado (parte encerrada)
            perdas_invest REAL          -- reservado
        )''')

        # migra id_origem e valor_oper_encerr se faltarem
        c.execute("PRAGMA table_info(encerradas)")
        ecols = [row[1] for row in c.fetchall()]
        if 'id_origem' not in ecols:
            c.execute("ALTER TABLE encerradas ADD COLUMN id_origem INTEGER")
        if 'valor_oper_encerr' not in ecols:
            c.execute("ALTER TABLE encerradas ADD COLUMN valor_oper_encerr REAL")
        if 'rolagem' not in ecols:
            c.execute("ALTER TABLE encerradas ADD COLUMN rolagem TEXT")
        c.execute("CREATE INDEX IF NOT EXISTS idx_enc_idorigem ON encerradas (id_origem)")
        conn.commit()
    logging.info("[DB] Banco pronto")

def _hoje_str() -> str:
    return dt.datetime.now().strftime('%d/%m/%Y')

def get_transactions() -> pd.DataFrame:
    try:
        with _connect() as conn:
            df = pd.read_sql_query(
                """SELECT id, ticker, operacao, direcao, strike, quantidade,
                          valor_opcao, data_exerc, data_op, valor_operacao,
                          estrutura, rolagem, vinculo_prejuizo, valor_atual
                   FROM transacoes""",
                conn
            )
            # Nomes com padrão da UI
            df.rename(columns={
                'ticker': 'TICKER',
                'operacao': 'OPERAÇÃO',
                'direcao': 'DIREÇÃO',
                'strike': 'STRIKE',
                'quantidade': 'QUANTIDADE',
                'valor_opcao': 'VALOR OPÇÃO',
                'data_exerc': 'DATA EXERC',
                'data_op': 'DATA OP',
                'valor_operacao': 'VALOR OPERAÇÃO',
                'estrutura': 'ESTRUTURA',
                'rolagem': 'ROLAGEM',
                'vinculo_prejuizo': 'VINCULO_PREJUIZO',
                'valor_atual': 'VALOR ATUAL'
            }, inplace=True)
            return df
    except Exception as e:
        logging.error(f"[DB] get_transactions erro: {e}")
        return pd.DataFrame()

def get_encerradas() -> pd.DataFrame:
    try:
        with _connect() as conn:
            df = pd.read_sql_query(
                """SELECT id, id_origem, ticker, operacao, direcao, strike,
                          quantidade, valor_opcao, valor_operacao, data_op,
                          data_exerc, estrutura, rolagem, data_encerr,
                          valor_encerr, valor_oper_encerr, g_p, perdas_invest
                   FROM encerradas""",
                conn
            )
            return df
    except Exception as e:
        logging.error(f"[DB] get_encerradas erro: {e}")
        return pd.DataFrame()

def _calc_signals(direcao: str) -> Tuple[int, int]:
    """
    Retorna (sign_qtd, sign_cashflow_abertura)
    Compra -> (+1, -1) ; Venda -> (-1, +1)
    """
    if direcao == 'Compra':
        return (+1, -1)
    return (-1, +1)

def add_operation(
    ticker: str,
    operacao: str,      # 'Call'/'Put'
    direcao: str,       # 'Compra'/'Venda'
    strike: float,
    quantidade: int,    # valor absoluto informado no formulário
    valor_opcao: float, # unitário positivo
    data_exerc: str,
    estrutura: Optional[str],
    rolagem: Optional[str]
) -> int:
    init_database()
    sign_qtd, sign_cash = _calc_signals(direcao)
    quantidade_norm = sign_qtd * abs(int(quantidade))
    valor_operacao = sign_cash * abs(float(valor_opcao)) * abs(int(quantidade))

    with _connect() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO transacoes
               (ticker, operacao, strike, quantidade, valor_opcao, data_exerc,
                data_op, valor_operacao, estrutura, rolagem, vinculo_prejuizo,
                direcao, valor_atual)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ticker.upper().strip(),
                operacao,
                float(strike) if strike is not None else None,
                quantidade_norm,
                abs(float(valor_opcao)),
                data_exerc,
                _hoje_str(),
                valor_operacao,
                (estrutura or None),
                (rolagem or None),
                None,
                direcao,
                None
            )
        )
        new_id = c.lastrowid
        # LOG
        c.execute(
            """INSERT INTO log_alteracoes
               (transacao_id, campo_alterado, valor_antigo, valor_novo, tipo_alteracao, data_alteracao)
               VALUES (?,?,?,?,?,?)""",
            (new_id, 'INSERCAO', '', f'{ticker}/{operacao}/{direcao}', 'INSERCAO', _hoje_str())
        )
        conn.commit()
        logging.info(f"[DB] Nova operação id={new_id} inserida")
        return new_id

def update_operation(
    operacao_id: int,
    quantidade: Optional[int] = None,  # absoluto
    estrutura: Optional[str] = None,
    rolagem: Optional[str] = None
) -> None:
    """
    Editáveis: quantidade, estrutura, rolagem.
    data_op e valor_opcao NÃO editáveis aqui.
    Recalcula valor_operacao se quantidade mudar (coerência com correção do lançamento).
    """
    with _connect() as conn:
        c = conn.cursor()
        c.execute("SELECT id, direcao, valor_opcao, quantidade, estrutura, rolagem FROM transacoes WHERE id=?", (operacao_id,))
        row = c.fetchone()
        if not row:
            raise ValueError("Operação não encontrada")
        _, direcao_old, valor_opcao, quantidade_old, estrutura_old, rolagem_old = row

        updates = []
        logs = []

        if quantidade is not None:
            sign_qtd, sign_cash = _calc_signals(direcao_old)
            quantidade_norm = sign_qtd * abs(int(quantidade))
            valor_operacao = sign_cash * abs(float(valor_opcao)) * abs(int(quantidade))
            updates.append(('quantidade', quantidade_norm))
            updates.append(('valor_operacao', valor_operacao))
            logs.append(('quantidade', str(quantidade_old), str(quantidade_norm)))
            logs.append(('valor_operacao', '', str(valor_operacao)))

        if estrutura is not None and estrutura != estrutura_old:
            updates.append(('estrutura', estrutura))
            logs.append(('estrutura', str(estrutura_old or ''), str(estrutura or '')))

        if rolagem is not None and rolagem != rolagem_old:
            updates.append(('rolagem', rolagem))
            logs.append(('rolagem', str(rolagem_old or ''), str(rolagem or '')))

        if updates:
            set_clause = ", ".join([f"{k}=?" for k, _ in updates])
            params = [v for _, v in updates] + [operacao_id]
            c.execute(f"UPDATE transacoes SET {set_clause} WHERE id=?", params)

            for campo, antigo, novo in logs:
                c.execute(
                    """INSERT INTO log_alteracoes
                       (transacao_id, campo_alterado, valor_antigo, valor_novo, tipo_alteracao, data_alteracao)
                       VALUES (?,?,?,?,?,?)""",
                    (operacao_id, campo, antigo, novo, 'ALTERACAO', _hoje_str())
                )
            conn.commit()
            logging.info(f"[DB] Operação id={operacao_id} atualizada")

def close_operation(
    row_id: int,
    qtd_encerrada: int,        # absoluto
    valor_encerr_unit: float,  # unitário positivo
    data_encerr: str,
    rolagem_texto: Optional[str] = None
) -> int:
    """
    Encerramento parcial/total.
    - Gera registro em 'encerradas' com id_origem, valor_oper_encerr e g_p.
    - Atualiza/remover a operação aberta.
    Retorna id do registro em 'encerradas'.
    """
    with _connect() as conn:
        c = conn.cursor()
        c.execute("""SELECT id, ticker, operacao, direcao, strike, quantidade,
                            valor_opcao, valor_operacao, data_op, data_exerc,
                            estrutura, rolagem
                     FROM transacoes WHERE id=?""", (row_id,))
        tx = c.fetchone()
        if not tx:
            raise ValueError("Operação original não encontrada")

        (tid, ticker, operacao, direcao, strike, quantidade_atual, valor_opcao,
         valor_operacao_abertura, data_op, data_exerc, estrutura, rolagem_old) = tx

        qtd = abs(int(qtd_encerrada))
        if qtd <= 0:
            raise ValueError("Quantidade encerrada inválida")

        # Sinais
        sign_qtd_open, sign_cash_open = _calc_signals(direcao)  # abertura
        # Direção de fechamento é a oposta da original
        direcao_encerr = 'Venda' if direcao == 'Compra' else 'Compra'
        _, sign_cash_close = _calc_signals(direcao_encerr)

        # Cash flow da parte encerrada na abertura (por parte)
        cash_open_part = sign_cash_open * abs(float(valor_opcao)) * qtd
        # Cash flow do encerramento (por parte)
        cash_close_part = sign_cash_close * abs(float(valor_encerr_unit)) * qtd
        # P&L realizado da parte encerrada
        gp_part = cash_close_part + cash_open_part

        # Atualiza quantidade remanescente
        # Regra: nova_qtd = qtd_atual - qtd * sinal(qtd_atual)
        sinal_atual = 1 if quantidade_atual > 0 else -1
        nova_qtd = quantidade_atual - sinal_atual * qtd

        # Inserir encerrada
        c.execute(
            """INSERT INTO encerradas
               (id_origem, ticker, operacao, direcao, strike, quantidade,
                valor_opcao, valor_operacao, data_op, data_exerc, estrutura, rolagem,
                data_encerr, valor_encerr, valor_oper_encerr, g_p, perdas_invest)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tid, ticker, operacao, direcao, strike, qtd,
                valor_opcao, cash_open_part, data_op, data_exerc, estrutura,
                (rolagem_texto or rolagem_old),
                data_encerr, abs(float(valor_encerr_unit)), cash_close_part, gp_part, None
            )
        )
        encerr_id = c.lastrowid

        # Log encerramento
        c.execute(
            """INSERT INTO log_alteracoes
               (transacao_id, campo_alterado, valor_antigo, valor_novo, tipo_alteracao, data_alteracao)
               VALUES (?,?,?,?,?,?)""",
            (tid, 'status', 'aberta', f'encerrada_parcial({qtd})' if nova_qtd != 0 else 'encerrada_total', 'ENCERRAMENTO', data_encerr)
        )

        # Ajusta abertura
        if nova_qtd == 0:
            c.execute("DELETE FROM transacoes WHERE id=?", (tid,))
        else:
            c.execute("UPDATE transacoes SET quantidade=? WHERE id=?", (nova_qtd, tid))

        conn.commit()
        logging.info(f"[DB] Encerramento id={encerr_id} (origem {tid}) registrado")
        return encerr_id

def update_valor_atual_transacao(transacao_id: int, valor_atual: Optional[float]) -> None:
    with _connect() as conn:
        conn.execute("UPDATE transacoes SET valor_atual=? WHERE id=?", (valor_atual, transacao_id))
        conn.commit()
