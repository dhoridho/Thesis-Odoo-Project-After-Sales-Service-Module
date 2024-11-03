# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from datetime import date, datetime, timedelta as td
from odoo.exceptions import UserError

class AcsWhatsappHistory(models.TransientModel):
    _name = "acs.whatsapp.history"
    _description = "WhatsApp Chat History"

    data =  fields.Html(string='WhatsApp Chat')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
