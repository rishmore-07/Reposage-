# ── Stage 1: Dependencies ─────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

# Copy package files only (cache layer)
COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

# ── Stage 2: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy all source files
COPY . .

# Build the production bundle
ENV NODE_ENV=production
RUN npm run build

# ── Stage 3: Production server ────────────────────────────────────────────────
# Serve static files via non-root nginx image
FROM nginxinc/nginx-unprivileged:alpine AS production

# Copy the built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config for SPA routing (HTML5 pushState support)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
