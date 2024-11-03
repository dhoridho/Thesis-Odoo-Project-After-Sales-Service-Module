# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class rma_report(models.Model):
    _name = "rma.report"
    _description = "RMA Statistics"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    name = fields.Char('RMA', readonly=True)
    sale_id = fields.Many2one('sale.order', string='Order Reference')
    picking_id = fields.Many2one('stock.picking', string='Delivery Order')
    date = fields.Date('Date', readonly=True)
    deadline_date = fields.Date('Expected Closing', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Channel', readonly=True, oldname='section_id')
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    
    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm'),
                              ('process','Processing'),
                              ('close','Close'),
                              ('reject','Reject')], string='State', readonly=True)
                              
                              
    
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
#    nbr = fields.Integer('# of Lines', readonly=True)
    delivered_qty = fields.Float('Delivered Qty')
    return_qty = fields.Float('Return Qty')
    replace_product_id = fields.Many2one('product.product', 'Replace Product', readonly=True)
    replace_qty = fields.Float('Replace Pro. Qty', readonly=True)
    
    country_id = fields.Many2one('res.country', 'Partner Country', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', 'Commercial Entity', readonly=True)

    def _select(self):
        select_str = """
             SELECT min(l.id) as id,
                    l.product_id as product_id,
                    l.replace_product_id as replace_product_id,
                    sum(l.delivered_qty) as delivered_qty,
                    sum(l.return_qty) as return_qty,
                    sum(l.replace_qty) as replace_qty,
                    r.name as name,
                    r.sale_id as sale_id,
                    r.picking_id as picking_id,
                    r.date as date,
                    r.deadline_date as deadline_date,
                    extract(epoch from avg(date_trunc('day',r.date)-date_trunc('day',r.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    r.state as state,
                    r.partner_id as partner_id,
                    r.user_id as user_id,
                    r.company_id as company_id,
                    t.categ_id as categ_id,
                    r.team_id as team_id,
                    p.product_tmpl_id,
                    partner.country_id as country_id,
                    partner.commercial_partner_id as commercial_partner_id
        """
        return select_str

    def _from(self):
        from_str = """
                dev_rma_line l
                      join dev_rma_rma r on (l.rma_id=r.id)
                      join res_partner partner on r.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY l.product_id,
                    l.replace_product_id,
                    r.sale_id,
                    r.picking_id,
                    l.rma_id,
                    t.categ_id,
                    r.name,
                    r.date,
                    r.deadline_date,
                    r.partner_id,
                    r.user_id,
                    r.state,
                    r.company_id,
                    r.team_id,
                    p.product_tmpl_id,
                    partner.country_id,
                    partner.commercial_partner_id
        """
        return group_by_str

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))
            
            
            
            


