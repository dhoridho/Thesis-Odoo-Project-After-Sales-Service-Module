from odoo import models, fields, api, tools


class MrpConsumption(models.Model):
    _inherit = 'mrp.consumption'

    @api.depends('location_dest_id')
    def _compute_warehouse_id(self):
        for record in self:
            record.warehouse_id = False
            location_dest_id = record.location_dest_id
            if location_dest_id:
                record.warehouse_id = location_dest_id.get_warehouse().id

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
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', compute=_compute_warehouse_id, store=True)
