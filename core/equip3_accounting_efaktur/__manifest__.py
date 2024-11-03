# -*- coding: utf-8 -*-
{
    'name': "E-Faktur",
    'author': "Irfan Suendi",
    'category': 'Accounting',
    'version': '1.3.39',
    'depends': ['account','web','l10n_id_efaktur','inputmask_widget', 'product', 'equip3_accounting_masterdata', 'equip3_accounting_operation', 'aos_base_account', 'equip3_general_features'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/keterangan_tambahan_data.xml',
        'data/kode_objek_pajak.xml',
        'views/templates.xml',
        'views/res_config_settings_views.xml',
        'views/efaktur_menuitem.xml',
        'views/nsfp_regitration.xml',
        'views/efaktur_views.xml',
        'views/account_views.xml',
        'views/res_partner_views.xml',
        'views/account_ebupot_views.xml',
        'views/product_template.xml',
        'views/res_company_views.xml',
        'views/res_branch_views.xml',
        'wizards/product_wizard_view.xml',
        'wizards/partner_wizard_view.xml',
        'wizards/account_tax_digunggung_view.xml',
        'wizards/nsfp_registration_wizard.xml',
        'wizards/nomor_seri_efaktur_wizard.xml',

        # 'views/buttton.xml',
    ],
      'qweb': [
        # 'static/src/xml/custom_button.xml'
     ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}
