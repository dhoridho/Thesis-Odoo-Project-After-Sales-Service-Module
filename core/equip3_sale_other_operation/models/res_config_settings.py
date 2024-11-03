
from odoo import api , fields , models
from odoo.exceptions import UserError, ValidationError, Warning


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    customer_credit_limit = fields.Float(string="Default Customer Credit limit", default=1000000)
    customer_max_invoice_overdue_days = fields.Float(string="Default Customer Max Invoice Overdue Days", default=30)
    customer_open_invoice_limit = fields.Float(string="Default Customer Open Invoice Limit", default=5)
    is_over_credit_limit = fields.Boolean(string="Over Credit Limit")
    over_credit_limit_sequence = fields.Integer(string="Approval Sequence", help="Define the sequence number in over limit approval matrix process for each configuration")
    over_credit_limit_sequence_select = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in over limit approval matrix process for each configuration")
    is_invoice_overdue = fields.Boolean(string="Invoice Overdue")
    invoice_overdue_sequence = fields.Integer(string="Approval Sequence", help="Define the sequence number in over limit approval matrix process for each configuration")
    invoice_overdue_sequence_select = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in over limit approval matrix process for each configuration")
    open_invoice_limit = fields.Boolean(string="Open Invoice Limit")
    open_invoice_limit_sequence = fields.Integer(string="Approval Sequence", help="Define the sequence number in Open limit approval matrix process for each configuration")
    open_invoice_limit_sequence_select = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in Open limit approval matrix process for each configuration", string="Approval Sequence")
    is_wa_overlimit_approval = fields.Boolean(string="Whatsapp Notification for Over Limit Approval")
    is_email_overlimit_approval = fields.Boolean(string='Email Notification for Over Limit Approval')
    is_email_notification_customer_credit = fields.Boolean(string="Email Notification for Customer Credit")
    is_whatsapp_notification_customer_credit = fields.Boolean(string="Whatsapp Notification for Customer Credit")
    show_customer_product_label = fields.Boolean(string='Customer Product Label')

    @api.onchange('over_credit_limit_sequence_select', 'invoice_overdue_sequence_select', 'open_invoice_limit_sequence_select')
    def _onchange_credit_limit_sequence_select(self):
        if self.over_credit_limit_sequence_select:
            self.over_credit_limit_sequence = int(self.over_credit_limit_sequence_select)
        if self.invoice_overdue_sequence_select:
            self.invoice_overdue_sequence = int(self.invoice_overdue_sequence_select)
        if self.open_invoice_limit_sequence_select:
            self.open_invoice_limit_sequence = int(self.open_invoice_limit_sequence_select)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'customer_credit_limit': IrConfigParam.get_param('customer_credit_limit', 1000000),
            'customer_max_invoice_overdue_days': IrConfigParam.get_param('customer_max_invoice_overdue_days', 30),
            'customer_open_invoice_limit': IrConfigParam.get_param('customer_open_invoice_limit', 5),
            'is_over_credit_limit': IrConfigParam.get_param('is_over_credit_limit', False),
            'over_credit_limit_sequence': IrConfigParam.get_param('over_credit_limit_sequence', 0),
            'is_invoice_overdue': IrConfigParam.get_param('is_invoice_overdue', False),
            'invoice_overdue_sequence': IrConfigParam.get_param('invoice_overdue_sequence', 0),
            'over_credit_limit_sequence_select': IrConfigParam.get_param('over_credit_limit_sequence_select', '1'),
            'invoice_overdue_sequence_select': IrConfigParam.get_param('invoice_overdue_sequence_select', '1'),
            'open_invoice_limit': IrConfigParam.get_param('open_invoice_limit', False),
            'open_invoice_limit_sequence' : IrConfigParam.get_param('open_invoice_limit_sequence', 0),
            'open_invoice_limit_sequence_select' : IrConfigParam.get_param('open_invoice_limit_sequence_select', '3'),
            'is_wa_overlimit_approval': IrConfigParam.get_param('is_wa_overlimit_approval', False),
            'is_email_overlimit_approval': IrConfigParam.get_param('is_email_overlimit_approval', False),
            'is_email_notification_customer_credit': IrConfigParam.get_param('equip3_sale_other_operation.is_email_notification_customer_credit'),
            'is_whatsapp_notification_customer_credit': IrConfigParam.get_param('equip3_sale_other_operation.is_whatsapp_notification_customer_credit'),
            'show_customer_product_label': IrConfigParam.get_param('show_customer_product_label'),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        seq_list = [1, 2, 3]
        sequence = []
        if self.is_over_limit_validation:
            if self.is_over_credit_limit and self.over_credit_limit_sequence not in seq_list:
                raise ValidationError("The sequence number for Credit Limit approval matrix is not sequential. Please rearrange the sequence number")
            if self.is_invoice_overdue and self.invoice_overdue_sequence not in seq_list:
                raise ValidationError("The sequence number for Invoice Overdue approval matrix is not sequential. Please rearrange the sequence number")
            if self.open_invoice_limit and self.open_invoice_limit_sequence not in seq_list:
                raise ValidationError("The sequence number for Open Invoice Limit approval matrix is not sequential. Please rearrange the sequence number")
            if (self.over_credit_limit_sequence == self.invoice_overdue_sequence and self.is_over_credit_limit and self.is_invoice_overdue) or \
               (self.invoice_overdue_sequence == self.open_invoice_limit_sequence and self.is_invoice_overdue and self.open_invoice_limit) or \
               (self.open_invoice_limit_sequence == self.over_credit_limit_sequence and self.open_invoice_limit and self.is_over_credit_limit) or \
               (self.over_credit_limit_sequence == self.invoice_overdue_sequence == self.open_invoice_limit_sequence and self.open_invoice_limit and self.is_invoice_overdue and self.is_over_credit_limit):
                raise ValidationError("The sequence number for Limits approval matrix is not sequential. Please rearrange the sequence number")
            if self.is_over_credit_limit:
                sequence.append(self.over_credit_limit_sequence)
            if self.is_invoice_overdue:
                sequence.append(self.invoice_overdue_sequence)
            if self.open_invoice_limit:
                sequence.append(self.open_invoice_limit_sequence)

            if sequence and 1 not in sequence:
                raise ValidationError("The sequence number for Limits approval matrix is not sequential. Please rearrange the sequence number")

            if sequence and not sorted(sequence) == list(range(min(sequence), max(sequence)+1)):
                raise ValidationError("The sequence number for Limits approval matrix is not sequential. Please rearrange the sequence number")
        
        if self.sales and self.is_over_limit_validation:
            partner_ids = self.env['res.partner'].search([])
            if not self.is_over_credit_limit:
                for partner_id in partner_ids:
                    partner_id.write({'set_customer_onhold': self.is_over_credit_limit})
            if not self.is_invoice_overdue:
                for partner_id in partner_ids:
                    partner_id.write({'is_set_customer_on_hold': self.is_invoice_overdue})
            if not self.open_invoice_limit:
                for partner_id in partner_ids:
                    partner_id.write({'customer_on_hold_open_invoice': self.open_invoice_limit})

        self.env['ir.config_parameter'].sudo().set_param('customer_credit_limit', self.customer_credit_limit),
        self.env['ir.config_parameter'].sudo().set_param('customer_max_invoice_overdue_days', self.customer_max_invoice_overdue_days)
        self.env['ir.config_parameter'].sudo().set_param('customer_open_invoice_limit', self.customer_open_invoice_limit)
        self.env['ir.config_parameter'].sudo().set_param('is_over_credit_limit', self.is_over_credit_limit)
        self.env['ir.config_parameter'].sudo().set_param('is_invoice_overdue', self.is_invoice_overdue)
        self.env['ir.config_parameter'].sudo().set_param('over_credit_limit_sequence', self.over_credit_limit_sequence)
        self.env['ir.config_parameter'].sudo().set_param('invoice_overdue_sequence', self.invoice_overdue_sequence)
        self.env['ir.config_parameter'].sudo().set_param('over_credit_limit_sequence_select', self.over_credit_limit_sequence_select)
        self.env['ir.config_parameter'].sudo().set_param('invoice_overdue_sequence_select', self.invoice_overdue_sequence_select)
        self.env['ir.config_parameter'].sudo().set_param('open_invoice_limit', self.open_invoice_limit)
        self.env['ir.config_parameter'].sudo().set_param('open_invoice_limit_sequence', self.open_invoice_limit_sequence)
        self.env['ir.config_parameter'].sudo().set_param('open_invoice_limit_sequence_select', self.open_invoice_limit_sequence_select)
        self.env['ir.config_parameter'].sudo().set_param('is_wa_overlimit_approval', self.is_wa_overlimit_approval)
        self.env['ir.config_parameter'].sudo().set_param('is_email_overlimit_approval', self.is_email_overlimit_approval)
        self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation.is_email_notification_customer_credit', self.is_email_notification_customer_credit)
        self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation.is_whatsapp_notification_customer_credit', self.is_whatsapp_notification_customer_credit)
        self.env['ir.config_parameter'].sudo().set_param('show_customer_product_label', self.show_customer_product_label)
        
        if self.show_customer_product_label:
            self.env.ref('equip3_sale_other_operation.menu_customer_product_template').active = True
        else:
            self.env.ref('equip3_sale_other_operation.menu_customer_product_template').active = False