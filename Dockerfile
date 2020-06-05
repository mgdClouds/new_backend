FROM python:3.6-slim

WORKDIR /opt/newcom

COPY . .

RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    cp sources.list /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y nginx supervisor libpoppler-qt5-dev poppler-utils wget && \
    wget https://newcom-local.oss-cn-beijing.aliyuncs.com/dependence.tar.gz && \
    tar -zxvf dependence.tar.gz && \
    tar -zxvf dependence/jdk.tar.gz -C /opt/ && \
    tar -zxvf dependence/OpenOffice.tar.gz -C ./dependence/ && \
    dpkg -i dependence/zh-CN/DEBS/*.deb && \
    tar -zxvf dependence/win.tar.gz -C /usr/share/fonts/ && \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ gunicorn setuptools supervisor && \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r scripts/requirements.txt && \
    rm /etc/nginx/sites-enabled/default -rf dependence.tar.gz dependence /var/lib/apt/lists/* && \
    ln -s /etc/nginx/sites-available/newcom_b.conf /etc/nginx/sites-enabled/newcom_b.conf && \
    echo "daemon off;" >> /etc/nginx/nginx.conf && \
    mkdir -p /var/log/supervisor && \
    cp scripts/nginx.conf /etc/nginx/sites-available/newcom_b.conf && \
    cp scripts/service_of_word2pdf.py_ /opt/openoffice4/program/t.py && \
    cp -R scripts/supervisor/* /etc/supervisor/ && \
    apt-get --purge -y remove wget && \
    apt-get clean autoclean autoremove

ENV JAVA_HOME=/opt/jdk1.8.0_201 PATH=$JAVA_HOME/bin:$PATH CONFIG=/usr/local/bin CONFIG=/opt/newcom

EXPOSE 5000
CMD ["supervisord","-c","/etc/supervisor/supervisord.conf"]