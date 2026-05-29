FROM python:3.13

RUN apt-get update \
  && apt-get install -y unixodbc-dev krb5-user tdsodbc freetds-bin \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -s /bin/bash coursys

RUN pip install --upgrade pip
COPY requirements.txt /requirements.txt
RUN python3 -m pip install -r /requirements.txt

COPY docker/files/odbc.ini /etc/odbc.ini
COPY docker/files/krb5.conf /etc/krb5.conf
COPY docker/files/odbcinst.ini /etc/odbcinst.ini

USER coursys

CMD tsql -S ss-csrpt-db1.dc.sfu.ca -D CSRPT

