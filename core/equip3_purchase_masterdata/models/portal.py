from odoo import api, fields, models
from odoo.tools import email_split
from ast import literal_eval
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.exceptions import ValidationError

def extract_email(email):
    """ extract the email address from a user-friendly email address """
    addresses = email_split(email)
    return addresses[0] if addresses else ''



class PortalWizard(models.TransientModel):
    """
        A wizard to manage the creation/removal of portal users.
    """

    _inherit = 'portal.wizard'
    

    def action_apply(self):
        self.ensure_one()
        for line in self.user_ids:
            if line.partner_id and line.partner_id.is_vendor and line.partner_id.state != 'approved' and self._context.get('active_model') and self._context.get('active_ids'):
                raise ValidationError("Vendor "+line.partner_id.name+" cannot grant portal access, must approved first.")
        return super(PortalWizard, self).action_apply()



class PortalWizardUser(models.TransientModel):

    _inherit = 'portal.wizard.user'

    def _create_user(self):
        """ create a new user for wizard_user.partner_id
            :returns record of res.users
        """
        return self.env['res.users'].with_context(no_reset_password=True)._create_user_from_template({
            'email': extract_email(self.email),
            'login': extract_email(self.email),
            'partner_id': self.partner_id.id,
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, self.env['res.company'].search([]).ids)],
            'branch_id': self.partner_id.branch_id.id or self.env.branch.id,
            'branch_ids': [(6, 0, self.env['res.branch'].search([]).ids)]
        })
