// src/App.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import Plot from 'react-plotly.js';
import 'mathlive';
import { requestOptimization } from './services/api';

const App = () => {
  // Estados da Aplicação
  const [path, setPath] = useState({ x: [], y: [], z: [] });
  const [grid, setGrid] = useState({ x: [], y: [], z: [] });
  const [iterations, setIterations] = useState(0);
  const [learningRate, setLearningRate] = useState(0.1);
  const [formula, setFormula] = useState('x^2 + 2*y^2');

  // Estados da Interface
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const mathFieldRef = useRef(null);

  // Escuta as mudanças no campo de fórmula
  useEffect(() => {
    const mf = mathFieldRef.current;
    if (mf) {
      const handleInput = () => setFormula(mf.getValue('ascii-math'));
      mf.addEventListener('input', handleInput);
      return () => mf.removeEventListener('input', handleInput);
    }
  }, []);

  // Função que se comunica com o "Backend"
  const triggerScan = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg('');

    // Chama o serviço (que hoje é o Mock, amanhã será o Flask)
    const response = await requestOptimization({ formula, learningRate });

    if (response.success) {
      setPath(response.data.path);
      setGrid(response.data.grid);
      setIterations(response.data.iterations);
    } else {
      setErrorMsg(response.error);
    }

    setIsLoading(false);
  }, [formula, learningRate]);

  // Executa uma varredura automática ao montar ou ao mudar a taxa
  useEffect(() => {
    triggerScan();
  }, [triggerScan]);

  const iterArray = path.z ? path.z.map((_, i) => i) : [];

  // Paleta de cores da Batcaverna
  const batColors = {
    bgFull: '#050505', bgPanel: '#111111', text: '#E0E0E0',
    yellow: '#FCE205', grid: '#333333', border: '#2A2A2A', error: '#FF4444'
  };

  const darkLayoutBase = {
    paper_bgcolor: batColors.bgPanel, plot_bgcolor: batColors.bgPanel,
    font: { color: batColors.text, family: '"Courier New", Courier, monospace' },
    margin: { t: 50, b: 50, l: 50, r: 50 }
  };

  const batColorScale = [[0, '#000000'], [0.5, '#222222'], [1, '#555555']];

  return (
    <div style={{ padding: '30px', fontFamily: '"Courier New", Courier, monospace', backgroundColor: batColors.bgFull, color: batColors.text, minHeight: '100vh' }}>
      <h1 style={{ textTransform: 'uppercase', letterSpacing: '2px', borderBottom: `2px solid ${batColors.yellow}`, paddingBottom: '10px', display: 'inline-block' }}>
        Batcomputador: Análise de Gradiente Dinâmico
      </h1>

      <div style={{ marginBottom: '30px', marginTop: '20px', padding: '20px', background: batColors.bgPanel, border: `1px solid ${batColors.border}`, borderRadius: '4px', boxShadow: `0 0 15px rgba(0,0,0,0.8)` }}>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '10px', color: batColors.yellow }}>
            Função Objetivo Alvo f(x,y):
          </label>
          <math-field
            ref={mathFieldRef}
            style={{
              fontSize: '24px', padding: '10px', backgroundColor: '#000',
              color: batColors.yellow, border: `1px solid ${batColors.yellow}`,
              borderRadius: '4px', outline: 'none', width: '100%', maxWidth: '400px'
            }}
          >
            x^2 + 2y^2
          </math-field>
          {errorMsg && <p style={{ color: batColors.error, marginTop: '10px', fontWeight: 'bold' }}>[ERRO]: {errorMsg}</p>}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
          <button
            onClick={triggerScan}
            disabled={isLoading}
            style={{
              padding: '12px 24px', cursor: isLoading ? 'wait' : 'pointer',
              background: batColors.yellow, color: '#000', fontWeight: 'bold',
              border: 'none', borderRadius: '2px', textTransform: 'uppercase',
              opacity: isLoading ? 0.6 : 1
            }}
          >
            {isLoading ? 'PROCESSANDO...' : 'Nova Varredura Aleatória'}
          </button>

          <label style={{ display: 'inline-flex', alignItems: 'center', fontWeight: 'bold' }}>
            Valor de Alpha (Taxa de Aprendizado):
            <input
              type="number" step="0.01" value={learningRate}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                if (!isNaN(val)) setLearningRate(val);
              }}
              disabled={isLoading}
              style={{
                marginLeft: '15px', padding: '8px', background: '#000',
                color: batColors.yellow, border: `1px solid ${batColors.yellow}`,
                outline: 'none', fontFamily: 'inherit'
              }}
            />
          </label>
        </div>

        <p style={{ marginTop: '20px', opacity: 0.8 }}>
          <strong>Status da Calibração:</strong> {isLoading ? 'Aguardando dados do servidor...' : `Mínimo localizado em ${iterations} iterações.`}
        </p>
      </div>

      {/* Renderiza os gráficos apenas se tiver dados do Grid e não houver erros fatais */}
      {!errorMsg && grid.z.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '30px', opacity: isLoading ? 0.5 : 1, transition: 'opacity 0.3s' }}>
          <Plot
            data={[
              { z: grid.z, x: grid.x, y: grid.y, type: 'surface', opacity: 0.9, colorscale: batColorScale, showscale: false },
              { x: path.x, y: path.y, z: path.z, type: 'scatter3d', mode: 'lines+markers', marker: { color: batColors.yellow, size: 4 }, line: { color: batColors.yellow, width: 4 }, name: 'Trajetória' },
            ]}
            layout={{
              ...darkLayoutBase, width: 600, height: 500, title: '1. Mapeamento Topográfico (3D)',
              scene: {
                xaxis: { gridcolor: batColors.grid, zerolinecolor: batColors.text, showbackground: false },
                yaxis: { gridcolor: batColors.grid, zerolinecolor: batColors.text, showbackground: false },
                zaxis: { gridcolor: batColors.grid, zerolinecolor: batColors.text, showbackground: false }
              }
            }}
          />

          <Plot
            data={[
              { z: grid.z, x: grid.x, y: grid.y, type: 'contour', colorscale: batColorScale, contours: { coloring: 'lines' }, line: { width: 1, color: '#444' }, showscale: false },
              { x: path.x, y: path.y, type: 'scatter', mode: 'lines+markers', marker: { color: batColors.yellow, size: 6, symbol: 'cross' }, line: { color: batColors.yellow, width: 2 }, name: 'Deslocamento' },
            ]}
            layout={{
              ...darkLayoutBase, width: 600, height: 500, title: '2. Varredura de Setor (2D)',
              xaxis: { gridcolor: batColors.grid, zerolinecolor: batColors.grid },
              yaxis: { gridcolor: batColors.grid, zerolinecolor: batColors.grid }
            }}
          />

          <Plot
            data={[
              { x: iterArray, y: path.z, type: 'scatter', mode: 'lines+markers', marker: { color: batColors.yellow, size: 5 }, line: { color: batColors.yellow, width: 2 } },
            ]}
            layout={{
              ...darkLayoutBase, width: 600, height: 400, title: '3. Telemetria de Convergência',
              xaxis: { title: 'Iterações', gridcolor: batColors.grid, zerolinecolor: batColors.grid },
              yaxis: { title: 'Valor do Alvo', gridcolor: batColors.grid, zerolinecolor: batColors.grid }
            }}
          />
        </div>
      )}
    </div>
  );
};

export default App;