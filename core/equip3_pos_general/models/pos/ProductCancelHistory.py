# -*- coding: utf-8 -*

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _

class ProductCancelHistory(models.Model):
    _name = "product.cancel"
    _description = 'Product Cancel'
    _rec_name = 'order_ref'

    order_ref = fields.Char(string='Order Reference')
    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Float(string='Qty')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    src_location_id = fields.Many2one('stock.location', string='Source Location')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    cancel_reason = fields.Text(string='Reason Cancel')
    pos_order_id = fields.Many2one('pos.order', string='POS Order', compute='_compute_pos_order_id')
    cancel_date = fields.Date(string='Cancel Date')
    company_id = fields.Many2one('res.company','Company',related="product_id.company_id")
    branch_id = fields.Many2one('res.branch','Branch',related="product_id.branch_id")
    last_supplier_id = fields.Many2one("res.partner", string="Vendor",related='product_id.last_supplier_id',store=True)

    def SavelogProcuctCancel(self, vals=[], product_id=False, qty=False, date=False):
        if vals:
            return self.create({
                'product_id': vals.get('product_id'),
                'qty': vals.get('qty'),
                # 'cancel_date' : datetime.date(2022,11,26)
                'cancel_date' : fields.Date.today()
            }).id
        else:
            return self.create({
                'product_id': product_id,
                'qty': qty,
                'cancel_date' : date
            }).id

    def _compute_pos_order_id(self):
        results = {}
        order_refs = list(set([h.order_ref for h in self if h.order_ref]))
        if order_refs:
            query = '''
                SELECT pos_reference, id FROM pos_order WHERE pos_reference IN (%s)
            ''' % (str(order_refs)[1:-1])
            self.env.cr.execute(query)        
            results = {x[0]: x[1] for x in self.env.cr.fetchall()}

        for rec in self:
            pos_order_id = False
            if rec.order_ref and results and results.get(rec.order_ref):
                pos_order_id = results[rec.order_ref]
            rec.pos_order_id = pos_order_id

    def schedule_cancel_date(self):
        today = date.today() - relativedelta(days=30)
        cancel = self.search([('cancel_date', '<', today)])
        for line in cancel:
            line.unlink()