from odoo import models,fields,api

class returnOfAssets(models.Model):
    _name = 'return.of.assets'
    
    product_template_id = fields.Many2one('product.template')
    lot_id = fields.Many2one('stock.production.lot')
    current_value = fields.Float()
    work_order_cost = fields.Float(compute='_compute_work_order_cost')
    work_order_cost_shadow = fields.Float()
    repair_order_cost = fields.Float(compute='_compute_work_order_cost')
    repair_order_cost_shadow = fields.Float()
    income = fields.Float(compute='_compute_income')
    income_shadow = fields.Float()
    retun_of_asset = fields.Float(compute='_compute_retun_of_asset')
    retun_of_asset_shadow = fields.Float()
    
    @api.depends('income','work_order_cost','repair_order_cost','current_value')
    def _compute_retun_of_asset(self):
        for record in self:
            try:
                retun_of_asset = (record.income - (record.work_order_cost + record.repair_order_cost)) * 100
                record.retun_of_asset = retun_of_asset / record.current_value
                if record.retun_of_asset_shadow != record.retun_of_asset:
                    record.write({'retun_of_asset_shadow':record.retun_of_asset})
                    
                
            except ZeroDivisionError:
                record.retun_of_asset = 0    
            
    
    @api.depends('product_template_id','lot_id')
    def _compute_work_order_cost(self):
        for record in self:
            wo_cost = 0
            ro_cost = 0
            if record.product_template_id and record.lot_id:
                equipment = self.env['maintenance.equipment'].search([('product_template_id','=',record.product_template_id.id),('lot_id','=',record.lot_id.id)])
                if equipment:
                    for eq in equipment:
                        if eq.workorder_ids:
                            repair_orders = self.env['maintenance.repair.order'].search([
                                ('work_order_id', 'in', eq.workorder_ids.ids)
                            ])
                            # Get repair order cost
                            for ro in repair_orders:
                                if ro.invoice_id.state == 'posted':
                                    ro_cost += ro.invoice_id.amount_total
                            
                            # Get work order cost
                            for wo in eq.workorder_ids:
                                if wo.invoice_id.state == 'posted':
                                    wo_cost += wo.invoice_id.amount_total
            record.work_order_cost = wo_cost
            if record.work_order_cost != record.work_order_cost_shadow:
                record.write({'work_order_cost_shadow':record.work_order_cost})    

            record.repair_order_cost = ro_cost
            if record.repair_order_cost != record.repair_order_cost_shadow:
                record.write({'repair_order_cost_shadow': record.repair_order_cost})                      

    @api.depends('product_template_id','lot_id')
    def _compute_income(self):
        for data in self:
            if data.product_template_id and data.lot_id:
                self.env.cr.execute("""
                    SELECT  SUM(price_total) AS income FROM account_move_line WHERE serial_number_id = %s;
                """, [data.lot_id.id])
                value_ids = self._cr.fetchall()
                if value_ids[0][0]:
                    data.income = value_ids[0][0]
                    data.write({'income_shadow':data.income})
                else:
                    data.income = 0
            else:
                data.income = 0
    
    