
from odoo import models,api


class IrModel(models.Model):
    _inherit = 'ir.model'

    @api.model
    def check_model_report_stock_quantity_new(self):
        query = """
            DELETE from ir_model where model = 'report.stock.quantity.new'
        """
        self.env.cr.execute(query)