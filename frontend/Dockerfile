FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# In Docker, the backend is at http://backend:8000
ENV NEXT_PUBLIC_API_URL=http://backend:8000

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
