from odoo import models, fields, api, _


class Equip3MrpConsumptionInherit(models.Model):
    _inherit = 'mrp.consumption'

    is_a_subcontracting = fields.Boolean(string='Is a Subcontracting', default=False)
    move_subcon_ids = fields.One2many('stock.move', 'mrp_consumption_subcon_id', 'Subcontracting', readonly=True)

    requisition_id = fields.Many2one('purchase.requisition', string='Blanket Order', readonly=True)
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order', readonly=True)
    picking_id = fields.Many2one('stock.picking', 'Receipt', readonly=True)

    def _update_stock_valuation_layers(self):
        res = super(Equip3MrpConsumptionInherit, self)._update_stock_valuation_layers()
        production_id = self.manufacturing_order_id
        svl_subcontracting = self.move_subcon_ids.stock_valuation_layer_ids
        svl_subcontracting.type = 'subcon'
        svl_subcontracting.update({
            'mrp_plan_id': production_id.mrp_plan_id.id,
            'mrp_production_id': production_id.id,
            'mrp_consumption_id': self.id,
            'mrp_workorder_id': self.workorder_id.id,
        })
        self.write({'stock_valuation_layer_ids': [(4, svl.id) for svl in svl_subcontracting]})
        return res

    def get_subcontracting_cost(self):
        self.ensure_one()
        subcon_cost = 0.0
        for move in self.move_subcon_ids.filtered(lambda m: m.state == 'done'):
            subcon_cost += sum(move.stock_valuation_layer_ids.mapped('value'))
        return subcon_cost

    def get_finished_cost(self):
        finished_cost = super(Equip3MrpConsumptionInherit, self).get_finished_cost()
        return finished_cost - self.get_subcontracting_cost()

    def _create_subcon_move_lines(self, svl_product_id, svl_quantity, fg_product_id, fg_quantity, value):
        self.ensure_one()
        credit_account_id = svl_product_id.categ_id.property_stock_account_input_categ_id
        credit_line = self._prepare_move_line_vals(svl_product_id, svl_quantity, credit_account_id)
        credit_line['credit'] = value

        debit_account_id = fg_product_id.categ_id.mrp_wip_account_id
        debit_line = self._prepare_move_line_vals(fg_product_id, fg_quantity, debit_account_id)
        debit_line['debit'] = value
        return [(0, 0, debit_line), (0, 0, credit_line)]

    def _check_accounting_data(self):
        self.ensure_one()
        err_message = super(Equip3MrpConsumptionInherit, self)._check_accounting_data()
        for move in self.move_subcon_ids:
            move_product = move.product_id
            if not move_product.categ_id.property_stock_account_input_categ_id.id:
                err_message = _("Please set Stock Input Account for %s first!" % move_product.name)
                break
        return err_message

    def button_confirm(self):
        res = super(Equip3MrpConsumptionInherit, self).button_confirm()
        if self.requisition_id and self.move_finished_ids:
            self.env['mrp.requisition.subcon.operation'].create({
                'requisition_id': self.requisition_id.id,
                'purchase_id': self.purchase_id.id,
                'picking_id': self.picking_id.id,
                'production_id': self.manufacturing_order_id.id,
                'consumption_id': self.id,
                'date_validated': fields.Datetime.now(),
                'amount_received': self.finished_qty
            })
        return res

    def _finish_workorder(self):
        previous_is_last_workorder = self.is_last_workorder
        if self.workorder_id.is_a_subcontracting and self.manufacturing_order_id.workorder_ids[-1] != self.workorder_id:
            self.is_last_workorder = False
        super(Equip3MrpConsumptionInherit, self)._finish_workorder()
        if self.is_last_workorder != previous_is_last_workorder:
            self.is_last_workorder = previous_is_last_workorder
