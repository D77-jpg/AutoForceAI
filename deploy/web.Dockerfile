FROM node:20-bookworm-slim AS build
WORKDIR /workspace/apps/web-console
COPY packages/ui-tokens/ /workspace/packages/ui-tokens/
COPY apps/web-console/package.json apps/web-console/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/web-console/ ./
# Same-origin public API calls must go to HTTPS ingress; server-side rewrites
# are built with an internal backend destination, not a browser-visible host.
ARG NEXT_PUBLIC_API_URL=
ARG INTERNAL_API_URL=http://backend:8010
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} INTERNAL_API_URL=${INTERNAL_API_URL}
RUN npm run build

FROM node:20-bookworm-slim
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build --chown=node:node /workspace/apps/web-console/.next/standalone ./
COPY --from=build --chown=node:node /workspace/apps/web-console/.next/static ./apps/web-console/.next/static
COPY --from=build --chown=node:node /workspace/apps/web-console/public ./apps/web-console/public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 CMD node -e "fetch('http://127.0.0.1:3000/login').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "apps/web-console/server.js"]
