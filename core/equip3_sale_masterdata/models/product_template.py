
from odoo import models, fields, api, _


class ProductTemplate(models.Model): 
	_inherit = 'product.template'

	alternative_product_ids = fields.Many2many('product.product', 'product_product_alternative_rel', 'product_id', 'tmpl_id', string="Alternative Product")
	is_pack = fields.Boolean(string='Is Product Bundle')

	last_sales_price = fields.Float(string="Last Sales Price")
	last_sales_date = fields.Date(string="Last Sales Date")
	last_customer_id = fields.Many2one(comodel_name="res.partner", string="Last Customer")
	description_sale = fields.Text(
        'Sales Description', translate=True,
        help="A description of the Product that you want to communicate to your customers. "
             "This description will be copied to every Sales Order, Delivery Order and Customer Invoice/Credit Note",
		tracking=True)
	service_policy = fields.Selection([
        ('ordered_timesheet', 'Prepaid'),
        ('delivered_timesheet', 'Timesheets on tasks'),
        ('delivered_manual', 'Milestones (manually set quantities on order)')
    ], string="Service Invoicing Policy", compute='_compute_service_policy', inverse='_inverse_service_policy',tracking=True)
	service_tracking = fields.Selection([
        ('no', 'Don\'t create task'),
        ('task_global_project', 'Create a task in an existing project'),
        ('task_in_project', 'Create a task in sales order\'s project'),
        ('project_only', 'Create a new project but no task')],
        string="Service Tracking", default="no",
        help="On Sales order confirmation, this product can generate a project and/or task. \
        From those, you can track the service you are selling.\n \
        'In sale order\'s project': Will use the sale order\'s configured project if defined or fallback to \
        creating a new project based on the selected template.",tracking=True)
	project_id = fields.Many2one(
        'project.project', 'Project', company_dependent=True,
        domain="[('company_id', '=', current_company_id)]",
        help='Select a billable project on which tasks can be created. This setting must be set for each company.',tracking=True)
	expense_policy = fields.Selection(
        [('no', 'No'), ('cost', 'At cost'), ('sales_price', 'Sales price')],
        string='Re-Invoice Expenses',
        default='no',tracking=True,
        help="Expenses and vendor bills can be re-invoiced to a customer."
             "With this option, a validated expense can be re-invoice to a customer at its cost or sales price.")	


	def set_product_last_sales(self, order_id=False):
		SaleOrderLine = self.env["sale.order.line"]
		if not self.check_access_rights("write", raise_exception=False):
			return
		for product in self:
			date_order = False
			price_unit_uom = 0.0
			last_customer = False
				
			if order_id:
				lines = SaleOrderLine.search(
                    [("order_id", "=", order_id), ("product_id", "=", product.id)],
                    limit=1,
                )
			else:
				lines = SaleOrderLine.search(
                    [
                        ("product_id", "=", product.id),
                        ("state", "in", ["sale", "done"]),
                    ]
                ).sorted(key=lambda l: l.order_id.date_order, reverse=True)
				
			if lines:
				
				last_line = lines[:1]
				
				date_order = last_line.order_id.date_order
                
				price_unit_uom = product.uom_id._compute_quantity(
                    last_line.price_unit, last_line.product_uom
                )
				last_customer = last_line.order_id.partner_id
				
			product.write(
				{
					"last_sales_date": date_order,
					"last_sales_price": price_unit_uom,
					"last_customer_id": last_customer.id if last_customer else False,
				}
			)