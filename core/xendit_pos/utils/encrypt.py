# -*- coding: utf-8 -*-
from ast import In, Or
import base64
from operator import or_
from cryptography.fernet import Fernet
from os import path

def generateKey():
    """
    Generates a key and save it into a file
    """
    return Fernet.generate_key()

def generateFernet(key):
    return Fernet(key)

def encrypt(str, key):
    fernet = generateFernet(key)
    return fernet.encrypt(str.encode())

def decrypt(str, key):
    """
    Decrypts an encrypted string
    """
    fernet = generateFernet(key)
    decryptedString = fernet.decrypt(bytes(str, 'utf-8'))
    return decryptedString.decode()