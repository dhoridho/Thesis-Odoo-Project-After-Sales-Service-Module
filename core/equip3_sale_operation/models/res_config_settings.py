
from odoo import api , fields , models
from odoo.exceptions import UserError, ValidationError, Warning


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_matrix_config = fields.Selection([
                    ('total_amt', 'Total Amount'),
                    ('margin_amt', 'Margin Amount'),
                    ('pargin_per', 'Margin Percentage'),
                    ('discount_amt', 'Discount Amount'),
                    #('discount_Pet', 'Discount Percentage')
                ], string='SO Default Configuration' )

    is_total_amount = fields.Boolean(string="Total Amount")
    total_sequence = fields.Integer(string="Approval Sequence", help="Define the sequence number in sale order approval matrix process for each configuration")
    total_sequence_select = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in sale order approval matrix process for each configuration")
    is_margin_amount = fields.Boolean(string="Margin Percentage")
    margin_sequence = fields.Integer(string="Approval Sequence", help="Define the sequence number in sale order approval matrix process for each configuration")
    margin_sequence_select = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in sale order approval matrix process for each configuration")
    is_discount_amount = fields.Boolean(string="Discount Amount")
    discount_sequence = fields.Integer(string="Approval Sequence", help="Define the sequence number in sale order approval matrix process for each configuration")
    discount_sequence_select = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Last')], help="Define the sequence number in sale order approval matrix process for each configuration")
    expired_date = fields.Integer(string="Expiry Of Document URL")
    multilevel_disc_sale = fields.Boolean(string="Multi Level Discount")
    is_wa_so_approval = fields.Boolean(string="Whatsapp Notification for SO Approval")
    is_email_so_approval = fields.Boolean(string='Email Notification for SO Approval')
    show_select_product_button = fields.Boolean(string='Select Product for Order')
    lock_sale_order = fields.Boolean(string='Lock Sale Order in Quotation')
    product_pricelist_default = fields.Many2one('product.pricelist', 'Default Pricelist', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    is_customer_partner_approval_matrix = fields.Boolean(string="Customer Approval Matrix", default=False)

    @api.onchange('total_sequence_select', 'margin_sequence_select', 'discount_sequence_select')
    def _onchange_sequence_select(self):
        if self.total_sequence_select:
            self.total_sequence = int(self.total_sequence_select)
        if self.margin_sequence_select:
            self.margin_sequence = int(self.margin_sequence_select)
        if self.discount_sequence_select:
            self.discount_sequence = int(self.discount_sequence_select)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()

        # product_pricelist_id = int(IrConfigParam.get_param('equip3_sale_operation.product_pricelist_default'))

        res.update({
            'sale_matrix_config': IrConfigParam.get_param('sale_matrix_config', 'total_amt'),
            'keep_name_so': IrConfigParam.get_param('keep_name_so', False),
            'is_total_amount': IrConfigParam.get_param('is_total_amount', False),
            'is_margin_amount': IrConfigParam.get_param('is_margin_amount', False),
            'is_discount_amount': IrConfigParam.get_param('is_discount_amount', False),
            'total_sequence': IrConfigParam.get_param('total_sequence', 0),
            'margin_sequence': IrConfigParam.get_param('margin_sequence', 0),
            'discount_sequence': IrConfigParam.get_param('discount_sequence', 0),
            'total_sequence_select': IrConfigParam.get_param('total_sequence_select', '1'),
            'margin_sequence_select': IrConfigParam.get_param('margin_sequence_select', '1'),
            'discount_sequence_select': IrConfigParam.get_param('discount_sequence_select', '1'),
            'use_sale_order_note': False,
            'expired_date': IrConfigParam.get_param('expired_date', '1'),
            'multilevel_disc_sale': IrConfigParam.get_param('multilevel_disc_sale'),
            'is_wa_so_approval': IrConfigParam.get_param('is_wa_so_approval', False),
            'is_email_so_approval': IrConfigParam.get_param('is_email_so_approval', False),
            'show_select_product_button': IrConfigParam.get_param('show_select_product_button'),
            'lock_sale_order': IrConfigParam.get_param('lock_sale_order'),
            'product_pricelist_default': self.env.company.product_pricelist_default.id,
            'is_customer_partner_approval_matrix': IrConfigParam.get_param('is_customer_partner_approval_matrix'),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        seq_list = [1, 2, 3]
        sequence = []
        if self.is_total_amount and self.total_sequence not in seq_list:
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")
        if self.is_margin_amount and self.margin_sequence not in seq_list:
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")
        if self.is_discount_amount and self.discount_sequence not in seq_list:
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")
        if (self.total_sequence == self.margin_sequence and self.is_total_amount and self.is_margin_amount) or \
           (self.margin_sequence == self.discount_sequence and self.is_margin_amount and self.is_discount_amount) or \
           (self.discount_sequence == self.total_sequence and self.is_discount_amount and self.is_total_amount) or \
           (self.total_sequence == self.margin_sequence == self.discount_sequence and self.is_discount_amount and self.is_total_amount and self.is_margin_amount):
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")
        if self.is_total_amount:
            sequence.append(self.total_sequence)
        if self.is_margin_amount:
            sequence.append(self.margin_sequence)
        if self.is_discount_amount:
            sequence.append(self.discount_sequence)

        if sequence and 1 not in sequence:
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")

        if sequence and not sorted(sequence) == list(range(min(sequence), max(sequence)+1)):
            raise ValidationError("The sequence number for Sale Order approval matrix is not sequential. Please rearrange the sequence number")

        self.env['ir.config_parameter'].sudo().set_param('sale_matrix_config', self.sale_matrix_config)
        self.env['ir.config_parameter'].sudo().set_param('is_total_amount', self.is_total_amount)
        self.env['ir.config_parameter'].sudo().set_param('is_margin_amount', self.is_margin_amount)
        self.env['ir.config_parameter'].sudo().set_param('is_discount_amount', self.is_discount_amount)
        self.env['ir.config_parameter'].sudo().set_param('total_sequence', self.total_sequence)
        self.env['ir.config_parameter'].sudo().set_param('margin_sequence', self.margin_sequence)
        self.env['ir.config_parameter'].sudo().set_param('discount_sequence', self.discount_sequence)
        self.env['ir.config_parameter'].sudo().set_param('keep_name_so', self.keep_name_so)
        self.env['ir.config_parameter'].sudo().set_param('total_sequence_select', self.total_sequence_select)
        self.env['ir.config_parameter'].sudo().set_param('margin_sequence_select', self.margin_sequence_select)
        self.env['ir.config_parameter'].sudo().set_param('discount_sequence_select', self.discount_sequence_select)
        self.env['ir.config_parameter'].sudo().set_param('expired_date', self.expired_date)
        self.env['ir.config_parameter'].sudo().set_param('multilevel_disc_sale', self.multilevel_disc_sale)
        self.env['ir.config_parameter'].sudo().set_param('is_wa_so_approval', self.is_wa_so_approval)
        self.env['ir.config_parameter'].sudo().set_param('is_email_so_approval', self.is_email_so_approval)
        self.env['ir.config_parameter'].sudo().set_param('show_select_product_button', self.show_select_product_button)
        self.env['ir.config_parameter'].sudo().set_param('lock_sale_order', self.lock_sale_order)
        self.env['ir.config_parameter'].sudo().set_param('is_customer_partner_approval_matrix', self.is_customer_partner_approval_matrix)
        
        if self.is_customer_partner_approval_matrix:
            self.env.ref('equip3_sale_operation.approval_matrix_customer_configuration_menu').active = True
            self.env.ref('equip3_sale_operation.menu_customer_to_approve').active = True
            self.env.ref('equip3_sale_operation.menu_customer_rejected').active = True
        else:
            self.env.ref('equip3_sale_operation.approval_matrix_customer_configuration_menu').active = False
            self.env.ref('equip3_sale_operation.menu_customer_to_approve').active = False
            self.env.ref('equip3_sale_operation.menu_customer_rejected').active = False

        if self.is_customer_approval_matrix:
            self.env.ref('equip3_sale_operation.approving_matrix_sale_order').active = True
        else:
            self.env.ref('equip3_sale_operation.approving_matrix_sale_order').active = False
        if self.is_customer_approval_matrix:
            self.env.ref('sale.model_sale_order_action_quotation_sent').unlink_action()

        self.env['ir.config_parameter'].sudo().set_param('equip3_sale_operation.product_pricelist_default', self.product_pricelist_default.id)
        self.env.company.product_pricelist_default = self.product_pricelist_default.id

class ResCompany(models.Model):
    _inherit = "res.company"

    sh_sale_pro_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        relation="sh_sale_pro_field_ids_rel_comp_table",
        string="Sale Product Fields",
    )
    sh_sale_pro_attr_ids = fields.Many2many(
        comodel_name="product.attribute",
        relation="sh_sale_pro_attr_ids_rel_comp_table",
        string="Sale Product Attributes",
    )
    product_pricelist_default = fields.Many2one('product.pricelist', 'Default Pricelist')

class SaleAdvSettings(models.TransientModel):
    _name = "sale.adv.settings"
    _description = "Sales Multi Product Selection Advanced Wizard Settings"

    @api.model
    def sh_get_user_company(self):
        if self.env.user.company_id:
            return self.env.user.company_id.id
        return False

    @api.model
    def get_sh_sale_pro_field_ids(self):
        if(
                self.env.user.company_id and
                self.env.user.company_id.sh_sale_pro_field_ids
        ):
            return self.env.user.company_id.sh_sale_pro_field_ids.ids
        return False

    @api.model
    def get_sh_sale_pro_attr_ids(self):
        if(
                self.env.user.company_id and
                self.env.user.company_id.sh_sale_pro_attr_ids
        ):
            return self.env.user.company_id.sh_sale_pro_attr_ids.ids
        return False

    company_id = fields.Many2one(
        "res.company",
        default=sh_get_user_company
    )
    name = fields.Char(
        string="Name",
        default="Search Products Settings"
    )

    sh_sale_pro_field_ids = fields.Many2many(
        "ir.model.fields",
        string="Product Fields",
        related="company_id.sh_sale_pro_field_ids",
        domain=[('model_id.model', 'in', ['product.product','product.template']),
                ('ttype', 'in', ['integer', 'char', 'float', 'boolean', 'many2one', 'selection']),
                ('store', '=', True)
                ],
        default=get_sh_sale_pro_field_ids,
        readonly=False
    )

    sh_sale_pro_attr_ids = fields.Many2many(
        "product.attribute",
        string="Product Attributes",
        related="company_id.sh_sale_pro_attr_ids",
        default=get_sh_sale_pro_attr_ids,
        readonly=False
    )
