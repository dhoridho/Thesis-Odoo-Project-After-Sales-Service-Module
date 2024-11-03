from odoo import models, fields, api, exceptions, _
from datetime import datetime, date, timedelta

class CommisionDetail(models.Model):
    _name = 'sh.commision.detail'

    sales_amount = fields.Float()
    collection_amount = fields.Float()
    commision = fields.Float()
    target_commision_id = fields.Many2one('sh.target.commision')