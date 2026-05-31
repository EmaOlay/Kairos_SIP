# Etapa de construccion
FROM node:25.0.0-slim AS build-stage

WORKDIR /app

# Copiar dependencias
COPY package*.json ./
RUN npm install

# Copiar codigo y build
COPY . .
RUN npm run build

# Etapa de produccion
FROM nginx:stable-alpine AS production-stage

# Copiar archivos estaticos desde la etapa de build
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copiar configuracion de nginx (opcional, para manejar rutas de SPA)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
