export default {
  apiBase: "/api",
  cognitoDomain: "https://YOUR-DOMAIN.auth.us-east-1.amazoncognito.com",
  clientId: "YOUR-APP-CLIENT-ID",
  redirectUri: `${window.location.origin}/`,
  scopes: "openid email",
  mock: false,
};
