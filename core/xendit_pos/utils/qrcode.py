# -*- coding: utf-8 -*-
from ast import In, Or
import base64
from operator import or_
import qrcode
import io

class Qrcode():

    def initQrCode(self):
        return qrcode.QRCode(  
            version = 1,
            error_correction = qrcode.constants.ERROR_CORRECT_L,
            box_size = 10,
            border = 4,
        )  

    def generateQrCode(self, xendit_invoice_url):
        qrcode = self.initQrCode()
        qrcode.add_data(xendit_invoice_url)
        qrcode.make(fit = True)
        qrcode_image = qrcode.make_image(fill_color = 'black', back_color = 'transparent')
        stream = io.BytesIO()
        qrcode_image.save(stream)
        return base64.b64encode(stream.getvalue()).decode('utf-8')

    def renderQrcode(self, xendit_invoice_url, echo = False, width = 180, height= 180):
        qrcode_image = self.generateQrCode(xendit_invoice_url)
        return 'data:image/png;base64,{}'.format(qrcode_image)

