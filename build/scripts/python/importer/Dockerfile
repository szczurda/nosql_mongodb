FROM python:3.10-slim

RUN pip install pymongo

WORKDIR /python

COPY ./importer/dataImport.py ./dataImport.py

CMD ["python3", "dataImport.py"]