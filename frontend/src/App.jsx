import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { LanguageProvider } from './context/LanguageContext';

import Login from './views/Login';
import Dashboard from './views/Dashboard';
import AdminPanel from './views/AdminPanel';
import TVDashboard from './views/TVDashboard';

// Route wrapper for authenticated users
const ProtectedRoute = ({ children }) => {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
        <div className="badge warning" style={{ padding: '12px 24px', fontSize: '1.1rem' }}>
          Loading...
        </div>
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Route wrapper to prevent logged in users from visiting login page
const AnonymousRoute = ({ children }) => {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
        <div className="badge warning" style={{ padding: '12px 24px', fontSize: '1.1rem' }}>
          Loading...
        </div>
      </div>
    );
  }

  if (token) {
    return <Navigate to="/" replace />;
  }

  return children;
};

function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public/Anonymous routes */}
              <Route 
                path="/login" 
                element={
                  <AnonymousRoute>
                    <Login />
                  </AnonymousRoute>
                } 
              />

              {/* Public routes */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/tv" element={<TVDashboard />} />
              
              {/* Protected routes */}
              <Route 
                path="/admin" 
                element={
                  <ProtectedRoute>
                    <AdminPanel />
                  </ProtectedRoute>
                } 
              />

              {/* Fallback redirect */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;
