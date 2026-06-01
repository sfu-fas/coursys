# This is a minimal dockerfile intended to test CSRPT connections. Do not emulate this style for production. Probably.

FROM python:3.14

# packages we need: for the app itself to run; build dependencies; for CSRPT auth/connection
RUN apt-get update \
  && apt-get install -y locales-all npm libfreetype-dev default-mysql-client \
  && apt-get install -y libmariadb-dev pkg-config \
  && apt-get install -y unixodbc-dev krb5-user tdsodbc freetds-bin \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# this UID must match the UID of the account outside of docker that is doing the CSRPT kinit auth: /tmp/krb5cc_${UID} is mounted into the container
ARG UID="6501"
RUN useradd --uid ${UID} -s /bin/bash coursys

#RUN pip install --upgrade pip
COPY requirements.txt /requirements.txt
RUN python3 -m pip install -r /requirements.txt --break-system-packages

COPY docker/files/odbc.ini /etc/odbc.ini
COPY docker/files/krb5.conf /etc/krb5.conf
COPY docker/files/odbcinst.ini /etc/odbcinst.ini

#COPY /tmp/krb5cc_${UID} /tmp/krb5cc_${UID}
#RUN chown coursys /tmp/krb5cc_${UID} && chmod 0700 /tmp/krb5cc_${UID}

USER coursys
#CMD tsql -S ss-csrpt-db1.dc.sfu.ca -D CSRPT
