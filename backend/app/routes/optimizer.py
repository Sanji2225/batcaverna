from flask import Blueprint, request, jsonify
from app.services.math_engine import process_latex_function, rodar_direcoes_aleatorias

optimizer_bp = Blueprint('optimizer', __name__)

def pre_processamento(dados):
    """
    Função auxiliar interna para validar o payload e a linearidade 
    antes de rodar qualquer algoritmo de otimização.
    """
    latex_str = dados.get('funcao_latex')
    objetivo = dados.get('objetivo') # Tem que ser 'max' ou 'min'

    if not latex_str:
        return {"valido": False, "codigo": 400, "resposta": {"error": "O campo 'funcao_latex' é obrigatório."}}
    
    if objetivo not in ['max', 'min']:
        return {"valido": False, "codigo": 400, "resposta": {"error": "O campo 'objetivo' deve ser 'max' ou 'min'."}}

    try:
        resultado_math = process_latex_function(latex_str)

        if resultado_math['is_linear']:
            return {
                "valido": False, 
                "codigo": 400, 
                "resposta": {
                    "error": "Modelo Linear detectado.",
                    "message": "Os métodos de otimização suportam exclusivamente funções não lineares.",
                    "detalhes": resultado_math
                }
            }
            
        return {"valido": True, "dados_matematicos": resultado_math, "objetivo": objetivo}

    except ValueError as e:
        return {"valido": False, "codigo": 400, "resposta": {"error": str(e)}}
    except Exception as e:
        return {"valido": False, "codigo": 500, "resposta": {"error": "Erro interno no processamento matemático.", "details": str(e)}}


@optimizer_bp.route('/direcoes-aleatorias', methods=['POST'])
def otimizar_direcoes_aleatorias():
    dados = request.json
    validacao = pre_processamento(dados)

    if not validacao['valido']:
        return jsonify(validacao['resposta']), validacao['codigo']

    dados_math = validacao['dados_matematicos']
    objetivo = validacao['objetivo']

    parametros = dados.get('parametros', {})
    step_size = parametros.get('step_size', 0.1)
    max_iter = parametros.get('max_iter', 1000)
    x_inicial = parametros.get('x_inicial', None)

    try:
        # Extrai (e remove do dicionário) os objetos SymPy puros
        expressao_sympy = dados_math.pop('sympy_expr')
        variaveis_sympy = dados_math.pop('sympy_vars')

        # Executa o cálculo com os objetos 
        resultado_otimizacao = rodar_direcoes_aleatorias(
            expressao_sympy=expressao_sympy,
            variaveis_sympy=variaveis_sympy,
            objetivo=objetivo,
            x_inicial=x_inicial,
            step_size=step_size,
            max_iter=max_iter
        )

        # Retorna o JSON. 
        return jsonify({
            "status": "sucesso",
            "metodo": "Direções Aleatórias",
            "objetivo": objetivo.upper(),
            "dados_interpretados": dados_math, 
            "resultado": resultado_otimizacao
        }), 200

    except Exception as e:
        return jsonify({
            "status": "erro",
            "error": "Falha interna ao executar o algoritmo de otimização.",
            "detalhes": str(e)
        }), 500


@optimizer_bp.route('/gradiente', methods=['POST'])
def otimizar_gradiente():
    """
    Endpoint: POST /api/optimizer/gradiente
    Payload esperado: {"funcao_latex": "...", "objetivo": "max" ou "min"}
    """
    dados = request.json
    validacao = pre_processamento(dados)

    if not validacao['valido']:
        return jsonify(validacao['resposta']), validacao['codigo']

    dados_math = validacao['dados_matematicos']
    objetivo = validacao['objetivo']

    # ==============================================================
    # AQUI ENTRARÁ A LÓGICA FUTURA DO MÉTODO DO GRADIENTE
    # Exemplo: 
    # resultado_final = rodar_descida_ascensao_gradiente(dados_math['parsed_expression'], objetivo)
    # ==============================================================

    # Remove os objetos SymPy para não dar erro no retorno temporário
    dados_math.pop('sympy_expr', None)
    dados_math.pop('sympy_vars', None)
    
    # Retorno temporário (Mock) para o Frontend testar
    return jsonify({
        "status": "sucesso",
        "metodo": "Gradiente",
        "objetivo": objetivo.upper(),
        "mensagem": "Função não linear validada. (Cálculo real do algoritmo será implementado aqui)",
        "dados_interpretados": dados_math
    }), 200
