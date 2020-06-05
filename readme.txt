 word2pdf的依赖性项安装
 1 jdk
 2 openoffice
 3 ./soffice -headless -accept="socket,host=127.0.0.1,port=10100;urp;" -nofirststartwizard &
。 4 将scripts下的service_of_word2pdf.py保存到openoffice的program路径下，并启动