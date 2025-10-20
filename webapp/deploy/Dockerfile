# Stage 1: Build
FROM node:20-buster AS builder

WORKDIR /app

# Copy package files and install dependencies
COPY package.json yarn.lock ./
RUN yarn install

# Copy the rest of the application
COPY . .

# Set production environment and build the project
ENV NODE_ENV=production
ENV NODE_OPTIONS="--max-old-space-size=2048"
RUN yarn build

# Stage 2: Final image
FROM node:20-slim

WORKDIR /app

# Copy the built application from builder stage
COPY --from=builder /app ./

# Expose the port
EXPOSE 3001

# Set production environment
ENV NODE_ENV=production

# Start the application
CMD ["yarn", "start", "--port", "3001"]
