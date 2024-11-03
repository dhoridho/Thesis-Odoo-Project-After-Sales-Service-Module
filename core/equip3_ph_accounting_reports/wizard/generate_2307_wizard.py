from odoo import models, _
from odoo.exceptions import UserError


class Generate2307WizardInherit(models.TransientModel):
    _inherit = "l10n_ph_2307.wizard"

    def action_generate(self):
        moves = self.moves_to_export
        for move in moves:
            invoice_lines = move.invoice_line_ids.filtered(
                lambda l: not l.display_type
                and l.tax_ids.filtered(lambda tax: tax.l10n_ph_atc).ids
            )
            if not invoice_lines:
                raise UserError(_("Please define Philippines ATC first!"))

        return super(Generate2307WizardInherit, self).action_generate()
