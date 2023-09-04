FROM python
WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app
ENV VLOTT_USE_V1=0
EXPOSE 80
CMD ["python", "run.py"]
