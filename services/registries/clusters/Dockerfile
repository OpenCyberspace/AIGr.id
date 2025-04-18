# Use the official Node.js image.
FROM node:latest

# Create and change to the app directory.
WORKDIR /usr/src/app

# Install app dependencies.
COPY package*.json ./
RUN npm install

# Copy the app files.
COPY . .

# Expose the port the app runs on.
EXPOSE 3000

# Define environment variable.
ENV NODE_ENV production

# Start the app.
CMD [ "node", "index.js" ]
