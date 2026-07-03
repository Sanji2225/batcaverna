import axios from 'axios';

const apiURL = process.env.REACT_APP_API_URL || '';

// Configuração base do Axios
const api = axios.create({
    baseURL: apiURL,
    headers: {
        'Content-Type': 'application/json'
    }
});

/**
 * Envia uma fórmula e restrições para o backend realizar a otimização.
 * @param {Object} payload { method, formula, objective, constraints, params }
 */
export const requestOptimization = async ({ method, formula, objective, constraints, params }) => {
    const endpoint = method === 'gradiente' ? '/api/optimizer/gradiente' : '/api/optimizer/direcoes-aleatorias';
    
    try {
        const response = await api.post(endpoint, {
            funcao_latex: formula,
            restricoes_latex: constraints || [],
            objetivo: objective,
            parametros: params
        });

        return {
            success: true,
            data: response.data.data
        };

    } catch (error) {
        console.error('Erro na requisição API:', error);
        const errorMessage = error.response?.data?.error || 
                             error.response?.data?.message || 
                             'Erro de conexão com o servidor.';
        
        return {
            success: false,
            error: errorMessage
        };
    }
};

export default api;
