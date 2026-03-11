const AUTH_EVENT = "auth-change";

export function setToken(token: string) {
  localStorage.setItem("token", token);
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function removeToken() {
  localStorage.removeItem("token");
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function getToken(): string | null {
  return localStorage.getItem("token");
}

export { AUTH_EVENT };
