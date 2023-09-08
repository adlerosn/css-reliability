FROM debian:12
RUN apt update
RUN apt install -y firefox-esr chromium nodejs python3 python3-pip python3-pillow python3-requests gstreamer1.0-plugins-good gstreamer1.0-plugins-bad libharfbuzz-icu0 libenchant-2-2 libhyphen0 libmanette-0.2-0
RUN mkdir -p /nonexistent
RUN chown 65534:65534 -R /nonexistent
USER 65534
RUN pip install --user --break-system-packages playwright
RUN /nonexistent/.local/bin/playwright install
USER 0
RUN mkdir -p /app
WORKDIR /app
ARG baseapi
ARG apikey
ENV baseapi $baseapi
ENV apikey $apikey
RUN echo $baseapi > /app/baseapi.txt
RUN echo $apikey > /app/apikey.txt
ADD updurl.txt /app/updurl.txt
ADD resolutions.json /app/resolutions.json
ADD client-dckshtr.py /app/client-dckshtr.py
RUN chmod 755 /app/client-dckshtr.py
RUN chown 65534:65534 -R /app
USER 65534
ENTRYPOINT [ "python3", "/app/client-dckshtr.py" ]