import { test, expect } from '@playwright/test';
import { getCurrentUser, isAuthenticated, login, logout } from '../src/auth';

test.describe('User Authentication', () => {
  test.beforeEach(() => {
    logout();
  });

  test('should return correct current user', () => {
    login('test', 'password');
    const user = getCurrentUser();
    expect(user.id).toBe('user-123');
    expect(user.name).toBe('Test User');
  });

  test('should be authenticated after login', () => {
    const result = login('test', 'password');
    expect(result).toBe(true);
    expect(isAuthenticated()).toBe(true);
  });
});
