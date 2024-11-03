from odoo import fields,models,api

class RecruitmentDashboard(models.Model):
    _inherit = 'ks_dashboard_ninja.board'

    ks_dashboard_icon_class = fields.Char(string="Equip Icon Class")

    @api.model
    def create(self, vals):
        record = super(RecruitmentDashboard, self).create(vals)
        if 'ks_dashboard_top_menu_id' in vals and 'ks_dashboard_menu_name' in vals:
            if record.ks_dashboard_menu_id:
                record.ks_dashboard_menu_id.write({
                        'equip_icon_class': vals.get('ks_dashboard_icon_class',''),
                    })
        return record

    def write(self, vals):
        record = super(RecruitmentDashboard, self).write(vals)
        for rec in self:
            if 'ks_dashboard_icon_class' in vals:
                rec.ks_dashboard_menu_id.sudo().equip_icon_class = vals['ks_dashboard_icon_class']
        return record
