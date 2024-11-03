from odoo import api, fields, models, _
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

class AccountMapLineMasterdata(models.Model):
    _name = 'account.account.map.line'
    _description = 'Account Map Line'
    _check_company_auto = False

    company_id = fields.Many2one('res.company', string='Parent Company', related='map_id.company_id')
    account_id = fields.Many2one('account.account', string='Parent Company Account', check_company=False, domain="[('company_id', '=', company_id)]")
    target_company = fields.Many2one('res.company', string='Target Company', related='map_id.child_company_id')
    target_account = fields.Many2one('account.account', string='Child Company Account', domain="[('company_id', '=', target_company)]", check_company=False, readonly=True)
    map_id = fields.Many2one('account.account.map')

class AccountMapMasterdata(models.Model):
    _name = 'account.account.map'
    _description = 'Account Map'
    _check_company_auto = False

    company_id = fields.Many2one('res.company', string="Parent Company", required=True, readonly=True, default=lambda self: self.env.company.id, tracking=True)
    line_ids = fields.One2many('account.account.map.line', 'map_id', string='Accounts')

    child_company_id = fields.Many2one('res.company', string="Child Company", required=True, tracking=True)
    ownership  = fields.Float(string='Ownership')
    sales_line_ids = fields.One2many('account.tax.map.sales.line', 'map_id', string="Sales Taxes", tracking=True)
    purchase_line_ids = fields.One2many('account.tax.map.purchase.line', 'map_id', string="Purchase Taxes ", tracking=True)

    def _valid_field_parameter(self, field, name):
        return name == "tracking" or super()._valid_field_parameter(field, name)
    

    def auto_map_account(self):
        for record in self:
            context = dict(record.env.context)
            context.update({'allowed_company_ids': [record.company_id.id, record.child_company_id.id],
                            'params': {'cids': str(record.company_id.id) + ',' + str(record.child_company_id.id)}})
            record.env.context = context
            comp = record.env['res.company'].search([('id', 'in', [record.company_id.id, record.child_company_id.id])])
            record.env.companies = comp

            record.ownership = 100.00
            account = record.env['account.account'].with_context(allowed_company_ids=[record.company_id.id, record.child_company_id.id])
            line_id_child = account.search([('company_id', '=', record.child_company_id.id)])

            list_line = [(5, 0, 0)]
            for line in line_id_child:
                record.env.cr.execute("""
                    SELECT id
                    FROM account_account
                    WHERE code = %s AND company_id = %s
                    LIMIT 1;
                    """, (line.code, record.company_id.id))
                result = record.env.cr.fetchone()
                matching_account_id = result[0] if result else False

                lines_dict = {'company_id': record.company_id.id,
                            'account_id': False,
                            'target_company': record.child_company_id.id,
                            'target_account': line.id,
                            'account_id': matching_account_id,
                            'map_id': record.id}
                list_line.append((0, 0, lines_dict))
            record.line_ids = list_line

    @api.onchange('child_company_id')
    def _write_detail(self):
        if self.child_company_id:
            if self.child_company_id.id != False:
                context = dict(self.env.context)
                context.update({'allowed_company_ids' : [self.company_id.id, self.child_company_id.id],'params' : {'cids' : str(self.company_id.id)+','+str(self.child_company_id.id) }})
                self.env.context = context
                comp = self.env['res.company'].search([('id', 'in', [self.company_id.id, self.child_company_id.id])])
                self.env.companies = comp
                
                self.ownership = 100.00
                account = self.env['account.account'].with_context(allowed_company_ids=[self.company_id.id, self.child_company_id.id])
                line_id_child = account.search([('company_id', '=', self.child_company_id.id)])       


                list_line=[(5,0,0)]
                n = len(line_id_child)
                i = 0
                while i < n:
                    query = """
                        SELECT id
                        FROM account_account
                        WHERE code = %s AND company_id = %s
                        LIMIT 1;
                        """

                    # Execute the query with parameters
                    self.env.cr.execute(query, (line_id_child[i].code, self.company_id.id))

                    # Fetch the result
                    result = self.env.cr.fetchone()
                    matching_account_id = result[0] if result else False

                    # matching_account = account.search([('code', '=', line_id_child[i].code), ('company_id', '=', self.company_id.id)], limit=1)
                    # parent_account = self.env['account.account'].search([('code', '=', code_account), ('company_id', '=', self.company_id.id)], limit=1)

                    lines_dict = {'company_id' : self.company_id.id,
                                  'account_id' : False,
                                  'target_company' : self.child_company_id.id,
                                  'target_account' : line_id_child[i].id,
                                  'map_id' : self.id,
                                  }
                    list_line.append((0,0,lines_dict))
                    i += 1
                self.line_ids = list_line
                
                line_id_child = self.env['account.tax'].search(['&', ('company_id', '=', self.child_company_id.id), ('type_tax_use', '=', 'sale')])            
                list_line=[(5,0,0)]
                n = len(line_id_child)
                i = 0
                while i < n:
                    lines_dict = {'company_id' : self.company_id.id,
                                  'sales_tax_id' : False    ,
                                  'target_company' : self.child_company_id.id,
                                  'target_sales_tax' : line_id_child[i].id,}
                    list_line.append((0,0,lines_dict))
                    i += 1
                self.sales_line_ids = list_line

                line_id_child = self.env['account.tax'].search(['&', ('company_id', '=', self.child_company_id.id), ('type_tax_use', '=', 'purchase')])
                list_line=[(5,0,0)]
                n = len(line_id_child)
                i = 0
                while i < n:
                    lines_dict = {'company_id' : self.company_id.id,
                                  'purchase_tax_id' : False,
                                  'target_company' : self.child_company_id.id,
                                  'target_purchase_tax' : line_id_child[i].id,}
                    list_line.append((0,0,lines_dict))
                    i += 1
                self.purchase_line_ids = list_line


class AccountTaxMapSales(models.Model):
    _name = 'account.tax.map.sales.line'
    _description = 'Account Tax Map Sales Line'

    company_id = fields.Many2one('res.company', string='Parent Company', related='map_id.company_id')
    sales_tax_id = fields.Many2one('account.tax', string='Parent Sales Tax', domain="['&', ('company_id', '=', company_id), ('type_tax_use', '=', 'sale')]")
    target_company = fields.Many2one('res.company', string='Child Company', related='map_id.child_company_id')
    target_sales_tax = fields.Many2one('account.tax', string='Child Sales Tax', domain="['&', ('company_id', '=', target_company), ('type_tax_use', '=', 'sale')]")
    map_id = fields.Many2one('account.account.map', delegate=True, required=True)

class AccountTaxMapPurchase(models.Model):
    _name = 'account.tax.map.purchase.line'
    _description = 'Account Tax Map Purchase Line'

    company_id = fields.Many2one('res.company', string='Parent Company', related='map_id.company_id')
    purchase_tax_id = fields.Many2one('account.tax', string='Parent Purchase Tax', domain="['&', ('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]")
    target_company = fields.Many2one('res.company', string='Child Company', related='map_id.child_company_id')
    target_purchase_tax = fields.Many2one('account.tax', string='Child Purchase Tax', domain="['&', ('company_id', '=', target_company), ('type_tax_use', '=', 'purchase')]")
    map_id = fields.Many2one('account.account.map', delegate=True, required=True)
