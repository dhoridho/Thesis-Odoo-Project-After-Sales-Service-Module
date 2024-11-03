
from odoo import fields, models,tools

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    product_state = fields.Selection(related='scrap_id.state', string='Scrap Status')
    usage_type = fields.Many2one('usage.type', string="Scrap Type", related='scrap_id.scrap_type')
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", related='scrap_id.warehouse_id')
    
class StockScrapRequest(models.Model):
    _inherit = 'stock.scrap.request'
    
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
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False
    
    def action_print(self):
        return self.env.ref('equip3_inventory_reports.action_report_stock_scrap_request').report_action(self)
