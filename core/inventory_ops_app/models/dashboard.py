from odoo import models, fields, api

class StockPickingTypeDeshboard(models.Model):
    _inherit = 'stock.picking.type.dashboard'

    def get_dashboard_info(self, wh_id):
        data_list = []
        code_dict = dict([('incoming', 'Receipt'),
        ('outgoing', 'Delivery'),
        ('internal', 'Internal Transfer')])
        for record in self.search([('warehouse_id', '=', wh_id), ('code', 'in', list(code_dict.keys()))]):
            vals = {}
            vals['code'] = record.code
            vals['name'] = code_dict[record.code]
            vals['warehouse_id'] = wh_id
            vals['late'] = record.count_picking_late
            vals['ready'] = record.count_picking_ready
            vals['draft'] = record.count_picking_draft
            vals['waiting'] = record.count_picking_waiting
            vals['backorders'] = record.count_picking_backorders
            data_list.append(vals)
        return data_list

StockPickingTypeDeshboard()