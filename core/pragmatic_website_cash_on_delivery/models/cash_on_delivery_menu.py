from odoo import api, fields, models,_
from odoo.exceptions import ValidationError,RedirectWarning,UserError
import re

class CashDelivery(models.Model):
    _name= "cash.delivery"
    _description='Cash Delivery'
    _rec_name = 'cash_on_delivery_msg'
  
    cash_on_delivery_msg = fields.Text(string='Message')
   
