# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools


class POSProfitAndLoss(models.Model):
    _name = 'pos.profit.and.loss'
    _description = 'POS Profit and Loss'
    _auto = False

    start_datetime = fields.Datetime(string='Start Datetime')
    end_datetime = fields.Datetime(string='End Datetime')

    pos_order_line_id = fields.Many2one('pos.order.line')
    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Float(string='Quantity')
    product_uom_id = fields.Many2one('uom.uom', string='UoM', related='pos_order_line_id.product_uom_id')
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Discount')
    taxes = fields.Float(string='Taxes')
    price_subtotal = fields.Float(string='Amount Without Taxes')
    cost_price = fields.Float('Cost Price')
    profit_and_loss = fields.Float(string='Gross Profit and Loss')
    percentage_profit_and_loss = fields.Float(string='Gross PL (%)',digits=(16, 1))

    pos_branch_id = fields.Many2one('res.branch', string='Branch')
    partner_id = fields.Many2one('res.partner', string='Customer')
    company_id = fields.Many2one('res.company', string='Company')
    pos_config_id = fields.Many2one('pos.config', string='Point of Sale')
    order_id = fields.Many2one('pos.order', string='Order')
    session_id = fields.Many2one('pos.session', string='Session')
    date_order = fields.Datetime(string='Order Date')
    categ_id = fields.Many2one('product.category', string='Product Category')
    pos_categ_id = fields.Many2one('pos.category', string='POS Category')
    vendor_id = fields.Many2one('res.partner','Vendor')

    def init(self):
        query = """
        SELECT
            pp.id AS product_id,
            pb.id AS pos_branch_id,
            po.id AS order_id,
            rc.id AS company_id,
            po.partner_id AS partner_id,
            po.session_id AS session_id,
            po.date_order AS date_order,
            ss.config_id AS pos_config_id,
            pp.categ_id AS categ_id,
            pt.pos_categ_id AS pos_categ_id,
            pp.last_supplier_id as vendor_id,



            pol.id AS id,
            pol.id AS pos_order_line_id,
            po.date_order AS start_datetime,
            po.date_order AS end_datetime,
            pol.price_unit AS price_unit,
            pol.price_subtotal AS price_subtotal,
            (pol.price_unit * pol.qty * pol.discount) / 100 AS discount,
            pol.price_subtotal_incl - pol.price_subtotal AS taxes,
            coalesce((select value_float from ir_property where name = 'standard_price' and res_id = CONCAT('product.product,',pol.product_id)), 0) AS cost_price,
            pol.price_subtotal_incl - (coalesce((select value_float from ir_property where name = 'standard_price' and res_id = CONCAT('product.product,',pol.product_id)), 0) * pol.qty) AS profit_and_loss,

            NULLIF(
                (NULLIF(coalesce((pol.price_subtotal_incl - (coalesce((select value_float from ir_property where name = 'standard_price' and res_id = CONCAT('product.product,',pol.product_id)), 0) * pol.qty)),0)
                                      / NULLIF((coalesce((select value_float from ir_property where name = 'standard_price' and res_id = CONCAT('product.product,',pol.product_id)), 0) * pol.qty), 0),0)) * 100
            ,0)
            AS percentage_profit_and_loss,


            pol.qty AS qty

        FROM
            pos_order_line pol
            left join res_branch pb on pol.pos_branch_id=pb.id
            left join res_company rc on pol.company_id=rc.id
            left join pos_order po on pol.order_id=po.id
            left join pos_session ss on po.session_id=ss.id
            left join product_product pp on pol.product_id=pp.id
            left join product_template pt on pp.product_tmpl_id=pt.id

        where po.state <> 'cancel' and NOT (po.pos_reference LIKE '%VOID%')

        ORDER BY
            pol.id
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query))


