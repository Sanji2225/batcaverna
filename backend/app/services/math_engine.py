import math
import random
import sympy as sp
from sympy.parsing.latex import parse_latex
from sympy.parsing.latex.errors import LaTeXParsingError

def process_latex_function(latex_str, constraints_latex=None):
    """
    Motor matemático: Converte o modelo LaTeX para sympy e realiza a análise de linearidade.
    Também processa as restrições se fornecidas.
    """
    try:
        expressao = parse_latex(latex_str).doit()
    except LaTeXParsingError:
        raise ValueError("O formato LaTeX da função é inválido.")
    except Exception as e:
        raise ValueError(f"Erro ao processar a função: {str(e)}")

    variaveis = sorted(list(expressao.free_symbols), key=lambda x: x.name)
    is_linear = True
    
    if variaveis:
        try:
            polinomio = sp.Poly(expressao, *variaveis)
            if polinomio.total_degree() > 1:
                is_linear = False
        except sp.PolynomialError:
            is_linear = False

    restricoes_sympy = []
    if constraints_latex:
        for c_latex in constraints_latex:
            if not c_latex.strip(): continue
            try:
                # Assume restrições no formato g(x,y) <= 0
                c_expr = parse_latex(c_latex).doit()
                restricoes_sympy.append(c_expr)
            except Exception:
                continue
            
    return {
        "parsed_expression": str(expressao),
        "is_linear": is_linear,
        "variables": [str(v) for v in variaveis],
        "sympy_expr": expressao,
        "sympy_vars": variaveis,
        "sympy_constraints": restricoes_sympy
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

def avaliar_restricoes(ponto_vals, variaveis_sympy, restricoes_sympy):
    """
    Verifica se um ponto viola alguma restrição g(x) <= 0.
    """
    v_map = {v: val for v, val in zip(variaveis_sympy, ponto_vals)}
    for r in restricoes_sympy:
        if float(r.subs(v_map)) > 0:
            return False
    return True

def rodar_gradiente(expressao_sympy, variaveis_sympy, objetivo, restricoes_sympy=None, x_inicial=None, step_size=0.1, max_iter=100, tolerance=0.01):
    """
    Executa a Descida/Ascensão do Gradiente com suporte a restrições simples (Barreira/Penalidade).
    """
    restricoes_sympy = restricoes_sympy or []
    if len(variaveis_sympy) != 2:
        raise ValueError("O método do gradiente nesta implementação suporta exatamente 2 variáveis (x e y).")

    vars_map = {v.name: v for v in variaveis_sympy}
    x_sym = vars_map.get('x')
    y_sym = vars_map.get('y')

    f_func = sp.lambdify((x_sym, y_sym), expressao_sympy, modules=['math'])
    dx_func = sp.lambdify((x_sym, y_sym), sp.diff(expressao_sympy, x_sym), modules=['math'])
    dy_func = sp.lambdify((x_sym, y_sym), sp.diff(expressao_sympy, y_sym), modules=['math'])

    if x_inicial is None:
        curr_x, curr_y = 0.0, 0.0
    else:
        curr_x, curr_y = x_inicial

    hist_x, hist_y, hist_z = [curr_x], [curr_y], [float(f_func(curr_x, curr_y))]
    is_max = (objetivo.lower() == 'max')
    mult = 1 if is_max else -1

    for _ in range(max_iter):
        try:
            gx, gy = float(dx_func(curr_x, curr_y)), float(dy_func(curr_x, curr_y))
        except (ValueError, ZeroDivisionError): break

        if math.sqrt(gx**2 + gy**2) < tolerance: break

        prox_x = curr_x + mult * step_size * gx
        prox_y = curr_y + mult * step_size * gy

        # Verifica restrição
        if restricoes_sympy and not avaliar_restricoes([prox_x, prox_y], variaveis_sympy, restricoes_sympy):
            # Se violar, tentamos um passo menor ou paramos aqui para simplificar
            step_size *= 0.5
            if step_size < 1e-6: break
            continue

        curr_x, curr_y = prox_x, prox_y
        hist_x.append(curr_x); hist_y.append(curr_y); hist_z.append(float(f_func(curr_x, curr_y)))

    return {
        "path": {"x": hist_x, "y": hist_y, "z": hist_z},
        "iterations": len(hist_x),
        "ponto_otimo": {"x": curr_x, "y": curr_y},
        "valor_otimo": hist_z[-1]
    }
    
def rodar_direcoes_aleatorias(expressao_sympy, variaveis_sympy, objetivo, restricoes_sympy=None, x_inicial=None, step_size=0.1, max_iter=1000):
    """
    Otimização por Direções Aleatórias com suporte a restrições.
    """
    restricoes_sympy = restricoes_sympy or []
    n_vars = len(variaveis_sympy)
    if n_vars == 0:
        return {"ponto_otimo": {}, "valor_otimo": float(expressao_sympy), "iteracoes_realizadas": 0}

    func = sp.lambdify(variaveis_sympy, expressao_sympy, modules=['math'])
    x_atual = [float(x) for x in x_inicial] if x_inicial else [0.0] * n_vars
    f_atual = func(*x_atual)
    is_max = (objetivo.lower() == 'max')

    for _ in range(max_iter):
        direcao = [random.gauss(0.0, 1.0) for _ in range(n_vars)]
        norma = math.sqrt(sum(d**2 for d in direcao))
        if norma == 0: continue
            
        x_novo = [x_atual[i] + step_size * (direcao[i]/norma) for i in range(n_vars)]
        
        try:
            # Verifica restrições antes de aceitar o novo ponto
            if restricoes_sympy and not avaliar_restricoes(x_novo, variaveis_sympy, restricoes_sympy):
                continue
            
            f_novo = func(*x_novo)
            if (f_novo > f_atual) if is_max else (f_novo < f_atual):
                x_atual, f_atual = x_novo, f_novo
        except (ValueError, ZeroDivisionError): continue

    vars_str_list = [str(v) for v in variaveis_sympy]
    return {
        "ponto_otimo": {name: val for name, val in zip(vars_str_list, x_atual)},
        "valor_otimo": float(f_atual),
        "iteracoes_realizadas": max_iter
    }
