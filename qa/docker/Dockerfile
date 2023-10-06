FROM python:3.9

WORKDIR /app

COPY requirements.txt /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

RUN python -m spacy download en_core_web_sm

COPY . /app

# Run main.py when the container launches
CMD ["python", "main.py"]
