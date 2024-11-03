# -*- coding: utf-8 -*-

from odoo import fields, models, api

class PosTopSellingWizard(models.TransientModel):
    _name = "pos.top.selling.wizard"
    _description = "POS Top Selling Wizard"


    start_dt = fields.Date('Start Date', required = True)
    end_dt = fields.Date('End Date', required = True)
    report_type = fields.Char('Report Type', readonly = True, default='PDF')
    no_product=fields.Integer("Number of Products (Top)",required=True)
    top_selling=fields.Selection([('products', 'Products'),('customers', 'Customers'),('categories', 'Categories'),
        ], string="Top Selling",default="products")
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)
    
    
    def top_selling_generate_report(self):
        return self.env.ref('equip3_pos_report.action_top_selling_report').report_action(self)
