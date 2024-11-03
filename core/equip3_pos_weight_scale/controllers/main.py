# # -*- coding: utf-8 -*-
# # from odoo import http
# import datetime
#
# from odoo import http
# from odoo.http import request
# import json
# import sys,glob,re
# import serial
# class PosWeightMachine(http.Controller):
#
#     def serial_ports(self):
#         if sys.platform.startswith('win'):  # for windows
#             ports = ['COM%s' % (i + 1) for i in range(256)]
#         elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):  # for linux
#             # this excludes your current terminal "/dev/tty"
#             ports = glob.glob('/dev/tty[A-Za-z]*')
#         elif sys.platform.startswith('darwin'):
#             ports = glob.glob('/dev/tty.*')
#         else:
#             raise EnvironmentError('Unsupported platform')
#
#         result = []
#         for port in ports:
#             try:
#                 s = serial.Serial(port)
#                 s.close()
#                 result.append(port)
#             except (OSError, serial.SerialException):
#                 pass
#         return result
#
#     def func(self):
#         ports = self.serial_ports()
#         for port in ports:
#             print(port)
#             try:
#                 ser = serial.Serial(port,
#                                     baudrate=9600,
#                                     parity=serial.PARITY_EVEN,
#                                     stopbits=serial.STOPBITS_ONE,
#                                     bytesize=serial.SEVENBITS,
#                                     timeout=1)
#             except:
#                 print("error")
#                 continue
#             try:
#                 byt_data = ser.read(20)
#                 data = byt_data.decode('utf-8')
#                 weight = str(re.search(r"\d+(?:\.\d+)?", data))
#                 ser.close()
#                 return  weight
#             except:
#                 return 0
#     @http.route('/sendWeightRequest',methods=['POST', 'GET'], auth='public',type='json')
#     def send_weight_request(self,**kw):
#         weight = self.func()
#         return weight