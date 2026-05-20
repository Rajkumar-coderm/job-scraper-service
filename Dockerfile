FROM python:3.11

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

RUN playwright install

EXPOSE 8000

CMD ["python", "run.py"]
