from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, Warning


class PurchaseAction(models.Model):
    _name = "purchase.action"
    _description = "Purchase Action"
    _order = "sequence"

    name = fields.Char("Name", required=True)
    purchase_action_number = fields.Char('Purchase Action Number', required=True)
    type_of_mr = fields.Selection(
        [('assets', 'Assets'), ('material', 'Material'), ('labour', 'Labour'), ('overhead', 'Overhead'),
         ('equipment', 'Equipment'), ('vehicle', 'Vehicle')], string="Type Of MR")
    analytic_group = fields.Many2one('account.analytic.tag', 'Analytic Group')
    sequence = fields.Integer('Sequence', index=True)

    @api.constrains('purchase_action_number')
    def _check_existing_record(self):
        for record in self:
            purchase_action_number_id = self.env['purchase.action'].search(
                [('purchase_action_number', '=', record.purchase_action_number)])
            if len(purchase_action_number_id) > 1:
                raise ValidationError(
                    f'The purchase action number in this purchase action is the same as another purchase action. Please change the purchase action number')
