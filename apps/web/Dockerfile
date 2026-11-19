# ==============================================================================
# ARTHSAVORA Web Frontend Multi-Stage Production Dockerfile
# Builds TypeScript monorepo packages, bundles Vite client, and serves via Nginx.
# ==============================================================================

# --- Stage 1: Monorepo Build Environment ---
FROM node:22-alpine AS builder

WORKDIR /app

# Enable corepack and prepare pnpm
RUN corepack enable && corepack prepare pnpm@12.18.0 --activate

# Copy root monorepo package configuration and lockfile
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Copy packages and apps package configurations
COPY packages/contracts/package.json ./packages/contracts/
COPY packages/design-tokens/package.json ./packages/design-tokens/
COPY packages/utilities/package.json ./packages/utilities/
COPY packages/validation/package.json ./packages/validation/
COPY apps/web/package.json ./apps/web/

# Install all monorepo dependencies with frozen lockfile
RUN pnpm install --frozen-lockfile

# Copy source code across packages and web application
COPY packages/ ./packages/
COPY apps/web/ ./apps/web/

# Build internal shared library packages
RUN pnpm -r run build

# Build production Vite web application bundle
RUN pnpm --filter @arthsavora/web build

# --- Stage 2: Production Nginx Server ---
FROM nginx:1.27-alpine AS runner

# Remove default nginx static assets and config
RUN rm -rf /usr/share/nginx/html/* && \
    rm -f /etc/nginx/conf.d/default.conf

# Copy custom hardened nginx configuration
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled SPA bundle and public PWA assets from builder stage
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Healthcheck targeting nginx health probe
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost/nginx-health || exit 1

CMD ["nginx", "-g", "daemon off;"]
