from odoo import fields, models, api
import time
from odoo.exceptions import ValidationError, Warning
import datetime
import logging
_logger = logging.getLogger(__name__)


class folio_invoice_transfer_wizard(models.TransientModel):
    _name = 'folio.invoice.transfer.wizard'
    _description = 'Folio invoice transfer Wizard'

    folio_id = fields.Many2one(
        'hotel.folio', 'Folio Ref', default=lambda self: self._get_default_rec())
    trans_folio_id = fields.Many2one(
        'hotel.folio', 'Transfer Folio Ref', domain="[('state', 'not in', ['check_out','done','cancel'])]",)

    def _get_default_rec(self):
        # print(self._context,'ffffffffffffffffffffffffffffffffffff')
        res = {}
        if 'by_dashbord' in self._context and self._context.get('by_dashbord'):
            hotel_folio_id = self.env['hotel.folio'].search(
                [('reservation_id', '=', self._context['active_id'])])
            if hotel_folio_id:
                res = hotel_folio_id.id
                return res
        if self._context is None:
            self._context = {}
        if 'active_id' in self._context:
            # print(self._context, '=================context=======')
            res = self._context['active_id']
            # print(res, "res=====================")
        return res

    def transfer_process(self):
        for obj in self.browse(self._ids):
            if obj.trans_folio_id:
                if obj.trans_folio_id.partner_id.id == obj.folio_id.partner_id.id:
                    raise ValidationError(
                        "Error !, Invoice can't be transfer as both folio partner is same !")
            folio = self.env['hotel.folio'].browse(obj.folio_id.id)
            so = self.env['sale.order'].browse(folio.order_id.id)
            for record in so.order_line:
                print("\n\n\nSale order Line==>>>", record.product_id,
                      "\n\n\nLine name", record.name)
            data = so._create_invoices()
            for acc_id in data:
                acc_obj = self.env["account.move"].browse(acc_id)
                obj.folio_id.write({'state': 'progress'})
                if obj.trans_folio_id:
                    print(obj.trans_folio_id.partner_id,
                          "obj.trans_folio_id.partner_id.id")
                    print(obj.folio_id.partner_id, "obj.folio_id.partner_id")
                    if obj.trans_folio_id.partner_id.id != obj.folio_id.partner_id.id:
                        acc_obj.write(
                            {'partner_id': obj.trans_folio_id.partner_id.id})

                    self._cr.execute('insert into sale_transfer_account_invoice_rel (sale_id,invoice_id) values (%s,%s)', (
                        obj.trans_folio_id.order_id.id, data[0]))

        return {'type': 'ir.actions.act_window_close'}


class FolioSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _description = 'Preparing Sale order Line'

    def _prepare_invoice_line(self, sequence):
        res = super(FolioSaleOrderLine, self)._prepare_invoice_line()
        hotel_folio_line_id = self._format_desc()

        checkin_date = hotel_folio_line_id.checkin_date
        print("TYPE==>>", type(checkin_date))
        if checkin_date:
            checkin_date = datetime.datetime.strftime(
                checkin_date, "%m/%d/%Y, %H:%M:%S")

            checkout_date = hotel_folio_line_id.checkout_date
            if checkout_date:
                checkout_date = datetime.datetime.strftime(
                    checkout_date, "%m/%d/%Y, %H:%M:%S")
            res.update({'name': res.get('name') + " : " + checkin_date +
                        " : "+checkout_date})
        return res

    def _format_desc(self):
        hotel_folio_line = self.env['hotel_folio.line'].search(
            [('order_line_id', '=', self.id)])
        return hotel_folio_line
