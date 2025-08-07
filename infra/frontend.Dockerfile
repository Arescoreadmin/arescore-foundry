FROM node:20-alpine
WORKDIR /app
COPY frontend/package.json frontend/vite.config.js ./
COPY frontend/src ./src
COPY frontend/index.html ./
RUN npm install
EXPOSE 3000
CMD ["npm", "start"]
