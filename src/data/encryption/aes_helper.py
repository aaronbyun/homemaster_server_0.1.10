#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import binascii
from Crypto.Cipher import AES
import base64
from err.error_handler import print_err_detail, err_dict

def aes_encrypt(data, key):
    try:
        cipher = AES.new(key)
        data = data + (u" " * (16 - (len(data) % 16)))
        return binascii.hexlify(cipher.encrypt(data))
    except Exception, e:
        print_err_detail(e)

def aes_decrypt(data, key):
    cipher = AES.new(key)
    return cipher.decrypt(binascii.unhexlify(data)).rstrip()


class MyCrypto2:
    def __init__(self, secret):
        BLOCK_SIZE = 16
        PADDING = '|'
        cipher = AES.new(secret)

        pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING

        self.encodeAES = lambda s: base64.b64encode(cipher.encrypt(pad(s)))
        self.decodeAES = lambda e: cipher.decrypt(base64.b64decode(e)).rstrip(PADDING) if e != None else ''

    def encodeAES(self, data):
        encoded = self.encodeAES(data)
        return encoded

    def decodeAES(self, data):
        decoded = self.decodeAES(data)
        return decoded


class MyCrypto:
    def __init__(self, secret):
        BLOCK_SIZE = 16
        self.secret = secret


    def encodeAES(self, data):
        expected_length = 16 * ((len(data) / 16) + 1)
        padding_length = expected_length - len(data)
        data = data + chr(padding_length) * padding_length

        cipher = AES.new(self.secret)

        encoded = base64.b64encode(cipher.encrypt(data))

        return encoded

    def decodeAES(self, data):
        try:
            cipher = AES.new(self.secret)
            data = base64.b64decode(data)
            dec = cipher.decrypt(data)

            if '\x00' in dec:   # Python-mysql은 padding으로 \x00을 사용한다.
                dec = dec[:dec.index('\x00')]

            # MySQL은 Padding으로 더해진 문자열 갯수를 사용한다.
            last = dec[len(dec) - 1]
            dec = dec[:-ord(last)]
        except Exception, e:
            print e
            return ''

        return dec

if __name__ == '__main__':
    crypto = MyCrypto('mE6NLdKhGjBpklzg')

    #encode = crypto.encodeAES('Dongjo Seo')
    #print encode
    print crypto.decodeAES('mITTyNN+JFTXQwOKOoByQ5hMqGoGq+Fn8Ec81ghnQ5pnV8xFQz0g3G8ojoz0SPzVYrjE4KDNw2MkzqulhPq8LZfJEbfuQVmmWfGX/xxh7izf4sgzLHNXGF4eLP19InV+')
    print crypto.decodeAES('3FYn/715CpFTS9wke6p+BQ==')
    print crypto.decodeAES('gpeHnOwGWaRw5pzE6mDzmw==')

    #G7kJAl+E2rCESsTU9McTS2n80tF7msAlpzGGY/oQ5/g=
