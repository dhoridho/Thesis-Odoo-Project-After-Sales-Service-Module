from odoo import models, fields, api, _,SUPERUSER_ID


class AccountMove(models.Model):
    _inherit = 'account.move'

    requisition_id = fields.Many2one('purchase.requisition', string="purchase requisition")
    consignment_id = fields.Many2one('consignment.agreement', string="Consignment ID")

    svl_line_id = fields.Many2one('stock.valuation.layer.line', string='Valuation Line')
    svl_line_ids = fields.Many2many('stock.valuation.layer.line', string='Valuation Lines')

    """ The reason this field still exists is that this field is still used in the project """
    svl_source_id = fields.Many2one('stock.valuation.layer.source', string="SVL Source ID")
    svl_source_ids = fields.Many2many('stock.valuation.layer.source', 'account_account_svl_source_rel',
        'account_id', 'svl_source_id', string='Svl Source IDS')
    
    sale_order_line_ids = fields.Many2many(
        'sale.order.line',
        string="Sale Order Line",
        readonly=True,
        copy=False,
    )
    # technical fields for commision account move
    is_commission = fields.Boolean()

    def unlink(self):
        if len(self) <= 1:
            for rec in self:
                # this is for account move product
                if rec.consignment_id and rec.sale_order_line_ids:
                    for sol in rec.sale_order_line_ids:
                        sol.write({'is_billed_consignment': False})
                    account_move = self.env['account.move'].search([('consignment_id','=', rec.consignment_id.id), ('id', '!=', rec.id), ('state','=', 'draft')])
                    if account_move:
                        self.env.cr.execute(f"""DELETE FROM account_move where id = {account_move.id} """)

                # this is for account move consignment account
                if rec.consignment_id and rec.is_commission:
                    account_move = self.env['account.move'].search([('consignment_id','=', rec.consignment_id.id), ('id', '!=', rec.id), ('state','=', 'draft')])
                    for mv in account_move.sale_order_line_ids:
                        mv.write({'is_billed_consignment': False})
                    if account_move:
                        self.env.cr.execute(f"""DELETE FROM account_move where id = {account_move.id} """)
        else:
            for rec in self:
                if rec.consignment_id and rec.sale_order_line_ids:
                    for sol in rec.sale_order_line_ids:
                        sol.write({'is_billed_consignment': False})
        return super().unlink()

    def write(self, vals):
        for rec in self:
            if rec.consignment_id and rec.sale_order_line_ids and rec.state in ('cancel', 'expired'):
                for sol in rec.sale_order_line_ids:
                    sol.write({'is_billed_consignment': False})
        return super(AccountMove, self).write(vals)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_name(self):
        res = super(AccountMoveLine, self)._get_computed_name()
        self.ensure_one()

        if self.partner_id.lang:
            product = self.product_id.with_context(lang=self.partner_id.lang)
        else:
            product = self.product_id

        values = []
        if product.partner_ref:
            values.append(product.partner_ref)

        if product.product_tmpl_id.is_consignment:
            values.append(self.name)
            return self.name
        if not product.product_tmpl_id.is_consignment:
            return res
