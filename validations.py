# validations.py  

import datetime as dt  
import re  
import logging  

logging.basicConfig(level=logging.INFO)  

def validate_ticker(ticker):  
    """Valida se o ticker tem 4 letras + série A-X + números + opcional W[1-2]|W[4-5]. Retorna (ticker_base, semana) ou False."""  
    if not ticker or not isinstance(ticker, str) or len(ticker.strip()) < 6:  
        return False  
    ticker = ticker.strip().upper()  
    match = re.match(r'^([A-Za-z]{4}[A-X][0-9]+)(W([1-2]|[4-5]))?$', ticker)  
    if not match:  
        return False  
    ticker_base = match.group(1)  
    semana = match.group(3) or '3'  # Padrão 3 se não houver W  
    return (ticker_base, semana)  

def validate_date(date_str):  
    """Valida e formata data no formato DD/MM/YYYY, retornando a string se válida."""  
    if not date_str:  
        return False  
    digits = ''.join(filter(str.isdigit, date_str))[:8]  
    if len(digits) == 8:  
        date_str = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"  
    try:  
        if len(date_str) != 10 or not re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):  
            return False  
        # Melhoria: Validação completa com strptime para datas reais 
        dt.datetime.strptime(date_str, '%d/%m/%Y') 
        return date_str 
    except ValueError: 
        return False 

def validate_numeric_positive(value, field_name, max_quant=1000000.0): 
    """   CORRIGIDO: Valida número positivo OU VAZIO (default original), com limite superior.""" 
    if value is None or str(value).strip() == "": 
        logging.info(f"[VALIDAÇÃO] {field_name} vazio - OK (usa original)") 
        return True  #   PERMITE VAZIO - usa valor original 
     
    try: 
        # Remove formatação monetária 
        clean_value = str(value).replace('R$ ', '').replace('.', '').replace(',', '.') 
        num_value = float(clean_value) 
        if num_value <= 0 or num_value > max_quant: 
            logging.error(f"[VALIDAÇÃO] Erro {field_name}: {num_value} (fora do limite >0 e <= {max_quant})") 
            return False 
        logging.info(f"[VALIDAÇÃO] {field_name}={value} → {num_value} → OK") 
        return True 
    except ValueError: 
        logging.error(f"[VALIDAÇÃO] Erro {field_name}: {value}") 
        return False 

def validate_future_date(date_str): 
    """Valida se a data é futura em relação a hoje.""" 
    if not validate_date(date_str): 
        return False 
    try: 
        date_obj = dt.datetime.strptime(date_str, '%d/%m/%Y') 
        return date_obj > dt.datetime.now() 
    except ValueError: 
        return False 
 
def validate_required(value, field_name): 
    """Valida se o valor é obrigatório e não vazio.""" 
    return bool(value and str(value).strip()) if value is not None else False 
 
def validate_structure(estrutura, transacoes=None): 
    """Valida se 'ESTRUTURA' é não vazio para operações multi-perna.""" 
    if transacoes is None: 
        return bool(estrutura and str(estrutura).strip()) 
    # Verificar se há múltiplas pernas associadas (simplificado) 
    if estrutura and str(estrutura).strip(): 
        return len(transacoes[transacoes['ESTRUTURA'] == estrutura]) > 1 
    return False 
 
def validate_input(ticker, valor, quantidade, data, estrutura=None, rolagem=None, 
                   transacoes=None, field_names=None): 
    """ 
    Valida os campos de entrada para os formulários de alteração e encerramento. 
    """ 
    field_names = field_names or ['ticker', 'valor', 'quantidade', 'data', 'estrutura', 'rolagem'] 
    errors = [] 
     
    # Ticker 
    ticker_result = validate_ticker(ticker) 
    if not ticker_result or not isinstance(ticker_result, tuple): 
        errors.append(f"{field_names[0]} inválido ou ausente") 
     
    # Valor opção 
    if not validate_numeric_positive(valor, field_names[1]): 
        errors.append(f"{field_names[1]} deve ser um valor positivo") 
     
    # Quantidade -   AGORA ACEITA VAZIO 
    if quantidade is not None and not validate_numeric_positive(quantidade, field_names[2]): 
        errors.append(f"{field_names[2]} deve ser um valor positivo") 
     
    # Data 
    validated_date = validate_date(data) 
    if not validated_date: 
        errors.append(f"{field_names[3]} inválida") 
     
    # Estrutura 
    if estrutura is not None and validate_structure(estrutura, transacoes) and not validate_required(estrutura, field_names[4]): 
        errors.append(f"{field_names[4]} obrigatória para operações multi-perna") 
     
    # Rolagem 
    if rolagem is not None and not isinstance(rolagem, (int, float)) and not str(rolagem).replace('.', '').replace('-', '').isdigit(): 
        errors.append(f"{field_names[5]} deve ser um valor numérico válido") 
     
    return errors 

def get_validation_tick(is_valid): 
    """Retorna ✔ ou × baseado em validação.""" 
    return '✔' if is_valid else '×' 
 
def validate_all_fields(ticker, direcao, qtd, valor, data_op, data_exerc, estrutura): 
    """Valida todos campos e retorna lista de ticks.""" 
    return [ 
        get_validation_tick(validate_ticker(ticker)), 
        get_validation_tick(bool(direcao)), 
        get_validation_tick(validate_numeric_positive(qtd, 'qtd')), 
        get_validation_tick(validate_numeric_positive(valor, 'valor')), 
        get_validation_tick(validate_date(data_op)), 
        get_validation_tick(validate_date(data_exerc)), 
        get_validation_tick(bool(estrutura)) 
    ]