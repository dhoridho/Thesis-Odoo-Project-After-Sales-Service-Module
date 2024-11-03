from odoo import api, fields, models, _


class ResBranch(models.Model):
    _inherit = 'res.branch'

    active_company_sequence = fields.Integer(string='Sequence', help="Gives the sequence order when displaying a list")

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(ResBranch, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        self.active_company_seq_sql()
        return res

    def active_company_seq_sql(self):
        query_statement = """UPDATE res_branch set active_company_sequence = '1' WHERE company_id = %s """
        self.sudo().env.cr.execute(query_statement, [self.env.company.id])
        query_statement_2 = """UPDATE res_branch set active_company_sequence = '2' WHERE company_id != %s """
        self.sudo().env.cr.execute(query_statement_2, [self.env.company.id])
