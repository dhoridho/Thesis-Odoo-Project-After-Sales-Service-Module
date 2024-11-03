# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import date, datetime


class PosOrder(models.Model):
    _inherit = 'pos.order'

    location_id = fields.Many2one(comodel_name='stock.location',string="Location", store=True,compute="compute_location")
    date_order_str = fields.Char("Date Order String",compute='_compute_date_order_str')

    def _compute_date_order_str(self):
    	for data in self:
    		date_order_str = False
    		if data.date_order:
    			date_order_str = data.date_order.strftime('%d-%m-%Y')
    		data.date_order_str = date_order_str


    @api.depends('picking_ids')
    def compute_location(self):
        for rec in self:
            rec.location_id = False
            for pck in rec.picking_ids:
                rec.location_id = pck.location_id

    def update_order_summery(self, ord_st_date, ord_end_date, ord_state,curr_session,order_current_session):
        to_day_date = datetime.now().date()     
        summery_order = []
        current_lang = self.env.context

        if order_current_session == True:
            if ord_state == 'Select State':
                orders = self.env['pos.order'].search_read([
                    ('session_id', '=', curr_session),
                    ('state', 'in', ['paid','invoiced','done']),
                    ],['name','amount_total','date_order_str','state'])
            else:
                orders = self.env['pos.order'].search_read([
                    ('session_id', '=', curr_session),
                    ('state','=',ord_state.lower()),
                    ],['name','amount_total','date_order_str','state'])

        else:
            if ord_state == 'Select State':
                orders = self.env['pos.order'].search_read([
                    ('date_order', '>=', ord_st_date + ' 00:00:00'),
                    ('date_order', '<=', ord_end_date + ' 23:59:59'),
                    ('state', 'in', ['paid','invoiced','done']),
                    ],['name','amount_total','date_order_str','state'])
            else:
                orders = self.env['pos.order'].search_read([
                    ('date_order', '>=', ord_st_date + ' 00:00:00'),
                    ('date_order', '<=', ord_end_date + ' 23:59:59'),
                    ('state','=',ord_state.lower()),
                    ],['name','amount_total','date_order_str','state'])
        if orders:
        	summery_order = orders
        return summery_order
    
    def update_product_summery(self,pro_st_date,pro_ed_date,prod_current_session,curr_session):
        config_obj = self.env['pos.config'].search([])
        current_lang = self.env.context

        if prod_current_session == True:
            orders = self.env['pos.order'].search([
            ('session_id', '=', curr_session),
            ('state', 'in', ['paid','invoiced','done']),
            ('config_id', 'in', config_obj.ids)])

        else:
            orders = self.env['pos.order'].search([
                ('date_order', '>=', pro_st_date + ' 00:00:00'),
                ('date_order', '<=', pro_ed_date + ' 23:59:59'),
                ('state', 'in', ['paid','invoiced','done']),
                ('config_id', 'in', config_obj.ids)])

        pos_line_ids = self.env["pos.order.line"].search([('order_id', 'in', orders.ids)]).ids
        
        
        if pos_line_ids:
            self.env.cr.execute("""
                SELECT product_tmpl.name, sum(pos_line.qty) total
                FROM pos_order_line AS pos_line,
                     pos_order AS pos_ord,
                     product_product AS product,
                     product_template AS product_tmpl
                WHERE pos_line.product_id = product.id
                    AND product.product_tmpl_id = product_tmpl.id
                    AND pos_line.order_id = pos_ord.id
                    AND pos_line.id IN %s 
                GROUP BY product_tmpl.name
                
            """, (tuple(pos_line_ids),))
            products = self.env.cr.dictfetchall()
        else:
            products = []


        return products


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    state_related = fields.Selection(related='order_id.state')

 
class PosOrderLocation(models.Model):
    _name = "pos.order.location" 
    _description = "POS Order Locaton"

    
    def update_location_summery(self, location,select_session,tab1,tab2):
        res = []
        prod =[]
        prod_data ={}
        product_ids = self.env['product.product'].search([])
        if tab1 == True:
            session_id = self.env['pos.session'].browse(int(select_session))
            orders = self.env['pos.order'].search([
                    ('session_id', '=', session_id.id),
                    ('state', 'in', ['paid','invoiced','done']),
                    ])
            for odr in orders:
                for line in odr.lines:
                    quants = self.env['stock.quant'].search([('product_id.id', '=', line.product_id.id),
                        ('location_id.id', '=', odr.location_id.id)])
                    product = line.product_id.name
                    if product in prod_data:
                        old_qty = prod_data[product]['qty']
                        prod_data[product].update({
                        'qty' : old_qty+line.qty,
                        })
                    else:
                        if len(quants) > 1:
                            quantity = 0.0
                            for quant in quants:
                                quantity += quant.quantity

                            prod_data.update({ product : {
                                'product_id':line.product_id.id,
                                'product_name':line.product_id.name,
                                'qty' : line.qty,
                                'avail_qty':quantity,
                            }})
                        else:
                            prod_data.update({ product : {
                                'product_id':line.product_id.id,
                                'product_name':line.product_id.name,
                                'qty' : line.qty,
                                'avail_qty':quants.quantity,
                            }})
        else:
            orders = self.env['pos.order'].search([('state', 'in', ['paid','invoiced','done']),])
            location_id = int(location)
            for odr in orders:
                if odr.location_id.id == location_id :
                    for line in odr.lines:
                        quants = self.env['stock.quant'].search([
                            ('product_id.id', '=', line.product_id.id),
                            ('location_id.id', '=', location_id)])
                        product = line.product_id.name
                        if product in prod_data:
                            old_qty = prod_data[product]['qty']
                            prod_data[product].update({
                                'qty' : old_qty+line.qty,
                            })
                        else:
                            if len(quants) > 1:
                                quantity = 0.0
                                for quant in quants:
                                    quantity += quant.quantity

                                prod_data.update({ product : {
                                    'product_id':line.product_id.id,
                                    'product_name':line.product_id.name,
                                    'qty' : line.qty,
                                    'avail_qty':quantity,
                                }})
                            else:
                                prod_data.update({ product : {
                                    'product_id':line.product_id.id,
                                    'product_name':line.product_id.name,
                                    'qty' : line.qty,
                                    'avail_qty':quants.quantity,
                                }})
        return prod_data