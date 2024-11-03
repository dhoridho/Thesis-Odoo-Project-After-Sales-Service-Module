# -*- coding: utf-8 -*-
from cryptography.fernet import Fernet
# from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
# import binascii
# import os
import json
import logging
_logger = logging.getLogger(__name__)


def hdencrypt(password, key=False):
    if key:
        ukey = bytes(key, 'UTF-8')
    else:
        ukey = Fernet.generate_key()
    fernet = Fernet(ukey)
    encMessage = fernet.encrypt(password.encode())
    return str(encMessage, 'UTF-8'), str(ukey, 'UTF-8')


def hddecrypt(password, key=False):
    if key:
        ukey = bytes(key, 'UTF-8')
    else:
        ukey = Fernet.generate_key()
    fernet = Fernet(ukey)
    upass = bytes(password, 'UTF-8')
    decMessage = fernet.decrypt(upass).decode()
    return decMessage

# def resize_length(string):
#     #resizes the String to a size divisible by 16 (needed for this Cipher)
#     return string.rjust((len(string) // 16 + 1) * 16)
#
# def mdencrypt(password, key=False):
#     if key:
#         ukey = bytes(key, 'UTF-8')
#     else:
#         ukey = os.urandom(32)
#     iv = os.urandom(16)
#     print(str(ukey.hex()), str(iv.hex()))
#     cipher = Cipher(algorithms.AES(ukey), modes.GCM(iv))
#     encryptor = cipher.encryptor()
#
#     # buf = bytearray(31)
#     # len_encrypted = encryptor.update_into(bytes(password, 'UTF-8'), buf)
#     # print(len_encrypted)
#     encryptor.authenticate_additional_data(bytes(password, 'UTF-8'))
#     ct = encryptor.update(bytes(password, 'UTF-8')) + encryptor.finalize()
#     print(str(ct.hex()))
#     return (str(ct.hex()), str(ukey.hex()), str(iv.hex()), encryptor.tag)
#
#
# def mddecrypt(password, key=False):
#     if key:
#         ukey = key.encode()
#     else:
#         ukey = os.urandom(32)
#     iv = os.urandom(16)
#     # Converts the string to bytes and decodes them with your Cipher
#     cipher = Cipher(algorithms.AES(ukey), modes.CBC(iv))
#     decryptor = cipher.decryptor()
#     dt = decryptor.update(password) + decryptor.finalize()
#     # return cipher.decrypt(password).decode().lstrip()
#     return dt.decode().ldstrip()

def log_request_error(param, req=None):
    try:
        param = json.dumps(param, indent=4, sort_keys=True, ensure_ascii=False)[:1000]
        if req is not None:
            _logger.error('\nSTATUS: %s\nSEND: %s\nRESULT: %s' %
                          (req.status_code, req.request.headers, req.text and req.text[:1000]))
    except Exception as _e:
        pass
    _logger.error(param, exc_info=True)
