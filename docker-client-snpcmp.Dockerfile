FROM alpine:3.18
RUN apk add python3 py3-pillow py3-requests py3-numpy py3-pandas
RUN mkdir -p /app
WORKDIR /app
ARG baseapi
ARG apikey
ENV baseapi $baseapi
ENV apikey $apikey
RUN echo $baseapi > /app/baseapi.txt
RUN echo $apikey > /app/apikey.txt
ADD updurl.txt /app/updurl.txt
ADD client-snpcmp.py /app/client-snpcmp.py
RUN chmod 755 /app/client-snpcmp.py
RUN chown nobody:nobody -R /app
USER nobody
ENTRYPOINT [ "python3", "/app/client-snpcmp.py" ]