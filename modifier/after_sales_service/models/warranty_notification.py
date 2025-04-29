from odoo import models, fields, api
from datetime import datetime, timedelta

class WarrantyNotification(models.Model):
    _name = 'warranty.notification'
    _description = 'Warranty Notification'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    warranty_end_date = fields.Date('Warranty End Date', required=True)
    notification_sent = fields.Boolean('Notification Sent', default=False)
    notification_status = fields.Selection([
        ('no', 'No'),
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ], string='Notification Sent Status', default='no')
    days_remaining = fields.Integer(string='Days Remaining', compute='_compute_days_remaining', store=True)

    @api.depends('warranty_end_date')
    def _compute_days_remaining(self):
        """Compute the number of days remaining until the warranty expires."""
        for record in self:
            if record.warranty_end_date:
                today = fields.Date.today()
                record.days_remaining = (record.warranty_end_date - today).days
            else:
                record.days_remaining = 0

    # def send_warranty_notifications(self):
    #     """Send email notifications for warranties expiring in 7 days."""
    #     today = fields.Date.today()
    #     seven_days_later = today + timedelta(days=7)
    #     notifications = self.search([
    #         ('warranty_end_date', '=', seven_days_later),
    #         ('notification_status', '=', 'no')
    #     ])
    #     for notification in notifications:
    #         notification.notification_status = 'sent'
    #         template = self.env.ref('after_sales_service.warranty_notification_email_template')
    #         template.send_mail(notification.id, force_send=True)

    def action_send_warranty_notifications(self):
        self.send_warranty_notifications()
