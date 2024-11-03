
from odoo import api, fields, models, tools

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    department_id = fields.Many2one(related='requested_by.department_id', string="Department", readonly=True, store=True)

class PurchaseRequestReport(models.Model):
    _name = "purchase.request.report"
    _descriptin = 'Purchase Request Report'
    _auto = False

    name = fields.Char(string='Reference')
    product_qty = fields.Float(string='Purchase Requested Qty')
    create_date = fields.Datetime(string='Create Date')
    category_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    requested_by = fields.Many2one(comodel_name="res.users", string="Requested by")
    assigned_to = fields.Many2one(comodel_name="res.users", string="Approver")
    expiry_date = fields.Date(string="Expiry Date")
    origin = fields.Char("Source Document")
    group_id = fields.Many2one('procurement.group', string="Procurement Group")
    state = fields.Selection([
        ("draft", "Draft"),
        ("to_approve", "To be approved"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("done", "Done"), ],
        string='Status')
    purchase_req_state = fields.Selection([
        ('pending', 'Pending'), 
        ('in_progress', 'In Progress'), 
        ('done', 'Done'), 
        ('close', 'Closed'), 
        ('cancel', 'Cancelled')])
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type')
    company_id = fields.Many2one('res.company', string='Company')
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    product_uom_id = fields.Many2one('uom.uom', string='UOM')
    date_required = fields.Date(string="Request Date")   
    estimated_cost = fields.Float(string="Estimated Cost")
    department_id = fields.Many2one('hr.department', string='Department',
                                    help='Select department')
    


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))

    def _select(self):
        select_str = """
            SELECT
            min(prl.id) as id,
            prl.product_id,
            prl.product_qty,
            pr.create_date,
            pr.name,
            pr.requested_by,
            pr.assigned_to,
            pr.expiry_date,
            pr.origin,
            t.categ_id as category_id,
            pr.group_id,
            pr.state,
            pr.purchase_req_state,
            pr.picking_type_id,
            pr.company_id,
            pr.branch_id,
            prl.product_uom_id,
            prl.date_required,
            prl.estimated_cost,
            pr.department_id
        """
        return select_str

    def _from(self):
        from_str = """
            purchase_request_line prl
                join purchase_request pr on (prl.request_id=pr.id)
                left join product_product p on (prl.product_id=pr.id)
                left join product_template t on (p.product_tmpl_id=t.id)
            """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                prl.product_id,
                prl.product_qty,
                pr.create_date,
                pr.name,
                pr.requested_by,
                pr.assigned_to,
                pr.expiry_date,
                pr.origin,
                pr.group_id,
                pr.state,
                t.categ_id,
                pr.purchase_req_state,
                pr.picking_type_id,
                pr.company_id,
                pr.branch_id,
                prl.product_uom_id,
                prl.date_required,
                prl.estimated_cost,
                pr.department_id
            """
        return group_by_str
