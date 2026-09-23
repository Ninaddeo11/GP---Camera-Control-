FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* variables are inlined into the client bundle at build time
# by `next build` — setting them only as a runtime `environment:` in
# docker-compose.yml (as every other service in this project does) has no
# effect on them, since the code reading them has already been compiled
# away by then. They have to arrive as build args instead.
ARG NEXT_PUBLIC_API_BASE_URL=https://localhost/api
ARG NEXT_PUBLIC_GO2RTC_WHEP_BASE_URL=http://localhost:1984
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_GO2RTC_WHEP_BASE_URL=$NEXT_PUBLIC_GO2RTC_WHEP_BASE_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
