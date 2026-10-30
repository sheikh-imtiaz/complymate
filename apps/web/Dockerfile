# Next.js standalone image (Azure Container Apps / self-hosting). On AWS the app is deployed with Amplify Hosting.
FROM node:25-alpine AS deps
RUN corepack enable
WORKDIR /repo
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml* ./
COPY packages ./packages
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile --filter @complymate/web...

FROM deps AS build
COPY apps/web apps/web
ARG NEXT_PUBLIC_API_URL NEXT_PUBLIC_WS_URL NEXT_PUBLIC_WS_MODE NEXT_PUBLIC_AUTH_MODE NEXT_PUBLIC_OIDC_ISSUER NEXT_PUBLIC_OIDC_CLIENT_ID NEXT_PUBLIC_OIDC_DOMAIN NEXT_PUBLIC_ENVIRONMENT
RUN pnpm --filter @complymate/web build

FROM node:25-alpine AS runtime
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /repo/apps/web/.next/standalone ./
COPY --from=build --chown=app:app /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=app:app /repo/apps/web/public ./apps/web/public
USER app
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
