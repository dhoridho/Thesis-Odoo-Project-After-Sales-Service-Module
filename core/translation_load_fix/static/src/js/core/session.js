
odoo.define('translation_load_fix.Session', function (require) {
    'use strict';
    console.log('sessionnnn====')

    var Session = require('web.Session');
    var core = require('web.core');
    var qweb = core.qweb;

    Session.include({
        load_qweb: function (mods) {
            var module_to_exclude = [
                                'abs_construction_management',
                'asset_mro_maintenance_management',
                'equip3_accounting_asset_budget',
                'equip3_accounting_bank_integration',
                'equip3_accounting_report_cashflow_id',
                'equip3_accounting_salepurchase_operation',
                'equip3_asset_fms_accessright_setting',
                'equip3_hr_employee_access_right_setting',
                'equip3_inventory_accessright_setting',
                'elearning_external_videos',
                'equip3_hr_contract_extend',
                'payment_xendit',
                'equip3_asset_fms_restructure_menu_flow',
                'equip3_consignment_sales',
                'equip3_crm_masterdata',
                'base_synchro',
                'bi_warranty_registration',
                'crm_phonecall',
                'equip3_accounting_bank_reconcile',
                'equip3_accounting_multicurrency_revaluation',
                'equip3_crm_report',
                'equip3_general_feature_email',
                'equip3_hr_working_schedule_calendar',
                'equip3_hr_training',
                'equip3_hr_employee_appraisals',
                'equip3_hr_employee_loan_extend',
                'sale_expense',
                'equip3_hr_expense_extend',
                'equip3_hr_travel_extend',
                'equip3_inventory_qc',
                'eq_scrap_order_report',
                'equip3_inventory_tracking',
                'equip3_inventory_scale',
                'equip3_kitchen_accessright_settings'
            ];
            mods = mods.split(',')
                .filter(item => !module_to_exclude.includes(item))
                    .join(',')

            var self = this;
            var lock = this.qweb_mutex.exec(function () {
            var cacheId = self.cache_hashes && self.cache_hashes.qweb;
            var route  = '/web/webclient/qweb/' + (cacheId ? cacheId : Date.now()) + '?mods=' + mods;
            return $.get(route).then(function (doc) {
                if (!doc) { return; }
                const owlTemplates = [];
                for (let child of doc.querySelectorAll("templates > [owl]")) {
                    child.removeAttribute('owl');
                    owlTemplates.push(child.outerHTML);
                    child.remove();
                }
                qweb.add_template(doc);
                self.owlTemplates = `<templates> ${owlTemplates.join('\n')} </templates>`;
            });
        });
        return lock;
        },
    });
    });
