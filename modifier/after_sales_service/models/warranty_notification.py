from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.fields import Date

class WarrantyNotification(models.Model):
    _name = 'warranty.notification'
    _description = 'Warranty Notification'

    name = fields.Char(string='Notification Reference', required=True, copy=False, readonly=True, default='New')
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

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            partner_id = vals.get('partner_id')
            product_id = vals.get('product_id')
            warranty_end_date = vals.get('warranty_end_date')

            if partner_id and product_id and warranty_end_date:
                partner = self.env['res.partner'].browse(partner_id)
                product = self.env['product.product'].browse(product_id)
                formatted_date = Date.to_string(Date.from_string(warranty_end_date))
                vals['name'] = f"{partner.name}/{product.name}/{formatted_date}"

        return super(WarrantyNotification, self).create(vals)

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
