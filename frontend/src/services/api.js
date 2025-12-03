import axios from 'axios';

// Support both build-time (import.meta.env) and runtime (window._env_) environment variables
const getEnv = (key, defaultValue) => {
  // Runtime config (from Docker container)
  if (window._env_ && window._env_[key]) {
    return window._env_[key];
  }
  // Build-time config (from .env file during development)
  return import.meta.env[key] || defaultValue;
};

const API_BASE_URL = getEnv('VITE_API_BASE_URL', 'http://localhost:8000');
const API_VERSION = getEnv('VITE_API_VERSION', 'v1');

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

api.interceptors.request.use(
  (config) => {
    if (getEnv('VITE_DEBUG', 'false') === 'true') {
      console.log('API Request:', config);
    }
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    if (getEnv('VITE_DEBUG', 'false') === 'true') {
      console.log('API Response:', response);
    }
    return response;
  },
  (error) => {
    console.error('API Response Error:', error);

    if (error.response) {
      console.error('Error Data:', error.response.data);
      console.error('Error Status:', error.response.status);
    } else if (error.request) {
      console.error('No response received');
    } else {
      console.error('Request setup error:', error.message);
    }

    return Promise.reject(error);
  }
);

export const scoreTransaction = async (transactionData) => {
  const response = await api.post('/transaction/score', transactionData);
  return response.data;
};

export const getTransactionHistory = async (limit = 100) => {
  const response = await api.get('/data/history', {
    params: { limit },
  });
  return response.data;
};

export const getMetrics = async () => {
  const response = await api.get('/data/metrics');
  return response.data;
};

export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
