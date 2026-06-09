import { useState, useMemo, createContext, useContext, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { lightTheme, darkTheme } from './theme/theme';
import Layout from './components/layout/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import EvaluationPage from './pages/EvaluationPage';
import HistoryPage from './pages/HistoryPage';
import type { EvaluationResponse } from './types';
import { api } from './services/api';
import './index.css';

// ─── Theme Context ───
interface ThemeContextType {
  isDark: boolean;
  toggleTheme: () => void;
}

export const ThemeContext = createContext<ThemeContextType>({
  isDark: false,
  toggleTheme: () => {},
});

export const useThemeContext = () => useContext(ThemeContext);

// ─── Evaluation Context ───
interface EvalContextType {
  currentEvaluation: EvaluationResponse | null;
  setCurrentEvaluation: (e: EvaluationResponse | null) => void;
  evaluationHistory: EvaluationResponse[];
  addEvaluation: (e: EvaluationResponse) => void;
  deleteEvaluation: (id: string) => void;
}

export const EvalContext = createContext<EvalContextType>({
  currentEvaluation: null,
  setCurrentEvaluation: () => {},
  evaluationHistory: [],
  addEvaluation: () => {},
  deleteEvaluation: () => {},
});

export const useEvalContext = () => useContext(EvalContext);

function App() {
  // Theme
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('theme_mode');
    return saved === 'dark';
  });

  const toggleTheme = () => {
    setIsDark((prev) => {
      const next = !prev;
      localStorage.setItem('theme_mode', next ? 'dark' : 'light');
      return next;
    });
  };

  const theme = useMemo(() => (isDark ? darkTheme : lightTheme), [isDark]);

  // Evaluation state
  const [currentEvaluation, setCurrentEvaluation] = useState<EvaluationResponse | null>(null);
  const [evaluationHistory, setEvaluationHistory] = useState<EvaluationResponse[]>([]);

  const addEvaluation = (e: EvaluationResponse) => {
    setEvaluationHistory((prev) => [e, ...prev]);
    setCurrentEvaluation(e);
  };

  const deleteEvaluation = (id: string) => {
    setEvaluationHistory((prev) => prev.filter((item) => item.evaluation_id !== id));
    setCurrentEvaluation((prev) => (prev?.evaluation_id === id ? null : prev));
  };

  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      api.getHistory()
        .then((response) => {
          const history = response.data;
          setEvaluationHistory(history);
          if (history.length > 0) {
            setCurrentEvaluation((prev) => (prev === null || prev === undefined ? history[0] : prev));
          }
        })
        .catch((err) => {
          console.error('Failed to fetch evaluation history:', err);
        });
    }
  }, [isAuthenticated]);
  return (
    <ThemeContext.Provider value={{ isDark, toggleTheme }}>
      <EvalContext.Provider
        value={{ currentEvaluation, setCurrentEvaluation, evaluationHistory, addEvaluation, deleteEvaluation }}
      >
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <BrowserRouter>
            <Routes>
              <Route
                path="/login"
                element={
                  isAuthenticated ? (
                    <Navigate to="/" replace />
                  ) : (
                    <LoginPage onLogin={() => setIsAuthenticated(true)} />
                  )
                }
              />
              <Route
                path="/*"
                element={
                  isAuthenticated ? (
                    <Layout onLogout={() => setIsAuthenticated(false)}>
                      <Routes>
                        <Route path="/" element={<DashboardPage />} />
                        <Route path="/evaluate" element={<EvaluationPage />} />
                        <Route path="/history" element={<HistoryPage />} />
                      </Routes>
                    </Layout>
                  ) : (
                    <Navigate to="/login" replace />
                  )
                }
              />
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </EvalContext.Provider>
    </ThemeContext.Provider>
  );
}

export default App;
