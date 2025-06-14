# wizard/service_request_cancel_wizard.py
from odoo import models, fields, api
from odoo.exceptions import UserError


class ServiceRequestCancelWizard(models.TransientModel):
    _name = 'service.request.cancel.wizard'
    _description = 'Service Request Cancel Wizard'

    service_request_id = fields.Many2one('service.request', string='Service Request', required=True)
    cancel_reason = fields.Selection([
        ('customer_request', 'Customer Request'),
        ('technical_issue', 'Technical Issue'),
        ('parts_unavailable', 'Parts Unavailable'),
        ('cost_concern', 'Cost Concern'),
        ('duplicate_request', 'Duplicate Request'),
        ('out_of_warranty', 'Out of Warranty'),
        ('other', 'Other'),
    ], string='Cancel Reason', required=True)

    cancel_notes = fields.Text(string='Additional Notes')
    notify_customer = fields.Boolean(string='Notify Customer', default=True)

    def action_confirm_cancel(self):
        """Confirm the cancellation with reason"""
        self.ensure_one()

        if not self.service_request_id:
            raise UserError('Service Request is required.')

        if self.service_request_id.state in ['completed', 'cancelled']:
            raise UserError('You cannot cancel a request that is already completed or cancelled.')

        # Update the service request
        self.service_request_id.write({
            'state': 'cancelled',
            'cancel_reason': self.cancel_reason,
            'cancel_notes': self.cancel_notes,
            'cancelled_by': self.env.user.id,
            'cancelled_date': fields.Datetime.now(),
        })

        # Add message to chatter
        reason_label = dict(self._fields['cancel_reason'].selection)[self.cancel_reason]
        message = f"Service request cancelled. </b>Reason: {reason_label}"
        if self.cancel_notes:
            message += f"\n</b>Notes: {self.cancel_notes}"

        self.service_request_id.message_post(
            body=message,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )

        # Send email notification if requested
        if self.notify_customer:
            template = self.env.ref('after_sales_service.email_template_service_cancel', raise_if_not_found=False)
            if template and self.service_request_id.partner_id.email:
                # Pass cancel reason and notes to email template context
                template.with_context({
                    'cancel_reason': reason_label,
                    'cancel_notes': self.cancel_notes,
                }).send_mail(self.service_request_id.id, force_send=True)

        return {'type': 'ir.actions.act_window_close'}