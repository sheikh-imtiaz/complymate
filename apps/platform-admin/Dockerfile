# Next.js standalone image (Azure Container Apps / self-hosting). On AWS the app is deployed with Amplify Hosting.
FROM node:25-alpine AS deps
RUN corepack enable
WORKDIR /repo
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml* ./
COPY packages ./packages
COPY apps/platform-admin/package.json apps/platform-admin/package.json
RUN pnpm install --frozen-lockfile --filter @complymate/platform-admin...

FROM deps AS build
COPY apps/platform-admin apps/platform-admin
ARG NEXT_PUBLIC_API_URL NEXT_PUBLIC_WS_URL NEXT_PUBLIC_WS_MODE NEXT_PUBLIC_AUTH_MODE NEXT_PUBLIC_OIDC_ISSUER NEXT_PUBLIC_OIDC_CLIENT_ID NEXT_PUBLIC_OIDC_DOMAIN NEXT_PUBLIC_ENVIRONMENT
RUN pnpm --filter @complymate/platform-admin build

FROM node:25-alpine AS runtime
ENV NODE_ENV=production PORT=3001 HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /repo/apps/platform-admin/.next/standalone ./
COPY --from=build --chown=app:app /repo/apps/platform-admin/.next/static ./apps/platform-admin/.next/static
COPY --from=build --chown=app:app /repo/apps/platform-admin/public ./apps/platform-admin/public
USER app
EXPOSE 3001
CMD ["node", "apps/platform-admin/server.js"]
