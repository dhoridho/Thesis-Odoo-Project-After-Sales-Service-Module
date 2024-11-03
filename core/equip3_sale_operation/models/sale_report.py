from odoo import _, api, fields, models, tools

class SaleReport(models.Model):
    _inherit = "sale.report"

    city_id = fields.Many2one('res.country.city', 'City')
    state_id = fields.Many2one('res.country.state', string='State')
    untaxed_amount = fields.Float("Untaxed Amount", readonly=True)
    total_amount = fields.Float("Total Amount", readonly=True)
    grand_total_order = fields.Float("Grand Total", readonly=True)
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['city_id'] = ", partner.city_id as city_id"
        fields['state_id'] = ", partner.state_id as state_id"
        groupby += ', partner.city_id'
        groupby += ', partner.state_id'
        fields['untaxed_amount'] = ", SUM(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS untaxed_amount"
        fields['total_amount'] = ", SUM(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS total_amount"
        fields['grand_total_order'] = ", s.amount_total AS grand_total_order"
        fields['payment_term_id'] = ", s.payment_term_id AS payment_term_id"
        res = super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
        # res[131] + "\CASE WHEN l.product_id IS NOT NULL THEN sum(l.price_subtotal, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount,CASE WHEN l.product_id IS NOT NULL THEN sum(l.price_total, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as total_amount,"
        # res[1746] + "s.amount_total as grand_total_order,\n"
        return res