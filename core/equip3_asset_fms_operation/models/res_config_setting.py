from odoo import fields, models, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_asset_stock_barcode_mobile_type = fields.Selection(
        related='company_id.sh_asset_stock_barcode_mobile_type', string='Product Scan Options In Mobile (Asset Stock)', translate=True, readonly=False)

    sh_asset_stock_bm_is_cont_scan = fields.Boolean(
        related='company_id.sh_asset_stock_bm_is_cont_scan', string='Continuously Scan? (Asset Stock)', readonly=False)

    sh_asset_stock_bm_is_notify_on_success = fields.Boolean(
        related='company_id.sh_asset_stock_bm_is_notify_on_success', string='Notification On Product Succeed? (Asset Stock)', readonly=False)

    sh_asset_stock_bm_is_notify_on_fail = fields.Boolean(
        related='company_id.sh_asset_stock_bm_is_notify_on_fail', string='Notification On Product Failed? (Asset Stock)', readonly=False)

    sh_asset_stock_bm_is_sound_on_success = fields.Boolean(
        related='company_id.sh_asset_stock_bm_is_sound_on_success', string='Play Sound On Product Succeed? (Asset Stock)', readonly=False)

    sh_asset_stock_bm_is_sound_on_fail = fields.Boolean(
        related='company_id.sh_asset_stock_bm_is_sound_on_fail', string='Play Sound On Product Failed? (Asset Stock)', readonly=False)
    
    asset_control = fields.Boolean(related='company_id.asset_control', string='Asset Control', readonly=False)
    
    is_approval_matix_mwo = fields.Boolean(string='Maintenance Work Order Approval Matrix')
    is_approval_matix_mro = fields.Boolean(string='Maintenance Repair Order Approval Matrix')
    is_approval_matix_mp = fields.Boolean(string='Maintenance Plan Approval Matrix')
    is_approval_matix_asset_transfer = fields.Boolean(string='Asset Transfer Approval Matrix')
    is_approval_matix_asset_employee_request = fields.Boolean(string='Asset Employee Request Approval Matrix')
    is_disposable_asset = fields.Boolean(string="Sale and Dispose Assets", default=False)
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'is_approval_matix_mwo': IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_mwo', False),
            'is_approval_matix_mro': IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_mro', False),
            'is_approval_matix_mp': IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_mp', False),
            'is_approval_matix_asset_transfer': IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_asset_transfer', False),
            'is_approval_matix_asset_employee_request': IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_asset_employee_request', False),
            'is_disposable_asset': IrConfigParam.get_param('equip3_asset_fms_operation.is_disposable_asset', False),
        })
        return res
    
    def set_values(self):
        if self.asset_control == False:
            self.update({
                'is_approval_matix_mwo': False,
                'is_approval_matix_mro': False,
                'is_approval_matix_mp': False,
                'is_approval_matix_asset_transfer': False,
                'is_approval_matix_asset_employee_request': False,
                'is_disposable_asset': False
            })

        # HIDE MENU BASED ON CONFIG
        fms_accessright_installed = self.env['ir.module.module'].search([('name', '=', 'equip3_asset_fms_accessright_setting'), ('state', '=', 'installed')])
        if fms_accessright_installed:
            if not self.is_approval_matix_asset_employee_request:
                self.env.ref('equip3_asset_fms_accessright_setting.employee_approval_request_menu_act').active = False
            else:
                self.env.ref('equip3_asset_fms_accessright_setting.employee_approval_request_menu_act').active = True
        if self.is_approval_matix_asset_transfer:
            self.env.ref('equip3_asset_fms_masterdata.menu_approval_matrix_asset_transfer').active = True
        else:
            self.env.ref('equip3_asset_fms_masterdata.menu_approval_matrix_asset_transfer').active = False
            
        
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_asset_fms_operation.is_approval_matix_mwo', self.is_approval_matix_mwo)
        self.env['ir.config_parameter'].sudo().set_param('equip3_asset_fms_operation.is_approval_matix_mro', self.is_approval_matix_mro)
        self.env['ir.config_parameter'].sudo().set_param('equip3_asset_fms_operation.is_approval_matix_mp', self.is_approval_matix_mp)
        self.env['ir.config_parameter'].sudo().set_param('equip3_asset_fms_operation.is_approval_matix_asset_transfer', self.is_approval_matix_asset_transfer)
        self.env['ir.config_parameter'].sudo().set_param('equip3_asset_fms_operation.is_approval_matix_asset_employee_request', self.is_approval_matix_asset_employee_request)
        self.env['ir.config_parameter'].sudo().set_param('equip3_asset_fms_operation.is_disposable_asset', self.is_disposable_asset)
