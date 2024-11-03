
from odoo import api , fields , models
from odoo.exceptions import UserError, ValidationError, Warning


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_matrix_config_const = fields.Selection([
                    ('contract_amt', 'Contract Amount'),
                    ('adjustment_amt', 'Adjustment Amount'),
                    ('discount_amt', 'Discount Amount'),
                ], string='SO Default Configuration' )

    is_contract_amount = fields.Boolean(string="Contract Amount")
    contract_sequence = fields.Integer(string="Approval Sequence", help="Define the sequence number in sale order approval matrix process for each configuration")
    contract_sequence_select = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in sale order approval matrix process for each configuration")
    is_adjustment_amount = fields.Boolean(string="Adjustment Amount")
    adjustment_sequence = fields.Integer(string="Approval Sequence", help="Define the sequence number in sale order approval matrix process for each configuration")
    adjustment_sequence_select = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in sale order approval matrix process for each configuration")
    is_discount_amount_const = fields.Boolean(string="Discount Amount")
    discount_sequence_const = fields.Integer(string="Approval Sequence", help="Define the sequence number in sale order approval matrix process for each configuration")
    discount_sequence_select_const = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in sale order approval matrix process for each configuration")
    con_expired_date = fields.Integer(string="Sale Order Expire Date")
    je_expiry_date = fields.Integer(string="BOQ Expiry Date")
    
    @api.onchange('is_customer_approval_matrix_const')
    def _onchange_const_sales(self):
        for config in self:
            if config.is_customer_approval_matrix_const == False:
                config.is_contract_amount = False
                config.is_adjustment_amount = False
                config.is_discount_amount_const = False

    @api.onchange('contract_sequence_select', 'adjustment_sequence_select', 'discount_sequence_select_const')
    def _onchange_sequence_select_const(self):
        if self.contract_sequence_select:
            self.contract_sequence = int(self.contract_sequence_select)
        if self.adjustment_sequence_select:
            self.adjustment_sequence = int(self.adjustment_sequence_select)
        if self.discount_sequence_select_const:
            self.discount_sequence_const = int(self.discount_sequence_select_const)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'sale_matrix_config_const': IrConfigParam.get_param('sale_matrix_config_const', 'contract_amt'),
            'keep_name_so' : IrConfigParam.get_param('keep_name_so', False),
            'is_contract_amount': IrConfigParam.get_param('is_contract_amount', False),
            'is_adjustment_amount': IrConfigParam.get_param('is_adjustment_amount', False),
            'is_discount_amount_const': IrConfigParam.get_param('is_discount_amount_const', False),
            'contract_sequence': IrConfigParam.get_param('contract_sequence', 0),
            'adjustment_sequence': IrConfigParam.get_param('adjustment_sequence', 0),
            'discount_sequence_const': IrConfigParam.get_param('discount_sequence_const', 0),
            'contract_sequence_select': IrConfigParam.get_param('contract_sequence_select', '1'),
            'adjustment_sequence_select': IrConfigParam.get_param('adjustment_sequence_select', '1'),
            'discount_sequence_select_const': IrConfigParam.get_param('discount_sequence_select_const', '1'),
            'use_sale_order_note': False,
            'con_expired_date': IrConfigParam.get_param('con_expired_date', '1'),
            'je_expiry_date': IrConfigParam.get_param('je_expiry_date', '1'),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        seq_list = [1, 2, 3]
        sequence = []
        if self.is_contract_amount and self.contract_sequence not in seq_list:
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")
        if self.is_adjustment_amount and self.adjustment_sequence not in seq_list:
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")
        if self.is_discount_amount_const and self.discount_sequence_const not in seq_list:
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")
        if (self.contract_sequence == self.adjustment_sequence and self.is_contract_amount and self.is_adjustment_amount) or \
           (self.adjustment_sequence == self.discount_sequence_const and self.is_adjustment_amount and self.is_discount_amount_const) or \
           (self.discount_sequence_const == self.contract_sequence and self.is_discount_amount_const and self.is_contract_amount) or \
           (self.contract_sequence == self.adjustment_sequence == self.discount_sequence_const and self.is_discount_amount_const and self.is_contract_amount and self.is_adjustment_amount):
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")
        if self.is_contract_amount:
            sequence.append(self.contract_sequence)
        if self.is_adjustment_amount:
            sequence.append(self.adjustment_sequence)
        if self.is_discount_amount_const:
            sequence.append(self.discount_sequence_const)

        if sequence and 1 not in sequence:
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")

        if sequence and not sorted(sequence) == list(range(min(sequence), max(sequence)+1)):
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")

        self.env['ir.config_parameter'].sudo().set_param('sale_matrix_config_const', self.sale_matrix_config_const)
        self.env['ir.config_parameter'].sudo().set_param('is_contract_amount', self.is_contract_amount)
        self.env['ir.config_parameter'].sudo().set_param('is_adjustment_amount', self.is_adjustment_amount)
        self.env['ir.config_parameter'].sudo().set_param('is_discount_amount_const', self.is_discount_amount_const)
        self.env['ir.config_parameter'].sudo().set_param('contract_sequence', self.contract_sequence)
        self.env['ir.config_parameter'].sudo().set_param('adjustment_sequence', self.adjustment_sequence)
        self.env['ir.config_parameter'].sudo().set_param('discount_sequence_const', self.discount_sequence_const)
        self.env['ir.config_parameter'].sudo().set_param('keep_name_so', self.keep_name_so)
        self.env['ir.config_parameter'].sudo().set_param('contract_sequence_select', self.contract_sequence_select)
        self.env['ir.config_parameter'].sudo().set_param('adjustment_sequence_select', self.adjustment_sequence_select)
        self.env['ir.config_parameter'].sudo().set_param('discount_sequence_select_const', self.discount_sequence_select_const)
        self.env['ir.config_parameter'].sudo().set_param('con_expired_date', self.con_expired_date)
        self.env['ir.config_parameter'].sudo().set_param('je_expiry_date', self.je_expiry_date) 
        if self.is_customer_approval_matrix_const:
            self.env.ref('equip3_construction_sales_operation.approving_matrix_sale_order_const').active = True
        else:
            self.env.ref('equip3_construction_sales_operation.approving_matrix_sale_order_const').active = False

        if self.is_job_estimate_approval_matrix:
            self.env.ref('equip3_construction_sales_operation.approving_matrix_job_estimate').active = True
            self.env.ref('equip3_construction_sales_operation.menu_internal_approving_matrix_job_estimate').active = True
        else:
            self.env.ref('equip3_construction_sales_operation.approving_matrix_job_estimate').active = False
            self.env.ref('equip3_construction_sales_operation.menu_internal_approving_matrix_job_estimate').active = False