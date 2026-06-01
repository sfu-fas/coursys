# This is a minimal dockerfile intended to test CSRPT connections. Do not emulate this style for production. Probably.

FROM ubuntu:26.04

RUN sed -i -e 's/http:\/\/archive\.ubuntu\.com\/ubuntu/http:\/\/mirror.rcg.sfu.ca\/mirror\/ubuntu/' /etc/apt/sources.list.d/ubuntu.sources
RUN sed -i -e 's/http:\/\/security.ubuntu.com\/ubuntu/http:\/\/mirror.rcg.sfu.ca\/mirror\/ubuntu/' /etc/apt/sources.list.d/ubuntu.sources

RUN apt-get update \
  && apt-get install -y python3-pip python3 \
  && apt-get install -y locales-all npm libfreetype-dev default-mysql-client \
  && apt-get install -y unixodbc-dev krb5-user tdsodbc freetds-bin \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
  && apt-get install -y libmariadb-dev pkg-config \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 12345 -s /bin/bash coursys

#RUN pip install --upgrade pip
COPY requirements.txt /requirements.txt
RUN python3 -m pip install -r /requirements.txt --break-system-packages

COPY docker/files/odbc.ini /etc/odbc.ini
COPY docker/files/krb5.conf /etc/krb5.conf
COPY docker/files/odbcinst.ini /etc/odbcinst.ini

COPY ./krb5cc_11713 /tmp/krb5cc_12345
RUN chown coursys /tmp/krb5cc_12345 && chmod 0700 /tmp/krb5cc_12345


USER coursys
#CMD tsql -S ss-csrpt-db1.dc.sfu.ca -D CSRPT
