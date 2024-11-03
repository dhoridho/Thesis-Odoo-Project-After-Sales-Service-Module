from odoo import models, fields, api, tools
import time
from odoo.exceptions import ValidationError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    deviation = fields.Float(compute="_compute_deviation", string="Deviation", store=True)
    bom_forecast_cost = fields.Float(related='bom_id.forecast_cost', store=True)

    @api.depends('duration_expected', 'duration')
    def _compute_deviation(self):
        for record in self:
            record.deviation = record.duration_expected - record.duration

    @api.depends('location_dest_id')
    def _compute_warehouse_id(self):
        for record in self:
            record.warehouse_id = False
            warehouse_id = record.location_dest_id.get_warehouse()
            if warehouse_id:
                record.warehouse_id = warehouse_id.id

    @api.model
    def set_dashboard_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('mrp.menu_mrp_root').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-manufacturing-dashboard'})

    
    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    warehouse_id = fields.Many2one('stock.warehouse', compute=_compute_warehouse_id, store=True)
    mrp_plan_name = fields.Char(related='mrp_plan_id.name')

    def ks_validate_constraint(self):
        pass
