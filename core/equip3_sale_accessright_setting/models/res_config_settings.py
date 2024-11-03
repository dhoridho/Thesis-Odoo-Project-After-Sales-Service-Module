
from odoo import api , fields , models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_customer_approval_matrix = fields.Boolean(string="Sale Order Approval Matrix")
    is_customer_limit_matrix = fields.Boolean(string="Customer Limit Approval Matrix")
    is_over_limit_validation = fields.Boolean(string="Over Limit Validation")
    is_bo_approval_matrix = fields.Boolean(string="Blanket Order Approval Matrix")
    show_sale_barcode_mobile_type = fields.Boolean("Sale Mobile Barcode Scanner")
    sh_sale_barcode_mobile_type_new = fields.Selection([
        ('int_ref', 'Internal Reference'),
        ('barcode', 'Barcode'),
        ('sh_qr_code', 'QR code'),
        ('all', 'All')
    ], default='all', string='Product Scan Options In Mobile (Sale)', translate=True)
    group_sale_pricelist_approval = fields.Boolean(string='Pricelist Approval Matrix', implied_group='equip3_sale_accessright_setting.group_sale_pricelist_approval')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_customer_approval_matrix = IrConfigParam.get_param('is_customer_approval_matrix')
        if is_customer_approval_matrix is None:
            is_customer_approval_matrix = True
        is_customer_limit_matrix = IrConfigParam.get_param('is_customer_limit_matrix')
        if is_customer_limit_matrix is None:
            is_customer_limit_matrix = True
        is_bo_approval_matrix = IrConfigParam.get_param('is_bo_approval_matrix')
        if is_bo_approval_matrix is None:
            is_bo_approval_matrix = True
        is_over_limit_validation = IrConfigParam.get_param('is_over_limit_validation', False)
        show_sale_barcode_mobile_type = IrConfigParam.get_param('show_sale_barcode_mobile_type', False)
        sh_sale_barcode_mobile_type_new = self.env['ir.config_parameter'].sudo().get_param('sh_sale_barcode_mobile_type_new')
        sales = IrConfigParam.get_param('sales', False)
        res.update({
            'is_customer_approval_matrix': is_customer_approval_matrix,
            'is_customer_limit_matrix': is_customer_limit_matrix,
            'is_bo_approval_matrix': is_bo_approval_matrix,
            'sales': sales,
            'is_over_limit_validation': is_over_limit_validation,
            'show_sale_barcode_mobile_type': show_sale_barcode_mobile_type,
            'sh_sale_barcode_mobile_type_new': sh_sale_barcode_mobile_type_new or self.env.company.sh_sale_barcode_mobile_type
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        self.env['ir.config_parameter'].sudo().set_param('is_customer_approval_matrix', self.is_customer_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_customer_limit_matrix', self.is_customer_limit_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_over_limit_validation', self.is_over_limit_validation)
        self.env['ir.config_parameter'].sudo().set_param('sales', self.sales)
        if not self.sales:
            self.is_bo_approval_matrix = False
        self.env['ir.config_parameter'].sudo().set_param('is_bo_approval_matrix', self.is_bo_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('show_sale_barcode_mobile_type', self.show_sale_barcode_mobile_type)
        if not self.show_sale_barcode_mobile_type:
            self.env['ir.config_parameter'].sudo().set_param('sh_sale_barcode_mobile_type_new', 'all')
            self.env.company.sh_sale_barcode_mobile_type = 'all'
        else:
            self.env['ir.config_parameter'].sudo().set_param('sh_sale_barcode_mobile_type_new', self.sh_sale_barcode_mobile_type_new or self.env.company.sh_sale_barcode_mobile_type)
            self.env.company.sh_sale_barcode_mobile_type = self.sh_sale_barcode_mobile_type_new or self.env.company.sh_sale_barcode_mobile_type
