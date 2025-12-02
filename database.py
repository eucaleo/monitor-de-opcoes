# database.py 
import sqlite3 
import pandas as pd 
import datetime as dt 
import logging 
from validations import validate_ticker 

logging.basicConfig(level=logging.INFO) 

def init_database(): 

    """Cria as tabelas necessárias e garante a presença das colunas esperadas.""" 

    logging.info("[LOG] Inicializando banco de dados") 

    conn = None 
    try: 
        conn = sqlite3.connect('transacoes.db') 
        c = conn.cursor() 
        # ---------- Tabela transacoes ---------- 
        c.execute('''CREATE TABLE IF NOT EXISTS transacoes ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            ticker TEXT, 
            operacao TEXT, 
            strike REAL, 
            quantidade INTEGER, 
            valor_opcao REAL, 
            data_exerc TEXT, 
            data_op TEXT, 
            valor_operacao REAL, 
            estrutura TEXT, 
            rolagem REAL, 
            vinculo_prejuizo INTEGER, 
            direcao TEXT 
        )''') 

        # Verifica e adiciona colunas faltantes 
        c.execute("PRAGMA table_info(transacoes)") 
        columns = [col[1] for col in c.fetchall()] 
        for col, sql in [ 
            ('direcao', "ALTER TABLE transacoes ADD COLUMN direcao TEXT"), 
            ('rolagem', "ALTER TABLE transacoes ADD COLUMN rolagem REAL"), 
            ('vinculo_prejuizo', "ALTER TABLE transacoes ADD COLUMN vinculo_prejuizo INTEGER") 
        ]: 
            if col not in columns: 
                c.execute(sql) 
                logging.info(f"[LOG] Coluna {col} adicionada à transacoes") 

        # Adição de índices para queries rápidas 
        c.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON transacoes (ticker)") 
        c.execute("CREATE INDEX IF NOT EXISTS idx_data_op ON transacoes (data_op)") 
        logging.info("[LOG] Índices adicionados para ticker e data_op") 

        # ---------- Tabela log_alteracoes ---------- 
        c.execute('''CREATE TABLE IF NOT EXISTS log_alteracoes ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            transacao_id INTEGER, 
            campo_alterado TEXT, 
            valor_antigo TEXT, 
            valor_novo TEXT, 
            tipo_alteracao TEXT, 
            data_alteracao TEXT 
        )''') 

        # ---------- Tabela encerradas ---------- 
        c.execute('''CREATE TABLE IF NOT EXISTS encerradas ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            ticker TEXT NOT NULL, 
            g_p REAL, 
            perdas_invest REAL, 
            data_encerr TEXT, 
            valor_opcao REAL, 
            quantidade INTEGER, 
            data_op TEXT, 
            data_exerc TEXT, 
            direcao TEXT, 
            operacao TEXT, 
            strike REAL, 
            valor_operacao REAL, 
            estrutura TEXT, 
            rolagem REAL, 
            valor_encerr REAL 
        )''') 
        c.execute("PRAGMA table_info(encerradas)") 
        enc_columns = [col[1] for col in c.fetchall()] 
        for col, sql in [ 
            ('direcao', "ALTER TABLE encerradas ADD COLUMN direcao TEXT"), 
            ('perdas_invest', "ALTER TABLE encerradas ADD COLUMN perdas_invest REAL"), 
            ('rolagem', "ALTER TABLE encerradas ADD COLUMN rolagem REAL") 
        ]: 
            if col not in enc_columns: 
                c.execute(sql) 
                logging.info(f"[LOG] Coluna {col} adicionada à encerradas") 
        conn.commit() 
        logging.info("[LOG] Tabelas criadas/atualizadas: transacoes, log_alteracoes, encerradas") 
        return conn, c 
    except sqlite3.Error as e: 
        logging.error(f"[LOG] Erro ao inicializar banco de dados: {e}") 
        if conn: 
            conn.rollback() 
        return None, None 
    finally: 
        if conn: 
            conn.close() 
def check_table_exists(table_name: str) -> bool: 
    """Verifica se a tabela existe.""" 
    with sqlite3.connect('transacoes.db') as conn: 
        c = conn.cursor() 
        c.execute( 
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
            (table_name,) 
        ) 
        exists = c.fetchone() is not None 
    logging.info(f"[LOG] Tabela {table_name}: {'existe' if exists else 'não existe'}") 
    return exists 
def get_transactions() -> pd.DataFrame: 
    """Retorna todas as transações abertas como DataFrame.""" 
    try: 
        with sqlite3.connect('transacoes.db') as conn: 
            c = conn.cursor() 
            c.execute("""SELECT id, ticker, operacao, strike, quantidade, 
                                valor_opcao, data_exerc, data_op, valor_operacao, 
                                estrutura, rolagem, vinculo_prejuizo, direcao 
                         FROM transacoes""") 
            rows = c.fetchall() 
            logging.info(f"[LOG] {len(rows)} linhas obtidas de transacoes") 
            df = pd.DataFrame( 
                rows, 
                columns=['id', 'TICKER', 'OPERAÇÃO', 'STRIKE', 'QUANTIDADE', 
                         'VALOR OPÇÃO', 'DATA EXERC', 'DATA OP', 'VALOR OPERAÇÃO', 
                         'ESTRUTURA', 'ROLAGEM', 'VINCULO_PREJUIZO', 'DIREÇÃO'] 
            ) 
            return df 
    except sqlite3.Error as e: 
        logging.error(f"[LOG] Erro em get_transactions: {e}") 
        return pd.DataFrame() 
def get_encerradas() -> pd.DataFrame: 
    """Retorna todas as operações encerradas como DataFrame.""" 
    try: 
        with sqlite3.connect('transacoes.db') as conn: 
            c = conn.cursor() 
            c.execute("""SELECT id, ticker, operacao, direcao, strike, quantidade, 
                                valor_opcao, valor_operacao, data_op, data_exerc, 
                                estrutura, rolagem, g_p, perdas_invest, 
                                data_encerr, valor_encerr 
                         FROM encerradas""") 
            rows = c.fetchall() 
            logging.info(f"[LOG] {len(rows)} linhas obtidas de encerradas") 
            df = pd.DataFrame( 
                rows, 
                columns=['id', 'ticker', 'operacao', 'direcao', 'strike', 
                         'quantidade', 'valor_opcao', 'valor_operacao', 
                         'data_op', 'data_exerc', 'estrutura', 'rolagem', 
                         'g_p', 'perdas_invest', 'data_encerr', 'valor_encerr'] 
            ) 
            return df 
    except sqlite3.Error as e: 
        logging.error(f"[LOG] Erro em get_encerradas: {e}") 
        return pd.DataFrame() 
def add_operation(ticker, operacao, strike, quantidade, valor_opcao, 
                  data_exerc, data_op, valor_operacao, estrutura, 
                  rolagem, direcao): 
    """Insere nova operação na tabela transacoes.""" 
    with sqlite3.connect('transacoes.db') as conn: 
        c = conn.cursor() 
        c.execute('''INSERT INTO transacoes 
                     (ticker, operacao, strike, quantidade, valor_opcao, 
                      data_exerc, data_op, valor_operacao, estrutura, 
                      rolagem, direcao) 
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)''', 
                  (ticker, operacao, strike, quantidade, valor_opcao, 
                   data_exerc, data_op, valor_operacao, estrutura, 
                   rolagem, direcao)) 
        conn.commit() 
        logging.info(f"[LOG] Operação inserida: {ticker} – {operacao}") 
def update_operation(ticker, valor_opcao, quantidade, rolagem, 
                     operacao_id, valor_operacao, estrutura, direcao): 
    """Atualiza operação existente.""" 
    try: 
        with sqlite3.connect('transacoes.db') as conn: 
            c = conn.cursor() 
            c.execute('''UPDATE transacoes 
                         SET ticker=?, valor_opcao=?, quantidade=?, 
                             rolagem=?, valor_operacao=?, estrutura=?, 
                             direcao=? 
                         WHERE id=?''', 
                      (ticker, valor_opcao, quantidade, rolagem, 
                       valor_operacao, estrutura, direcao, operacao_id)) 
            conn.commit() 
            logging.info(f"[LOG] Operação ID {operacao_id} atualizada") 
    except sqlite3.Error as e: 
        logging.error(f"[LOG] Erro em update_operation: {e}") 
def close_operation(row_id, valor_encerr, data_encerr, rolagem, 
                    quantidade, direcao): 
    """Move operação aberta para encerradas e registra log.""" 
    try: 
        with sqlite3.connect('transacoes.db') as conn: 
            c = conn.cursor() 
            if not check_table_exists('encerradas'): 
                init_database() 
                logging.info("[LOG] Tabela encerradas criada em close_operation") 
            c.execute("SELECT * FROM transacoes WHERE id = ?", (row_id,)) 
            transacao = c.fetchone() 
            if not transacao: 
                raise ValueError(f"Operação com id {row_id} não encontrada") 
            transacao_id = transacao[0] 
            valor_operacao = transacao[8]          # coluna valor_operacao 
            g_p = (float(valor_encerr) - float(valor_operacao) 
                   if valor_encerr and valor_operacao else 0.0) 
            perdas_invest = (abs(float(valor_operacao) * quantidade) 
                             if quantidade > 0 and g_p < 0 else 0.0) 
            vinculo_prejuizo = transacao_id if g_p < 0 else None 
            c.execute('''INSERT INTO encerradas 
                         (id, ticker, operacao, strike, quantidade, 
                          valor_opcao, data_exerc, data_op, valor_operacao, 
                          estrutura, rolagem, data_encerr, valor_encerr, 
                          g_p, direcao, perdas_invest) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                      (transacao_id, transacao[1], transacao[2], transacao[3], 
                       transacao[4], transacao[5], transacao[6], transacao[7], 
                       transacao[8], transacao[9], transacao[10], 
                       data_encerr, valor_encerr, g_p, transacao[12], 
                       perdas_invest)) 
            c.execute("""INSERT INTO log_alteracoes 
                         (transacao_id, campo_alterado, valor_antigo, 
                          valor_novo, tipo_alteracao, data_alteracao) 
                         VALUES (?,?,?,?,?,?)""", 
                      (transacao_id, 'status', 'aberta', 'encerrada', 
                       'ENCERRAMENTO', data_encerr)) 
            c.execute("DELETE FROM transacoes WHERE id = ?", (transacao_id,)) 
            if vinculo_prejuizo: 
                c.execute("UPDATE transacoes SET vinculo_prejuizo = ? WHERE id = ?", 
                          (vinculo_prejuizo, transacao_id)) 
            conn.commit() 
            logging.info(f"[LOG] Operação encerrada (id={transacao_id})") 
    except sqlite3.Error as e: 
        logging.error(f"[LOG] Erro em close_operation: {e}") 
        raise 
def recalculate_values(): 
    """Recalcula saldo do mês corrente (exemplo simples).""" 
    try: 
        with sqlite3.connect('transacoes.db') as conn: 
            c = conn.cursor() 
            hoje = dt.datetime.now().strftime('%d/%m/%Y') 
            c.execute("""SELECT ticker, operacao, quantidade, valor_opcao 
                         FROM transacoes WHERE data_exerc >= ?""", (hoje,)) 
            rows = c.fetchall() 
            total = sum(float(r[3]) * int(r[2]) * 
                        (-1 if 'Compra' in r[1] else 1) for r in rows) 
            logging.info(f"[LOG] Saldo recalculado: {total}") 
    except sqlite3.Error as e: 
        logging.error(f"[LOG] Erro em recalculate_values: {e}") 
        raise 
def update_saldo(mes_ano: str, valor: float): 
    """Registra/atualiza saldo mensal.""" 
    with sqlite3.connect('transacoes.db') as conn: 
        c = conn.cursor() 
        c.execute("""CREATE TABLE IF NOT EXISTS saldos 
                     (mes_ano TEXT PRIMARY KEY, valor REAL)""") 
        c.execute("""INSERT OR REPLACE INTO saldos (mes_ano, valor) 
                     VALUES (?, ?)""", (mes_ano, valor)) 
        conn.commit() 
def extrair_info_ticker(ticker): 
    """Extrai empresa, tipo, strike e data de vencimento a partir do ticker.""" 
    logging.info(f"[DEBUG] Extrair info para ticker: {ticker}") 
    if not ticker or len(ticker) < 6: 
        return None, None, None, None 
    try: 
        ticker = ticker.upper() 
        empresa = ticker[:4] 
        tipo = ticker[4] 
        result = validate_ticker(ticker) 
        if not result: 
            return empresa, tipo, None, None 
        ticker_base, semana = result 
        # strike 
        m = re.search(r'(\\d+)', ticker_base[5:]) 
        strike = float(m.group(1)) if m else None 
        # mês de vencimento 
        mes_map = {'A':1,'B':2,'C':3,'D':4,'E':5,'F':6, 
                   'G':7,'H':8,'I':9,'J':10,'K':11,'L':12, 
                   'M':1,'N':2,'O':3,'P':4,'Q':5,'R':6, 
                   'S':7,'T':8,'U':9,'V':10,'W':11,'X':12} 
        mes_base = mes_map.get(tipo) 
        if not mes_base: 
            return empresa, tipo, strike, None 
        hoje = dt.datetime.now() 
        ano = hoje.year + (1 if mes_base < hoje.month else 0) 
        data_base = dt.datetime(ano, mes_base, 1) 
        cal = pd.date_range(start=data_base, 
                            end=data_base.replace(month=mes_base % 12 + 1, day=1) - 
                            dt.timedelta(days=1), 
                            freq='W-FRI') 
        idx = {1:0, 2:1, 4:3, 5:4}.get(int(semana), 2) 
        vencimento = cal[min(idx, len(cal)-1)].strftime('%d/%m/%Y') 
        return empresa, tipo, strike, vencimento 
    except Exception as e: 
        logging.error(f"[DEBUG] Erro ao extrair ticker {ticker}: {e}") 
        return None, None, None, None 
def get_structure_transactions(estrutura: str) -> pd.DataFrame: 
    """Retorna transações de uma estrutura específica.""" 
    try: 
        with sqlite3.connect('transacoes.db') as conn: 
            c = conn.cursor() 
            c.execute("""SELECT id, ticker, operacao, strike, quantidade, 
                                valor_opcao, data_exerc, data_op, valor_operacao, 
                                estrutura, rolagem, vinculo_prejuizo, direcao 
                         FROM transacoes WHERE estrutura = ?""", (estrutura,)) 
            rows = c.fetchall() 
            if not rows: 
                return pd.DataFrame(columns=[ 
                    'id', 'TICKER', 'OPERAÇÃO', 'STRIKE', 'QUANTIDADE', 
                    'VALOR OPÇÃO', 'DATA EXERC', 'DATA OP', 'VALOR OPERAÇÃO', 
                    'ESTRUTURA', 'ROLAGEM', 'VINCULO_PREJUIZO', 'DIREÇÃO']) 
            df = pd.DataFrame(rows, columns=[ 
                'id', 'TICKER', 'OPERAÇÃO', 'STRIKE', 'QUANTIDADE', 
                'VALOR OPÇÃO', 'DATA EXERC', 'DATA OP', 'VALOR OPERAÇÃO', 
                'ESTRUTURA', 'ROLAGEM', 'VINCULO_PREJUIZO', 'DIREÇÃO']) 
            return df 
    except sqlite3.Error as e: 
        logging.error(f"[LOG] Erro em get_structure_transactions: {e}") 
        return pd.DataFrame() 
def get_saldo_mes(mes_ano: str) -> float: 
    """Saldo de um mês específico.""" 
    with sqlite3.connect('transacoes.db') as conn: 
        c = conn.cursor() 
        c.execute("SELECT COALESCE(SUM(valor), 0) FROM saldos WHERE mes_ano = ?", (mes_ano,)) 
        return c.fetchone()[0] 
def get_saldo_acumulado() -> float: 
    """Saldo total acumulado.""" 
    with sqlite3.connect('transacoes.db') as conn: 
        c = conn.cursor() 
        c.execute("SELECT COALESCE(SUM(valor), 0) FROM saldos") 
        return c.fetchone()[0] 