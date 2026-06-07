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
  const [learningRate, setLearningRate] = useState(0.5);
  const [stepSize, setStepSize] = useState(0.5);
  const [maxIter, setMaxIter] = useState(200);
  const [x0, setX0] = useState('3, 3');

  const [formula, setFormula] = useState('x^2 + 2y^2');
  const [constraint, setConstraint] = useState('');
  const [method, setMethod] = useState('gradiente');
  const [objective, setObjective] = useState('min');

  // Estados da Interface
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const mathFieldRef = useRef(null);
  const constraintFieldRef = useRef(null);

  // Escuta as mudanças no campo de fórmula
  useEffect(() => {
    const mf = mathFieldRef.current;
    if (mf) {
      mf.setValue(formula, { silenceInternalErrors: true });
      let timeoutId;
      const handleInput = () => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          setFormula(mf.getValue('latex'));
        }, 800); // 800ms de debounce
      };
      mf.addEventListener('input', handleInput);
      return () => {
        mf.removeEventListener('input', handleInput);
        clearTimeout(timeoutId);
      };
    }
  }, []);

  // Escuta as mudanças no campo de restrição
  useEffect(() => {
    const cf = constraintFieldRef.current;
    if (cf) {
      cf.setValue(constraint, { silenceInternalErrors: true });
      let timeoutId;
      const handleInput = () => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          setConstraint(cf.getValue('latex'));
        }, 800);
      };
      cf.addEventListener('input', handleInput);
      return () => {
        cf.removeEventListener('input', handleInput);
        clearTimeout(timeoutId);
      };
    }
  }, []);

  // Função que se comunica com o Backend
  const triggerScan = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg('');

    const startPoint = x0.split(',').map(v => parseFloat(v.trim()));
    if (startPoint.some(isNaN)) {
      setErrorMsg('Ponto inicial inválido. Use o formato: x, y');
      setIsLoading(false);
      return;
    }

    const payload = {
      method,
      formula,
      objective,
      constraints: constraint ? [constraint] : [],
      params: {
        learning_rate: learningRate,
        step_size: stepSize,
        max_iter: maxIter,
        x_inicial: startPoint
      }
    };

    const response = await requestOptimization(payload);

    if (response.success) {
      const data = response.data;
      if (method === 'gradiente') {
        setPath(data.path);
        setIterations(data.iterations);
      } else {
        // Para Direções Aleatórias, usamos o valor real de z inicial retornado pelo backend
        const pt = data.result.ponto_otimo;
        setPath({
          x: [startPoint[0], pt.x],
          y: [startPoint[1], pt.y],
          z: [data.result.valor_inicial, data.result.valor_otimo]
        });
        setIterations(data.result.iteracoes_realizadas);
      }
      setGrid(data.grid);
    } else {
      setErrorMsg(response.error);
    }

    setIsLoading(false);
  }, [formula, constraint, method, objective, learningRate, stepSize, maxIter, x0]);

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
        Batcomputador: Sistema de Otimização Restrita
      </h1>

      <div style={{ marginBottom: '30px', marginTop: '20px', padding: '20px', background: batColors.bgPanel, border: `1px solid ${batColors.border}`, borderRadius: '4px', boxShadow: `0 0 15px rgba(0,0,0,0.8)` }}>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '10px', color: batColors.yellow }}>
              Função Objetivo f(x,y):
            </label>
            <math-field ref={mathFieldRef} style={mathFieldStyle}></math-field>
          </div>
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '10px', color: batColors.yellow }}>
              Zona de Restrição g(x,y) ≤ 0:
            </label>
            <math-field ref={constraintFieldRef} style={mathFieldStyle}></math-field>
            <small style={{ color: '#888' }}>Deixe vazio para sem restrição</small>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', alignItems: 'flex-end', marginBottom: '20px' }}>
          <label style={controlLabelStyle}>
            Método:
            <select value={method} onChange={(e) => setMethod(e.target.value)} style={selectStyle}>
              <option value="gradiente">Gradiente</option>
              <option value="direcoes-aleatorias">Direções Aleatórias</option>
            </select>
          </label>

          <label style={controlLabelStyle}>
            Objetivo:
            <select value={objective} onChange={(e) => setObjective(e.target.value)} style={selectStyle}>
              <option value="min">Minimizar</option>
              <option value="max">Maximizar</option>
            </select>
          </label>

          <label style={controlLabelStyle}>
            Alpha:
            <input type="number" step="0.01" value={learningRate} onChange={(e) => {
              setLearningRate(e.target.value);
              setStepSize(e.target.value);
            }} style={inputStyle} />
          </label>

          <label style={controlLabelStyle}>
            Máx Iterações:
            <input type="number" value={maxIter} onChange={(e) => setMaxIter(e.target.value)} style={inputStyle} />
          </label>

          <label style={controlLabelStyle}>
            Ponto Inicial (x, y):
            <input type="text" value={x0} onChange={(e) => setX0(e.target.value)} style={inputStyle} />
          </label>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button onClick={triggerScan} disabled={isLoading} style={btnStyle}>
            {isLoading ? 'PROCESSANDO...' : 'INICIAR VARREDURA'}
          </button>
          {errorMsg && <p style={{ color: batColors.error, fontWeight: 'bold', margin: 0 }}>[ERRO]: {errorMsg}</p>}
        </div>

        <p style={{ marginTop: '20px', opacity: 0.8 }}>
          <strong>Telemetria:</strong> {isLoading ? 'Calculando trajetória...' : `Convergência em ${iterations} iterações.`}
          {!isLoading && path.x.length > 0 && (
            <span style={{ marginLeft: '20px', color: batColors.yellow }}>
              Ótimo em: <strong>({path.x[path.x.length - 1].toFixed(4)}, {path.y[path.y.length - 1].toFixed(4)})</strong>
              | Valor: <strong>{path.z[path.z.length - 1].toFixed(6)}</strong>
            </span>
          )}
        </p>
      </div>

      {!errorMsg && grid.z && grid.z.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '30px', opacity: isLoading ? 0.5 : 1, transition: 'opacity 0.3s' }}>
          <Plot
            data={[
              { z: grid.z, x: grid.x, y: grid.y, type: 'surface', opacity: 0.9, colorscale: batColorScale, showscale: false },
              { x: path.x, y: path.y, z: path.z, type: 'scatter3d', mode: 'lines+markers', marker: { color: batColors.yellow, size: 4 }, line: { color: batColors.yellow, width: 4 }, name: 'Trajetória' },
              { x: [path.x[path.x.length - 1]], y: [path.y[path.y.length - 1]], z: [path.z[path.z.length - 1]], type: 'scatter3d', mode: 'markers', marker: { color: '#FF0000', size: 8, symbol: 'diamond' }, name: 'Ponto Ótimo' }
            ]}
            layout={{ ...darkLayoutBase, width: 600, height: 500, title: 'Visualização Topográfica 3D' }}
          />

          <Plot
            data={[
              { z: grid.z, x: grid.x, y: grid.y, type: 'contour', colorscale: batColorScale, contours: { coloring: 'lines' }, showscale: false },
              { x: path.x, y: path.y, type: 'scatter', mode: 'lines+markers', marker: { color: batColors.yellow, size: 6 }, line: { color: batColors.yellow, width: 2 }, name: 'Deslocamento' },
              { x: [path.x[path.x.length - 1]], y: [path.y[path.y.length - 1]], type: 'scatter', mode: 'markers', marker: { color: '#FF0000', size: 12, symbol: 'x' }, name: 'Ponto Ótimo' }
            ]}
            layout={{ ...darkLayoutBase, width: 600, height: 500, title: 'Mapa de Isolinhas 2D' }}
          />

          <Plot
            data={[
              { x: iterArray, y: path.z, type: 'scatter', mode: 'lines+markers', marker: { color: batColors.yellow, size: 5 }, line: { color: batColors.yellow, width: 2 } },
            ]}
            layout={{
              ...darkLayoutBase, width: 1230, height: 400, title: 'Telemetria de Convergência (f(x,y) por Iteração)',
              xaxis: { title: 'Iterações', gridcolor: batColors.grid, zerolinecolor: batColors.grid },
              yaxis: { title: 'Valor do Alvo', gridcolor: batColors.grid, zerolinecolor: batColors.grid }
            }}
          />
        </div>
      )}
    </div>
  );
};

const mathFieldStyle = {
  fontSize: '20px', padding: '10px', backgroundColor: '#000',
  color: '#FCE205', border: '1px solid #FCE205',
  borderRadius: '4px', outline: 'none', width: '100%'
};

const controlLabelStyle = { display: 'inline-flex', flexDirection: 'column', fontWeight: 'bold', fontSize: '14px' };

const selectStyle = {
  marginTop: '5px', padding: '8px', background: '#000',
  color: '#FCE205', border: '1px solid #333', outline: 'none',
  fontFamily: 'inherit'
};

const inputStyle = {
  marginTop: '5px', padding: '8px', background: '#000',
  color: '#FCE205', border: '1px solid #333', outline: 'none',
  width: '100px', fontFamily: 'inherit'
};

const btnStyle = {
  padding: '12px 30px', cursor: 'pointer',
  background: '#FCE205', color: '#000', fontWeight: 'bold',
  border: 'none', borderRadius: '2px', textTransform: 'uppercase'
};

export default App;
