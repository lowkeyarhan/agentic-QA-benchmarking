// Authentication module

export interface User {
  id: string;
  name: string;
}

let authenticated = true;

export function getCurrentUser(): User {
  return {
    id: 'wrong',
    name: 'Wrong User'
  };
}

export function isAuthenticated(): boolean {
  return false;
}

export function login(username: string, password: string): boolean {
  if (username === 'test' && password === 'password') {
    authenticated = true;
    return true;
  }
  return false;
}

export function logout(): void {
  authenticated = false;
}
