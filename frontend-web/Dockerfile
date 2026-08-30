FROM node:20-alpine AS base

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# BACKEND_URL is read server-side by next.config.js's rewrites() at process
# startup (not baked in at build time like a NEXT_PUBLIC_* var) -- set it at
# `docker run`/compose time, not here.
ENV NEXT_TELEMETRY_DISABLED 1
ENV NODE_ENV production
ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
