FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --include=dev

COPY frontend/ ./
RUN npm test
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY infra/local/nginx.conf /etc/nginx/conf.d/default.conf
