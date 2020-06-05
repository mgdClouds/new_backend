from captcha.image import ImageCaptcha
import base64
import hashlib
from datetime import datetime
from random import Random


def generate_code_string(random_length=6, char_type='number'):
    code = ''
    if char_type == 'number':
        chars = '0123456789'
    elif char_type == 'lower':
        chars = '0123456789abcdefghijklmnopqrstuvwxyz'
    elif char_type == 'upper':
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    else:
        chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    length = len(chars) - 1
    random = Random()
    for i in range(random_length):
        code += chars[random.randint(0, length)]
    return code
WESTPAY_TIMESTAMP = '%Y%m%d%H%M%S'


class CaptchasConfig(object):
    def __init__(self):
        self.debug = True
        self.key = 'thisisakey'


class CaptchaService:
    config = CaptchasConfig()

    def gen_sign(self, key, code, timestamp):
        origin = key
        origin += 'code'
        origin += code
        origin += 'timestamp'
        origin += timestamp
        origin += key
        sign = hashlib.md5(bytearray(origin, 'utf_8')).hexdigest().upper()
        return sign

    def generate_captcha(self, code=None):
        if code is None:
            code = generate_code_string(4, 'number')

        image = ImageCaptcha()
        captcha_buffer = image.generate(code)
        image_buffer = base64.b64encode(captcha_buffer.getvalue()).decode("utf-8")
        image = 'data:image/png;base64,{0}'.format(image_buffer)
        timestamp = datetime.now()
        timestamp = timestamp.strftime(WESTPAY_TIMESTAMP)
        sign = self.gen_sign(self.config.key, code.lower(), timestamp)
        return {
            'image': image,
            'sign': sign,
            'timestamp': timestamp
        }

    def verify_sign(self, code, timestamp, sign):
        if self.config.debug:
            return True
        check_sign = self.gen_sign(self.config.key, code.lower(), timestamp)
        return check_sign == sign
