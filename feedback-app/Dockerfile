FROM python:3.12-slim
WORKDIR /app
COPY standalone/requirements.txt standalone/requirements.txt
RUN pip install --no-cache-dir -r standalone/requirements.txt
COPY app.html app.html
COPY standalone/ standalone/
ENV DB_PATH=/data/cases.db PORT=8000
RUN mkdir -p /data
VOLUME /data
EXPOSE 8000
CMD ["sh", "-c", "gunicorn --chdir standalone -b 0.0.0.0:${PORT} -w 1 --threads 4 server:app"]
