# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    user_name = fields.Char(string='User Name')
    user_name_param = fields.Char(string='User Name Parameter', default="uname")
    password = fields.Char(string='Password')
    password_param = fields.Char(string='Password Parameter', default="pass")
    sender_id = fields.Char(string='Sender')
    sender_param = fields.Char(string='Sender Parameter', default="source")
    message_param = fields.Char(string='Message Parameter', default="message")
    receiver_param = fields.Char(string='Receiver Parameter', default="destination")
    extra_param = fields.Char(string='Extra Parameter', default="")

    url = fields.Char(string='URL', default='http://www.unicel.in/SendSMS/sendmsg.php?')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: