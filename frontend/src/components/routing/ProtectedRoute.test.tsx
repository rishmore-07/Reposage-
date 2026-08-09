import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { ProtectedRoute } from './ProtectedRoute';
import { useAuthStore } from '@/lib/auth-store';

describe('ProtectedRoute', () => {
  it('redirects to login when unauthenticated', () => {
    useAuthStore.setState({ isAuthenticated: false });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <div>Dashboard Content</div>
              </ProtectedRoute>
            } 
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard Content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    useAuthStore.setState({ isAuthenticated: true });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <div>Dashboard Content</div>
              </ProtectedRoute>
            } 
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Dashboard Content')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });
});
