from odoo import models, fields, api

class WarrantyNotification(models.Model):
    _name = 'warranty.notification'

    customer_id = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.product', string='Product')
    warranty_end_date = fields.Date('Warranty End Date')
    notification_sent = fields.Boolean('Notification Sent')
