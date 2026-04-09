FROM nginx:1.27-alpine

# Bake nginx config into image to avoid host bind-mount issues on PaaS.
COPY nginx/nginx.conf /etc/nginx/nginx.conf
