from odoo import models,fields,api

class AccountingDashboard(models.Model):
    _inherit = 'ks_dashboard_ninja.board'

    ks_dashboard_icon_budget = fields.Char(string="Equip Icon Budget")

    @api.model
    def set_dashboard_icon(self):
            menu_id = self.env['ir.ui.menu'].search([
                ('name', 'ilike', 'accounting dashboard'),
                ('parent_id', '=', self.env.ref('account.menu_finance').id)
            ])
            if menu_id:
                menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-accounting-account-dashboard'})

    @api.model
    def create(self, vals):
        record = super(AccountingDashboard, self).create(vals)
        if 'ks_dashboard_top_menu_id' in vals and 'ks_dashboard_menu_name' in vals:
            if record.ks_dashboard_menu_id:
                record.ks_dashboard_menu_id.write({
                        'equip_icon_class': vals.get('ks_dashboard_icon_budget',''),
                    })
        return record

    def write(self, vals):
        record = super(AccountingDashboard, self).write(vals)
        for rec in self:
            if 'ks_dashboard_icon_budget' in vals:
                rec.ks_dashboard_menu_id.sudo().equip_icon_class = vals['ks_dashboard_icon_budget']
        return record
