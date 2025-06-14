# wizard/warranty_claim_cancel_wizard.py
from odoo import models, fields, api
from odoo.exceptions import UserError


class WarrantyClaimCancelWizard(models.TransientModel):
    _name = 'warranty.claim.cancel.wizard'
    _description = 'Warranty Claim Cancel Wizard'

    warranty_claim_id = fields.Many2one('warranty.claim', string='Warranty Claim', required=True)
    cancel_reason = fields.Selection([
        ('customer_request', 'Customer Request'),
        ('out_of_warranty', 'Out of Warranty Period'),
        ('invalid_claim', 'Invalid Warranty Claim'),
        ('user_damage', 'User/Accidental Damage'),
        ('manufacturing_defect_excluded', 'Manufacturing Defect Excluded'),
        ('incomplete_documentation', 'Incomplete Documentation'),
        ('duplicate_claim', 'Duplicate Claim'),
        ('product_modification', 'Product Modified/Tampered'),
        ('normal_wear_tear', 'Normal Wear and Tear'),
        ('misuse', 'Product Misuse'),
        ('parts_unavailable', 'Warranty Parts Unavailable'),
        ('technical_assessment_failed', 'Failed Technical Assessment'),
        ('other', 'Other'),
    ], string='Cancel Reason', required=True)

    cancel_notes = fields.Text(string='Additional Notes')
    notify_customer = fields.Boolean(string='Notify Customer', default=True)

    def action_confirm_cancel(self):
        """Confirm the cancellation with reason"""
        self.ensure_one()

        if not self.warranty_claim_id:
            raise UserError('Warranty Claim is required.')

        if self.warranty_claim_id.state in ['completed', 'cancelled']:
            raise UserError('You cannot cancel a claim that is already completed or cancelled.')

        # Update the warranty claim
        self.warranty_claim_id.write({
            'state': 'cancelled',
            'cancel_reason': self.cancel_reason,
            'cancel_notes': self.cancel_notes,
            'cancelled_by': self.env.user.id,
            'cancelled_date': fields.Datetime.now(),
        })

        # Add message to chatter
        reason_label = dict(self._fields['cancel_reason'].selection)[self.cancel_reason]
        message = f"Warranty claim cancelled. </b>Reason: {reason_label}"
        if self.cancel_notes:
            message += f"\n</b>Notes: {self.cancel_notes}"

        self.warranty_claim_id.message_post(
            body=message,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )

        # Send email notification if requested
        if self.notify_customer:
            template = self.env.ref('after_sales_service.email_template_claim_cancel', raise_if_not_found=False)
            if template and self.warranty_claim_id.partner_id.email:
                # Pass cancel reason and notes to email template context
                template.with_context({
                    'cancel_reason': reason_label,
                    'cancel_notes': self.cancel_notes,
                }).send_mail(self.warranty_claim_id.id, force_send=True)


        return {'type': 'ir.actions.act_window_close'}