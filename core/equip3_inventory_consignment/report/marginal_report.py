from odoo import tools
from odoo import api, fields, models, _

class MarginalReport(models.Model):
    _name = "marginal.report"
    _description = "Marginal Report"
    _order = "so_date desc"
    _auto = False

    product_name = fields.Char('Product Name')
    consignor = fields.Char('Consignor')
    consignee = fields.Char('Consignee')
    product_code = fields.Char('Product Code')
    reference = fields.Char('PO Reference')
    lot = fields.Char('Lot')
    product_qty = fields.Float('Product QTY')
    price_unit = fields.Float('Price Unit')
    purchase_price = fields.Float('Purchase Price')
    purchase_qty = fields.Float('Purchase QTY')
    purchase_total = fields.Float('Purchase Total')
    sale_order_name = fields.Char('Sale Order Line')
    sale_qty = fields.Float('Sale QTY')
    sale_price = fields.Float('Sale Price')
    margin = fields.Float('Margin')
    state = fields.Char('Consignment Status')
    so_date = fields.Date('SO Date')
    branch_id = fields.Many2one('res.branch', string='Branch')
    
    
    def init(self):
        # sol.qty_delivered == sml.qty_done
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """ SELECT sml.id as id,
                        product.product_display_name as product_name,
                        rp2.name as consignor,
                        rp.name as consignee,
                        product.default_code as product_code,
                        po.name as reference,
                        spl.name as lot,
                        product.total_available_qty as product_qty,
                        po.branch_id,
                        pol.price_unit as purchase_price,
                        pol.qty_received as purchase_qty,
                        pol.price_unit * pol.qty_received as purchase_total,
                        so.NAME as sale_order_name,
                        so.date_order as so_date,
                        sol.price_unit as price_unit,
                        sml.qty_done as sale_qty,
                        sml.qty_done * sol.price_unit as sale_price,
                        (sol.price_unit - pol.price_unit) * sml.qty_done as margin,
                        CASE
                            when product.total_available_qty = sum(sml.qty_done) then 'sold'
                            WHEN product.total_available_qty > sum(sml.qty_done) and sol.qty_delivered is not null then 'partial' 
                            WHEN product.total_available_qty > sum(sml.qty_done) then 'not_sold' 
                        end state
                    FROM sale_order_line as sol
                        left join sale_order as so ON sol.order_id = so.id
                        left join product_product as product ON product.id = sol.product_id
                        left join res_partner as rp ON rp.id = so.partner_id
                        join purchase_order_line as pol ON pol.id = sol.purchase_order_line_id
                        left join purchase_order as po ON po.id = pol.order_id
                        left join stock_picking as sp ON sp.sale_id = sol.order_id
                        left join stock_move as sm ON sm.picking_id = sp.id
                        left join stock_move_line as sml ON sml.move_id = sm.id
                        left join stock_production_lot as spl ON spl.id = sml.lot_id
                        left join res_partner as rp2 ON po.partner_id = rp2.id
                    WHERE so.is_consignment = True and sml.id is not null and sp.picking_type_code = 'outgoing'
                    GROUP BY sml.id,
                        product.product_display_name,
                        rp.name,
                        rp2.name,
                        product.default_code,
                        po.name,
                        lot,
                        product.total_available_qty,
                        sol.price_unit,
                        pol.price_unit,
                        pol.qty_received,
                        so.NAME,
                        so.date_order,
                        sol.qty_delivered,
                        po.branch_id"""
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s
            )""" % (self._table, query))
        # print(self._table)

    # def _select(self):
    #     select_str = """
    #         sol.id as id,
    #         product.product_display_name as product_name,
    #         rp2.name as consignor,
    #         rp.name as consignee,
    #         product.default_code as product_code,
    #         po.name as reference,
    #         spl.name as lot,
    #         product.total_available_qty as product_qty,
    #         pol.price_unit as purchase_price,
    #         pol.qty_received as purchase_qty,
    #         pol.price_unit * pol.qty_received as purchase_total,
    #         so.NAME as sale_order_name,
    #         so.date_order as so_date,
    #         sol.price_unit as price_unit,
    #         sol.qty_delivered as sale_qty,
    #         sol.qty_delivered * sol.price_unit as sale_price,
    #         (sol.price_unit - pol.price_unit) * sol.qty_delivered as margin,
    #         CASE
    #             when product.total_available_qty = sum(sol.qty_delivered) then 'sold'
    #             WHEN product.total_available_qty > sum(sol.qty_delivered) and sol.qty_delivered is not null then 'partial' 
    #             WHEN product.total_available_qty > sum(sol.qty_delivered) then 'not_sold' 
    #         end state
    #     """
    #     return select_str

    # def _from(self):
    #     from_str = """
    #         sale_order_line as sol
    #             left join sale_order as so ON sol.order_id = so.id
    #             left join product_product as product ON product.id = sol.product_id
    #             left join res_partner as rp ON rp.id = so.partner_id
    #             join purchase_order_line as pol ON pol.id = sol.purchase_order_line_id
    #             left join purchase_order as po ON po.id = pol.order_id
    #             left join stock_picking as sp ON sp.sale_id = sol.order_id
    #             left join stock_move as sm ON sm.picking_id = sp.id
    #             left join stock_move_line as sml ON sml.move_id = sm.id
    #             left join stock_production_lot as spl ON spl.id = sml.lot_id
    #             left join res_partner as rp2 ON po.partner_id = rp2.id
    #     """
    #     return from_str

    # def _where(self):
    #     where_str = """
    #         so.is_consignment = True
    #     """
    #     return where_str

    # def _group_by(self):
    #     group_by_str = """
    #         sol.id,
    #         product.product_display_name,
    #         rp.name,
    #         rp2.name,
    #         product.default_code,
    #         po.name,
    #         lot,
    #         product.total_available_qty,
    #         sol.price_unit,
    #         pol.price_unit,
    #         pol.qty_received,
    #         so.NAME,
    #         so.date_order,
    #         sol.qty_delivered
    #     """
    #     return group_by_str
    




