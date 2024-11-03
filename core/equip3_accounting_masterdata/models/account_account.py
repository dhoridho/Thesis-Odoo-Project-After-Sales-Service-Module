from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SetupBarBankConfigWizard(models.TransientModel):    
    _inherit = 'account.setup.bank.manual.config'

    
    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

    def validate(self):
        res = super(SetupBarBankConfigWizard, self).validate()
        for rec in self:
            vals = {
                'acc_number': rec.acc_number,
                'bank_id': rec.bank_id.id,
                'bank_bic': rec.bank_bic,
                'company_id': rec.company_id.id,
                'branch_id': rec.branch_id.id,            
            }
            self.env['bank.account.account'].create(vals)
        return res

class AccountReconcile(models.Model):
    _inherit = "account.reconcile.model"

    
    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountAccount(models.Model):
    _inherit = "account.account"

    
    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountTax(models.Model):
    _inherit = "account.tax" 

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)


    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        for rec in self:
            if rec.env.company:
                rec.company_id = rec.env.company

        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountType(models.Model):
    _inherit = "account.account.type"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountTaxReport(models.Model):
    _inherit = "account.tax.report"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountBudget(models.Model):
    _inherit = "account.budget.post"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountAssetCategory(models.Model):
    _inherit = "account.asset.category"

    
    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', domain=_domain_branch, readonly=False)
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', domain=_domain_branch, readonly=False)

    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountAnalyticGroup(models.Model):
    _inherit = "account.analytic.group"

    
    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', domain=_domain_branch, readonly=False)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        for rec in self:
            if rec.env.company:
                rec.company_id = rec.env.company
        
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountAnalyticDefault(models.Model):
    _inherit = "account.analytic.default"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', domain=_domain_branch, readonly=False)


    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        for rec in self:
            if rec.env.company:
                rec.company_id = rec.env.company
        
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class FiscalYear(models.Model):
    _inherit = "sh.fiscal.year"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class FiscalYearPeriod(models.Model):
    _inherit = "sh.account.period"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    # branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    branch_id = fields.Many2one('res.branch', check_company=True, related='fiscal_year_id.branch_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', related='fiscal_year_id.company_id', store=True, readonly=True)
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    
    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)

    @api.onchange('branch_id')
    @api.depends('branch_id')
    def _set_company(self):
        for rec in self:
            if rec.env.company:
                rec.company_id = rec.env.company

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")
                
class ResBank(models.Model):
    _inherit = "res.bank"

    code = fields.Char('Bank Code', tracking=True)
    bank_provider = fields.Selection([
        ('bank_other', 'Other'),
        ('bank_bca', 'BCA')
        ], "Bank Provider", default='bank_other')

    def _valid_field_parameter(self, field, name):
        return name == "tracking" or super()._valid_field_parameter(field, name)

class productTemplate(models.Model):
    _inherit = "product.template"

    tax_code = fields.Selection([
        ('2410101', '24-101-01'), ('2410201', '24-102-01'),
        ('2410301', '24-103-01'), ('2410001', '24-100-01'),
        ('2410002', '24-100-02'), ('2410401', '24-104-01'),
        ('2410402', '24-104-02'), ('2410403', '24-104-03'),
        ('2410404', '24-104-04'), ('2410405', '24-104-05'),
        ('2410406', '24-104-06'), ('2410407', '24-104-07'),
        ('2410408', '24-104-08'), ('2410409', '24-104-09'),
        ('2410410', '24-104-10'), ('2410411', '24-104-11'),
        ('2410412', '24-104-12'), ('2410413', '24-104-13'),
        ('2410414', '24-104-14'), ('2410415', '24-104-15'),
        ('2410416', '24-104-16'), ('2410417', '24-104-17'),
        ('2410418', '24-104-18')],
        "Kode Objek Pajak")
    doc_code = fields.Selection([
        ('1', '01'),
        ('2', '02'),
        ('3', '03'),
        ('4', '04'),
        ('5', '05'),
        ('6', '06')],
        "Jenis Dokumen")