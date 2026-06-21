# Build Stage
FROM node:20-slim AS builder

WORKDIR /app

# Upgrade npm first (node:18 ships npm 9.x which has the optional-deps bug #4828)
RUN npm install -g npm@10

# Ignore host lockfile (generated on Windows — contains Windows-native binaries)
COPY package.json ./
RUN rm -f package-lock.json && npm install

# Manually install the matching Linux native binding (workaround for npm optional-deps bug #4828)
RUN OXIDE_VER=$(node -e "console.log(require('@tailwindcss/oxide/package.json').version)") && \
    npm install @tailwindcss/oxide-linux-x64-gnu@$OXIDE_VER

COPY . .

RUN npm run build

# Runner Stage
FROM node:20-slim

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json /app/package-lock.json ./

RUN npm install --omit=dev

ENV NODE_ENV=production \
    PORT=3000

EXPOSE 3000

CMD ["node", "dist/server.cjs"]
