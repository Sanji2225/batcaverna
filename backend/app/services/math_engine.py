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

    variaveis = list(expressao.free_symbols)
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
        "variables": [str(v) for v in variaveis]
    }