FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create .env file if it doesn't exist
RUN if [ ! -f .env ]; then echo "REACT_APP_API_URL=http://localhost:5000/api" > .env; fi

# Build the application
RUN npm run build

# Use nginx to serve the built application
FROM nginx:alpine

# Copy built application to nginx
COPY --from=0 /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
