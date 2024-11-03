from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.opportunity_id:
            if res.opportunity_id.salesperson_lines:
                for line in res.opportunity_id.salesperson_lines:
                    target = self.env['crm.target'].search([('salesperson_id','=',line.salesperson_id.id),('state','=','approved'),('start_date','<=',fields.Date.today()),('end_date','>=',fields.Date.today())])
                    if target:
                        if target.based_on == 'amount':
                            target.current_achievement += res.amount_untaxed * (line.weightage / 100)
                        else:
                            target.current_achievement += sum(res.order_line.mapped("product_uom_qty")) or 0.0 * (line.weightage / 100)
                        target.target_left = target.main_target - target.current_achievement
        return res