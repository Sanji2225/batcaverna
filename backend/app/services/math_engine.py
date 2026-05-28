import math
import random
import sympy as sp
from sympy.parsing.latex import parse_latex
from sympy.parsing.latex.errors import LaTeXParsingError

def process_latex_function(latex_str):
    """
    Motor matemático: Converte o modelo LaTeX (que vem da lib Mathlive.io do front) para sympy e realiza a análise de linearidade.
    """
    try:
        expressao = parse_latex(latex_str).doit()
    except LaTeXParsingError:
        raise ValueError("O formato LaTeX fornecido é inválido ou não suportado.")
    except Exception as e:
        raise ValueError(f"Erro ao processar o modelo matemático: {str(e)}")

    variaveis = sorted(list(expressao.free_symbols), key=lambda x: x.name)
    is_linear = True
    
    if variaveis:
        try:
            polinomio = sp.Poly(expressao, *variaveis)
            if polinomio.total_degree() > 1:
                is_linear = False
        except sp.PolynomialError:
            is_linear = False
            
    return {
        "parsed_expression": str(expressao),
        "is_linear": is_linear,
        "variables": [str(v) for v in variaveis],
        "sympy_expr": expressao,
        "sympy_vars": variaveis
    }

def gerar_grid(expressao_sympy, variaveis_sympy, range_val=5, step=0.5):
    """
    Gera a malha topográfica (Grid 3D) para o frontend.
    Suporta apenas 2 variáveis (x e y).
    """
    if len(variaveis_sympy) != 2:
        return None

    # Garante que a ordem seja x, y
    vars_map = {v.name: v for v in variaveis_sympy}
    x_sym = vars_map.get('x')
    y_sym = vars_map.get('y')

    if not x_sym or not y_sym:
        return None

    func = sp.lambdify((x_sym, y_sym), expressao_sympy, modules=['math'])

    x_vals = []
    y_vals = []
    curr = -float(range_val)
    while curr <= range_val:
        x_vals.append(round(curr, 2))
        y_vals.append(round(curr, 2))
        curr += step

    z_vals = []
    for xv in x_vals:
        row = []
        for yv in y_vals:
            try:
                row.append(float(func(xv, yv)))
            except (ValueError, ZeroDivisionError, TypeError):
                row.append(0.0)
        z_vals.append(row)

    return {"x": x_vals, "y": y_vals, "z": z_vals}

def rodar_gradiente(expressao_sympy, variaveis_sympy, objetivo, x_inicial=None, step_size=0.1, max_iter=100, tolerance=0.01):
    """
    Executa a Descida/Ascensão do Gradiente.
    """
    if len(variaveis_sympy) != 2:
        raise ValueError("O método do gradiente nesta implementação suporta exatamente 2 variáveis (x e y).")

    vars_map = {v.name: v for v in variaveis_sympy}
    x_sym = vars_map.get('x')
    y_sym = vars_map.get('y')

    if not x_sym or not y_sym:
        raise ValueError("Variáveis 'x' e 'y' não encontradas para o método do gradiente.")

    # Derivadas
    dx = sp.diff(expressao_sympy, x_sym)
    dy = sp.diff(expressao_sympy, y_sym)

    # Funções executáveis
    f_func = sp.lambdify((x_sym, y_sym), expressao_sympy, modules=['math'])
    dx_func = sp.lambdify((x_sym, y_sym), dx, modules=['math'])
    dy_func = sp.lambdify((x_sym, y_sym), dy, modules=['math'])

    if x_inicial is None:
        curr_x = random.uniform(-4, 4)
        curr_y = random.uniform(-4, 4)
    else:
        curr_x, curr_y = x_inicial

    hist_x = [curr_x]
    hist_y = [curr_y]
    hist_z = [float(f_func(curr_x, curr_y))]

    is_max = (objetivo.lower() == 'max')
    mult = 1 if is_max else -1

    iter_count = 0
    for _ in range(max_iter):
        try:
            gx = float(dx_func(curr_x, curr_y))
            gy = float(dy_func(curr_x, curr_y))
        except (ValueError, ZeroDivisionError):
            break

        grad_norm = math.sqrt(gx**2 + gy**2)
        if grad_norm < tolerance:
            break

        curr_x = curr_x + mult * step_size * gx
        curr_y = curr_y + mult * step_size * gy

        hist_x.append(curr_x)
        hist_y.append(curr_y)
        hist_z.append(float(f_func(curr_x, curr_y)))
        
        iter_count += 1

    return {
        "path": {"x": hist_x, "y": hist_y, "z": hist_z},
        "iterations": iter_count,
        "ponto_otimo": {"x": curr_x, "y": curr_y},
        "valor_otimo": hist_z[-1]
    }
    
def rodar_direcoes_aleatorias(expressao_sympy, variaveis_sympy, objetivo, x_inicial=None, step_size=0.1, max_iter=1000):
    """
    Executa o método de otimização por Direções Aleatórias recebendo 
    diretamente os objetos SymPy (Sem necessidade de parse_expr).
    """
    n_vars = len(variaveis_sympy)
    
    # Verifica se a função possui variáveis
    if n_vars == 0:
        return {
            "ponto_otimo": {},
            "valor_otimo": float(expressao_sympy),
            "iteracoes_realizadas": 0,
            "mensagem": "A função é constante, não há variáveis para otimizar."
        }

    # Converte para uma função executável
    func = sp.lambdify(variaveis_sympy, expressao_sympy, modules=['math'])

    if x_inicial is None:
        x_atual = [0.0] * n_vars
    else:
        x_atual = [float(x) for x in x_inicial]

    try:
        f_atual = func(*x_atual)
    except Exception as e:
        raise ValueError(f"Erro ao calcular a função no ponto inicial: {str(e)}")

    is_max = (objetivo.lower() == 'max')

    # Loop Principal do Algoritmo
    for _ in range(max_iter):
        direcao = [random.gauss(0.0, 1.0) for _ in range(n_vars)]
        
        norma = math.sqrt(sum(d**2 for d in direcao))
        if norma == 0:
            continue
            
        direcao_normalizada = [d / norma for d in direcao]
        x_novo = [x_atual[i] + step_size * direcao_normalizada[i] for i in range(n_vars)]
        
        try:
            f_novo = func(*x_novo)
        except (ValueError, ZeroDivisionError):
            continue

        melhorou = (f_novo > f_atual) if is_max else (f_novo < f_atual)

        if melhorou:
            x_atual = x_novo
            f_atual = f_novo

    # Estruturação do resultado final
    vars_str_list = [str(v) for v in variaveis_sympy]
    resultado = {
        "ponto_otimo": {var_nome: float(val) for var_nome, val in zip(vars_str_list, x_atual)},
        "valor_otimo": float(f_atual),
        "iteracoes_realizadas": max_iter,
        "step_size_utilizado": step_size
    }
    
    return resultado
