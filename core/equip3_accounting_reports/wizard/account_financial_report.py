from odoo import api, models, fields


class AccountFinancialReport(models.Model):
    _inherit = "account.financial.report"

    code = fields.Char('Code')
    domain = fields.Char(default=None)
    formulas = fields.Char()

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "A report line with the same code already exists."),
    ]

    @api.constrains('code')
    def _code_constrains(self):
        for rec in self:
            if rec.code and rec.code.strip().lower() in __builtins__.keys():
                raise ValidationError('The code "%s" is invalid on line with name "%s"' % (rec.code, rec.name))

    @api.onchange('type')
    def _clear_field_account(self):
        if not self.type == 'accounts':
            self.account_ids = False
        if not self.type == 'account_type_ids':
            self.account_type_ids = False
        if not self.type in ['accounts','account_type', 'account_report']:
            self.domain = False

    def _split_formulas(self):
        result = {}
        if self.formulas:
            for f in self.formulas.split(';'):
                [column, formula] = f.split('=')
                formula = formula.strip()
                column = column.strip()
                result.update({column: formula})
        return result



    # def action_get_account_move(self):
    #     action = self.env.ref('account.action_account_moves_all_a').read()[0]
    #     action['domain'] = self.domain and eval(self.domain) or [('id','=',False)] # to display nothing when there is no domain
    #     return action

    # @api.model
    # def create(self, vals):
    #     if vals.get('type') or vals.get('account_ids') or vals.get('account_type_ids'):
    #         domain = self.prepare_domain(vals)
    #         vals.update({'domain': domain, 'groupby': 'account_id'})
    #     return super(AccountFinancialReportLine, self).create(vals)

    # def write(self, vals):
    #     if vals.get('type') or vals.get('account_ids') or vals.get('account_type_ids'):
    #         domain = self.prepare_domain(vals)
    #         vals.update({'domain': domain, 'groupby': 'account_id'})
    #     return super(AccountFinancialReportLine, self).write(vals)

    # def prepare_domain(self, vals):
    #     domain = []
    #     if (vals.get('type') == 'account') or vals.get('account_ids'):
    #         account_ids = []
    #         if self.ids:
    #             account_ids = self[0].account_ids.ids
    #         if vals.get('account_ids'):
    #             account_ids = vals.get('account_ids')[0][2]
    #         if account_ids:
    #             domain = [('account_id', 'in', account_ids)]
    #     elif (vals.get('type') == 'account_type') or vals.get('account_type_ids'):
    #         account_type_ids = []
    #         if self.ids:
    #             account_type_ids = self[0].account_type_ids.ids
    #         if vals.get('account_type_ids'):
    #             account_type_ids = vals.get('account_type_ids')[0][2]
    #         if account_type_ids:
    #             domain = [('account_id.user_type_id', 'in', account_type_ids)]
    #     return str(domain)