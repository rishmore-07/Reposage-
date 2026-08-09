import type { Mock } from 'vitest';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from './auth-store';

// Mock the api-client
vi.mock('./api-client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  }
}));

import apiClient from './api-client';

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset state before each test
    useAuthStore.setState({ user: null, isAuthenticated: false });
    vi.clearAllMocks();
  });

  it('initializes with unauthenticated state', () => {
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });

  it('setUser updates the state correctly', () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      full_name: 'Test',
      avatar_url: null,
      github_username: null,
      is_active: true,
      is_email_verified: true,
      is_superuser: false,
    };

    useAuthStore.getState().setUser(mockUser);
    
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user).toEqual(mockUser);
  });

  it('logout clears the state', () => {
    // @ts-expect-error - Mocking partial user object for testing
    useAuthStore.setState({ isAuthenticated: true, user: { id: '123' } });
    
    useAuthStore.getState().logout();
    
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });

  it('initializeAuth successfully sets user', async () => {
    const mockUser = { id: '123', email: 'test@example.com' };
    (apiClient.get as Mock).mockResolvedValue({ data: mockUser });

    await useAuthStore.getState().initializeAuth();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user).toEqual(mockUser);
  });

  it('initializeAuth handles failure and clears state', async () => {
    // @ts-expect-error - Mocking partial user object for testing
    useAuthStore.setState({ isAuthenticated: true, user: { id: '123' } });
    
    (apiClient.get as Mock).mockRejectedValue(new Error('Unauthorized'));

    await useAuthStore.getState().initializeAuth();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });
});
