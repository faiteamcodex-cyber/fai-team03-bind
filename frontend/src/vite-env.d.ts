// Ambient types for Vite environment variables used by BIND.
// `types: ["vite/client"]` in tsconfig.app.json provides the base ImportMetaEnv.
// Keep this list in sync with .env.example — never read `import.meta.env.X` for an
// undeclared variable, it is a typo waiting to happen.

interface ImportMetaEnv {
  /** BIND API Gateway base URL (ap-south-1). Empty until the backend deploys. */
  readonly VITE_API_BASE_URL?: string
  /** 'true' → mockApi fixtures; 'false' → live API Gateway. */
  readonly VITE_USE_MOCK_API?: string
  /** Dev/preview port, used when allow-listing CORS on the AWS side. */
  readonly VITE_DEV_PORT?: string
  /** Comma-separated extra hostnames the dev server may be reached through. */
  readonly VITE_ALLOWED_HOSTS?: string
  /** Optional GeoJSON fixture/endpoint used by the map until Member 3 delivers data. */
  readonly VITE_GEOJSON_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
