# coding=utf-8
import socket


def turn_word_to_pdf(from_path, to_path):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    ip_port = ('127.0.0.1', 9999)
    client.connect(ip_port)
    client.send('{},{}'.format(from_path, to_path).encode('utf8'))
    r = client.recv(1024)
    client.close()
    result = r.decode('utf8')
    if result == 'ok':
        return True
    return False
