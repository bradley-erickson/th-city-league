FROM python:3.9
COPY requirements.txt /
RUN pip3 install --upgrade pip
RUN pip3 install -r /requirements.txt
COPY . /app
WORKDIR /app
EXPOSE 8000
CMD ["gunicorn",  "-b", "0.0.0.0:8000", "-w", "4", "app:server"]
