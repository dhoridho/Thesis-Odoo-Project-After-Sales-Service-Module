# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Interest on Overdue Invoice in Odoo',
    'version': '14.0.0.3',
    'summary': 'App for Calculate interest on Overdue Invoice interest on pending invoice Penalty on due invoices financial charges on overdue invoices Late payment interest in invoice Late payment fee on invoice Penalty Overdue Invoices interest on customer Invoices',
    'category': 'Accounting',
    'price': 69.00,
    'currency': "EUR",
    'description': """
    
	interest on pending invoice
	interest on delayed payment 
	Late Fee & Interest Charges
	Interest Calculation on Customer Account
	Interest Calculation on invoice
	Interest Calculation on pending invoice
	Interest Calculation on late payment
    invoice interest calculation
    invoice interest for due invoice
    Penalty on due invoices
    Penalty invoices 
    financial charges on overdue invoices
    componsation on invoice
	Penalty on overdue invoices
	claim interest and debt recovery costs
	interest on an outstanding invoice
	Late payment interest calculation scheduling
	Calculate Interest on Bill of Exchange in Advance
    This Odoo apps is helps to calculate daily,monthly or yearly Interest Penalty on Overdue Invoices based on payment term configuration.Payment term is something that accountant emphasis on most , delay payment can cost as late payment fee , so when payment get over due , interest needs to be charges in order to get payment sooner, this odoo module does perfect job this payment over due method , automatically calculate interest on overdue payments this odoo apps apply financial charges on overdue invoices. When your invoice is validated and overdue than everyday/monthly it automatically updates the interest/penalty of invoice based on interest rate assinged on payment terms configuration.calculation of invoice will be done based on invoice due date. 
	Calculate Interest on overdue Bill of Exchange in Advance
	-Calculate Interest for Overdue Invoice, Calculate interest from Payment terms, Interest on payment terms, Interest on invoice, Overdue payment interest. Overdue charges on invoice. Overdue rate calculate. Penalty on overdue invoice, Penatly on overdue payment. Add interest on invoice. Add Interest on Ovedue payment. Late Payment charges. Apply Penalty charges for Overdue Invoice, Apply interest on ovedue invoice.
حساب الفائدة للفاتورة المتأخرة ، وحساب الفائدة من شروط الدفع ، والفائدة على شروط الدفع ، والفائدة على الفاتورة ، وفائدة الدفع المتأخر. الرسوم المتأخرة على الفاتورة. حساب معدل المتأخرة. عقوبة على فاتورة المتأخرة ، Penatly على دفع المتأخر. إضافة الفائدة على الفاتورة. إضافة الفائدة على دفع Ovedue. رسوم التأخر في السداد. تطبيق رسوم عقوبة لفاتورة المتأخرة ، تطبيق الفائدة على فاتورة ovedue.
hisab alfayidat lilfatwrat almuta'akhirat , wahisab alfayidat min shurut aldafe , walfayidat ealaa shurut aldafe , walfayidat ealaa alfatwrt , wafayidat aldafe almuta'akhri. alrusum almuta'akhirat ealaa alfaturat. hisab mueadal almuta'akhirati. euqubatan ealaa faturat almuta'akhirat , Penatly ealaa dafe almuta'akhr. 'iidafat alfayidat ealaa alfaturat. 'iidafat alfayidat ealaa dafe Ovedue. rusum alta'akhur fi alsidadi. tatbiq rusum euqubat lifaturat almuta'akhrat , tatbiq alfayidat ealaa faturat ovedue.Bereken rente voor te late factuur, Bereken rente van betalingsvoorwaarden, Rente op betalingsvoorwaarden, Rente op factuur, Achterstallige betalingsrente. Achterstallige kosten op factuur. Achterstallige tariefberekening. Straf op achterstallige factuur, Penatly op achterstallige betaling. Rente toevoegen op factuur. Interesse toevoegen aan Ovedue-betaling. Kosten voor laattijdige betaling. Strafvergoedingen toepassen op achterstallige factuur, rente toepassen op oveduefactuur.
Calcular juros para fatura vencida, calcular juros de condições de pagamento, juros sobre as condições de pagamento, juros sobre a fatura, juros de pagamento em atraso. Despesas vencidas na fatura. A taxa vencida é calculada. Pena na fatura vencida, Penatly no pagamento atrasado. Adicione juros na fatura. Adicione juros sobre pagamento Ovedue. Atrasos de pagamento. Aplica multas por fatura vencida, aplica juros sobre a fatura ovedue.
Berechnen Sie Zinsen für überfällige Rechnungen, Berechnen Sie Zinsen aus Zahlungsbedingungen, Zinsen auf Zahlungsbedingungen, Zinsen auf Rechnung, Überfällige Zahlungszinsen. Überfällige Gebühren auf der Rechnung. Überfällige Rate berechnen. Strafe für überfällige Rechnung, Penatly für überfällige Zahlung. Zinsen auf Rechnung hinzufügen Verzinsung auf Ovedue-Zahlung hinzufügen Späte Zahlung Gebühren. Überweisungsgebühren für überfällige Rechnung anwenden, Zinsen für Rechnung auf Rechnung anwenden.
Calculer l'intérêt pour la facture en souffrance, Calculer l'intérêt des modalités de paiement, Intérêts sur les modalités de paiement, Intérêts sur la facture, Intérêt de paiement en retard. Les frais en retard sur la facture. Calcul du taux en retard. Pénalité sur la facture en retard, Penatly sur le paiement en retard. Ajouter un intérêt sur la facture. Ajouter un intérêt sur le paiement Ovedue. Frais de retard de paiement. Appliquer des frais de pénalité pour facture en retard, appliquer des intérêts sur la facture ovedue.
Calcule el interés de la factura vencida, calcule los intereses de las condiciones de pago, los intereses sobre las condiciones de pago, los intereses sobre la factura, los intereses vencidos de los pagos. Cargos atrasados ​​en la factura. Tasa vencida calcule. La multa en la factura vencida, Penatly en el pago atrasado. Agregue interés en la factura. Agregue interés en el pago de Ovedue. Cargos por pagos atrasados. Aplica cargos por multa por factura vencida, aplica intereses en la factura ovedue.

    """,
    "category": 'Accounting',
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    'live_test_url':'https://youtu.be/DhDf16VTlck',
    'depends': ['base','sale_management','account'],
    'data': [
        'security/invoice_security.xml',
        'data/invoice_report.xml',
        'views/account_payment_term_view.xml',
        'views/cron.xml'
        
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    "images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
