FROM node:26-alpine AS build
RUN corepack enable
WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
# VITE_API_URL vacío: el navegador llama al mismo origen y nginx reenvía al backend
ARG VITE_API_URL=
ARG VITE_APP_TITLE="Agente IA - Panel de Configuración"
ENV VITE_API_URL=$VITE_API_URL VITE_APP_TITLE=$VITE_APP_TITLE
RUN pnpm build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
