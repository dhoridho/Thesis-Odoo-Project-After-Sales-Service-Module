from odoo import models, fields, api


class ShQcPoint(models.Model):
    _inherit = 'sh.qc.point'
    _rec_name = 'name'

    @api.model
    def _get_default_operation(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        return self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', '=', company_id),
        ], limit=1).id

    operation = fields.Many2one(default=_get_default_operation, string='Operation')
    is_mandatory = fields.Boolean(string='Mandatory?')
    number_of_test = fields.Integer(string='Max. test', required=True, default=1, help='Maximum number of tests allowed.')

    description = fields.Char(string='Description')
    need_alert = fields.Boolean('Need Alert?')
    auto_create_alert = fields.Boolean('Auto Create Alert?', default=True)

    branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        tracking=True)
    create_uid = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user)
    move_id = fields.Many2one('stock.move', string='Move')

    @api.onchange('need_alert')
    def onchange_need_alert(self):
        if not self.need_alert:
            self.auto_create_alert = False
