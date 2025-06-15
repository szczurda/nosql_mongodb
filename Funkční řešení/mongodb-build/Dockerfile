FROM mongo:8.0.10
COPY /auth/mongodb-keyfile /data
RUN chmod 400 /data/mongodb-keyfile
RUN chown 999:999 /data/mongodb-keyfile