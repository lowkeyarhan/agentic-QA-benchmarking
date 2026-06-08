// User service with bugs
export interface User {
  id: string;
  name: string;
  email: string;
}

// BUG: Returns wrong user
export function getCurrentUser(): User {
  return { id: 'wrong', name: 'Wrong User', email: 'wrong@test.com' };
}

// BUG: Always returns false
export function isAuthenticated(): boolean {
  return false;
}
