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
        ('manual_send', 'Manually Sent'),
        ('auto_send', 'Automatically Sent'),
        ('failed', 'Failed')
    ], string='Notification Sent Status', default='no')
    days_remaining = fields.Integer(string='Days Remaining', compute='_compute_days_remaining', store=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True, default=lambda self: self.env.company)

    @api.depends('warranty_end_date')
    def _compute_days_remaining(self):
        """Compute the number of days remaining until the warranty expires."""
        for record in self:
            if record.warranty_end_date:
                today = fields.Date.today()
                record.days_remaining = (record.warranty_end_date - today).days
            else:
                record.days_remaining = 0

    def send_warranty_notifications(self):
        """Send email notifications for warranties expiring in 7 days."""
        for record in self:
            record.notification_status = 'manual_send'
            template = record.env.ref('after_sales_service.warranty_notification_email_template')
            template.with_context(company=self.env.company).send_mail(record.id, force_send=True)

    def cron_send_warranty_notifications(self):
        """Update days remaining and send warranty expiration emails for warranties expiring in 7 days."""

        # Step 1: Recompute days_remaining for all notifications
        all_notifications = self.env['warranty.notification'].search([])
        all_notifications._compute_days_remaining()

        # Step 2: Calculate target date (7 days from today)
        today = fields.Date.today()
        target_date = today + timedelta(days=7)

        # Step 3: Search notifications where warranty will expire in 7 days and hasn't been sent yet
        notifications_to_send = self.env['warranty.notification'].search([
            ('warranty_end_date', '=', target_date),
            ('notification_status', '=', 'no')
        ])

        # Step 4: Send emails
        template = self.env.ref('after_sales_service.warranty_notification_email_template')
        for notification in notifications_to_send:
            template.with_context(company=notification.env.company).send_mail(notification.id, force_send=True)
            notification.notification_status = 'auto_send'

    def action_send_warranty_notifications(self):
        self.send_warranty_notifications()
