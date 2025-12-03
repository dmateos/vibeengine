/**
 * Get the API base URL based on the current hostname.
 * This allows the frontend to work in both local development and production.
 */
export const getApiBaseUrl = (): string => {
  const hostname = window.location.hostname;
  const protocol = window.location.protocol; // http: or https:

  console.log('[API Config] Current hostname:', hostname);
  console.log('[API Config] Current protocol:', protocol);

  // If accessing from dev0.lan.mateos.cc, use that for the API
  if (hostname === 'dev0.lan.mateos.cc') {
    const apiUrl = `${protocol}//dev0.lan.mateos.cc:8000/api`;
    console.log('[API Config] Using production API:', apiUrl);
    return apiUrl;
  }

  // If accessing from any non-localhost hostname, use that hostname for the API
  if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
    const apiUrl = `${protocol}//${hostname}:8000/api`;
    console.log('[API Config] Using hostname-based API:', apiUrl);
    return apiUrl;
  }

  // Default to localhost for local development
  const apiUrl = 'http://localhost:8000/api';
  console.log('[API Config] Using localhost API:', apiUrl);
  return apiUrl;
};

export const API_BASE_URL = getApiBaseUrl();
