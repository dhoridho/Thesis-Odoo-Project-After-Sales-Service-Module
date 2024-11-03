
from odoo import models, fields, api, http, _
from datetime import datetime
from lxml import etree

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def default_get(self, fields_list):
        res = super(ResPartner, self).default_get(fields_list)
        if 'supplier_rank' in res and 'customer_rank' in res:
            if res['supplier_rank'] != 0 or res['customer_rank'] != 0:
                res.update({'company_id': self.env.company.id})
        if res.get('is_customer', True):
            vals = fields.Date.today()
            res.update({'customer_creation_date': vals})
        return res

    customer_sequence = fields.Char(string="ID", readonly=True, copy=False)
    debtor_id = fields.Many2one('customer.degree.trust', string="Trust Degree", compute="_compute_debtor_id", store=False)
    is_customer = fields.Boolean(string='Customer')
    company_id = fields.Many2one('res.company', string='Company')
    is_limit_salesperson = fields.Boolean(string='Limit Salesperson', default=False)
    customer_category = fields.Many2one('customer.category', string="Customer Category")
    property_product_pricelist = fields.Many2one(
        'product.pricelist', 'Pricelist', compute='',
        inverse="_inverse_product_pricelist", company_dependent=False,
        help="This pricelist will be used, instead of the default one, for sales to the current partner")
    res_city_id = fields.Many2one('res.country.city', 'City')
    city_id = fields.Many2one('res.city', string='City of Address', invisible=True)
    customer_creation_date = fields.Date(string='Customer Creation Date', readonly=True)
    
    # @api.model
    # def default_get(self, field_list):
    #     res = super(ResPartner, self).default_get(field_list)
    #     if res.get('is_customer', True):
    #         vals = fields.Date.today()
    #         res.update({'customer_creation_date': vals})


    @api.onchange('customer_category')
    def compute_product_pricelist(self):
        if self.customer_category:
            pricelist = self.env['product.pricelist'].search([('customer_category', '=', self.customer_category.id)])
            self.property_product_pricelist = pricelist

    @api.onchange('is_customer')
    def onchange_customer_creation_date(self):
        if self.is_customer == True:
            self.customer_creation_date = fields.Date.today()
        if self.is_customer == False:
            self.customer_creation_date = False
    
    

    # @api.onchange('customer_category')
    # def set_available_customer_category(self):
    #     domain = [('company_id','=', self.company_id.id)]
    #     available_category = self.env['customer.category'].sudo().search(domain)
    #     return {'domain': {'customer_category': [('id', 'in', available_category.ids)]}}

    @api.model
    def create(self, values):
        if 'is_customer' in values:
            if values.get('is_customer', False):
                sequence = self.env['ir.sequence'].next_by_code('res.partner.customer.sequence')
                values.update({'customer_sequence': sequence})
                values.update({'customer_rank': 1})
            else:
                values.update({'customer_rank': 0})

        res = super(ResPartner, self).create(values)
        return res

    def write(self, values):
        if values.get('is_customer') == True and self.is_customer == False:
            sequence = self.env['ir.sequence'].next_by_code('res.partner.customer.sequence')
            values.update({'customer_sequence': sequence})
            values.update({'customer_rank': 1})
        elif values.get('is_customer') == False and self.is_customer == True:
            res = super(ResPartner, self).write(values)
            if self.create_date != self.write_date:
                is_data_exist = 0
                res_data = self.env['sale.order'].search([('partner_id', '=', self.ids[0])], limit=1)
                if len(res_data) > 0:
                    is_data_exist = 1

                if is_data_exist == 0:
                    res_data = self.env['account.move'].search([('partner_id', '=', self.ids[0])], limit=1)
                    if len(res_data) > 0:
                        is_data_exist = 1

                if is_data_exist == 1:
                    # values.update({'is_customer': True})
                    # res = super(ResPartner, self).write(values)
                    pass
                else:
                    # values.update({'is_customer': False})
                    values.update({'customer_sequence': None})
                    values.update({'customer_rank': 0})

        res = super(ResPartner, self).write(values)
        return res
     
    def _compute_debtor_id(self):
        no_of_invoices_overdue = 0
        no_of_invoice_days_overdue = 0
        for record in self:
            record.debtor_id = False
            invoice_ids = self.env['account.move'].search([('partner_id', '=', record.id),
                                                           ('move_type', '=', 'out_invoice'),
                                                           ('state', '=', 'posted'),
                                                           ('payment_state','=','not_paid'),
                                                           ('invoice_date_due', '<', datetime.now().date())])
            no_of_invoices_overdue = sorted(invoice_ids, key=lambda k: k['invoice_date_due'])
            if len(no_of_invoices_overdue) > 0:
                invoice_date = datetime.now().date() - no_of_invoices_overdue[0].invoice_date_due
                no_of_invoice_days_overdue += invoice_date.days
            index = len(no_of_invoices_overdue) * no_of_invoice_days_overdue
            customer_degree_trust_ids = self.env['customer.degree.trust'].search([])
            sort_customer_degree_trust_ids = sorted(customer_degree_trust_ids, key=lambda k: k['index'])
            i = 0
            for item in sort_customer_degree_trust_ids:
                if sort_customer_degree_trust_ids[i+1] == sort_customer_degree_trust_ids[-1]:
                    break
                if index == 0:
                    record.debtor_id = sort_customer_degree_trust_ids[0].id
                    break
                if sort_customer_degree_trust_ids[i].index < index <= sort_customer_degree_trust_ids[i+1].index:
                    record.debtor_id = sort_customer_degree_trust_ids[i+1].id
                i += 1
            if not record.debtor_id:
                record.debtor_id = sort_customer_degree_trust_ids[-1].id

    def export_data(self, fields_to_export):
        default_fields_to_export = ['vendor_sequence', 'customer_sequence', 'display_name', 'phone', 'email', 'rfm_segment_id', 'user_id', 'activity_ids', 'city', 'country_id', 'branch_id', 'company_id']
        if fields_to_export == default_fields_to_export:
            # update context untuk pengecekan model ketika print header excel
            ctx = (http.request.context.copy())
            ctx.update(res_partner=True)
            http.request.context = ctx
            # merubah field yg akan di export pada customer dan vendor
            fields_to_export = ['id','display_name', 'phone', 'mobile', 'email', 'country_id', 'city', 'company_id', 'is_vendor', 'is_customer']
        else:
            # update context untuk skip perubahan
            ctx = (http.request.context.copy())
            ctx.update(skip=True)
        res = super().export_data(fields_to_export)
        return res

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Customers'),
            'template': '/equip3_sale_masterdata/static/xls/res_partner.xls'
        }]