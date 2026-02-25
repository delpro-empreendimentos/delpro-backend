# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
# envsubst replaces only ${FASTAPI_HOST} and ${FASTAPI_PORT}, leaving nginx
# variables like $host and $remote_addr untouched.
CMD ["/bin/sh", "-c", "envsubst '${FASTAPI_HOST} ${FASTAPI_PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
