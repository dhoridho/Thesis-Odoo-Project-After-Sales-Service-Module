

from odoo import models, api, fields, _


class IRActionsReport(models.Model):
    _inherit = 'ir.actions.report'


    ssc_create_template_id = fields.Many2one('ssc.create.template','SSC Create Template')


class IRUIView(models.Model):
    _inherit = 'ir.ui.view'


    ssc_create_template_id = fields.Many2one('ssc.create.template','SSC Create Template')


    def unlink(self):
        view_obj = self.env['ir.ui.view']
        records = view_obj
        for data in self:
            if data.ssc_create_template_id and not self._context.get('force_delete'):
                continue
            records |= data
        return super(IRUIView, records).unlink()
