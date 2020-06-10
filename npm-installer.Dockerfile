FROM node:14

COPY package.json /
COPY package-lock.json /

WORKDIR /
CMD ["npm", "install"]