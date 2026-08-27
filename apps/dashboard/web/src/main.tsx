import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';
import './editorial.css';

const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('找不到 #root 挂载节点');

createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
