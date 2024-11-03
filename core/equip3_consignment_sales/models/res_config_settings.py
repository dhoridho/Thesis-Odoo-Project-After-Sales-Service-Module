from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_consignment_sales = fields.Boolean(string='Consignment Sales', related='company_id.is_consignment_sales',
                                          config_parameter='is_consignment_sales', readonly=False, help="Enable Consignment Sales")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        company_id = self.env.company.id
        config_key = f'is_consignment_sales_{company_id}'
        res.update({
            'is_consignment_sales': IrConfigParam.get_param(config_key, default=False),
        })
        return res

    def set_values(self):
        company = self.env.company
        company.write({'is_consignment_sales': self.is_consignment_sales})

        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        company_id = self.env.company.id
        config_key = f'is_consignment_sales_{company_id}'
        param.set_param(config_key, self.is_consignment_sales)

        if company.is_consignment_sales:
            self.create_warehouse_consignment()
            self.env.ref(
                'equip3_consignment_sales.sale_consign_menu').active = True
            self.env.ref(
                'equip3_consignment_sales.consignment_report_header').active = True
        else:
            self.env.ref(
                'equip3_consignment_sales.sale_consign_menu').active = False
            self.env.ref(
                'equip3_consignment_sales.consignment_report_header').active = False

    def create_warehouse_consignment(self):
        param = self.env['ir.config_parameter'].sudo()
        company_id = self.env.company.id
        config_key = f'is_consignment_sales_{company_id}'
        is_consignment_sales = param.get_param(config_key)

        if is_consignment_sales:
            company = self.env.company
            existing_wh = self.env['stock.warehouse'].sudo().search([
                ('is_consignment_warehouse', '=', True),
                ('company_id', '=', company.id)
            ], limit=1)

            if not existing_wh:
                warehouse_vals = {
                    'name': "Warehouse Consignment",
                    'code': "WCT",
                    'company_id': company.id,
                    'partner_id': company.partner_id.id,
                    'branch_id': company.partner_id.branch_id.id,
                    'is_consignment_warehouse': True
                }
                warehouse_id = self.env['stock.warehouse'].sudo().create(
                    warehouse_vals)
        return True
