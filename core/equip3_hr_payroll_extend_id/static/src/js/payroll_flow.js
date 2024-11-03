odoo.define('equip3_hr_payroll_extend_id.payroll_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var payroll_flow = AbstractAction.extend({
            contentTemplate: "payroll_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var employee_payslip = self.$('.employee-payslip')
                var payslip_batches = self.$('.payslip-batches')
                var payslip_report = self.$('.menu-button-payslip-report')
                var payroll_report = self.$('.menu-button-payroll-report')
                var bpjs_report = self.$('.menu-button-bpjs-kesehatan-report')
                var ketenagakerjaan_report = self.$('.menu-button-bpjs-ketenagakerjaan-report')
                var mayapada = self.$('.menu-button-mayapada-bank-transfer')
                var danamon = self.$('.menu-button-danamon-bank-transfer')
                var bca = self.$('.menu-button-bca-bank-transfer')
                var generate_spt = self.$('.menu-button-generate-spt')
                var spt_report = self.$('.menu-button-spt-report')
                var aja = self.$('.menu-button-1721-A1A2')

                this.getSession().user_has_group('hr_payroll_community.group_hr_payroll_community_manager').then(function(has_group) {
                    if(!has_group) {
                        employee_payslip.prop('disabled', true)
                        payslip_batches.prop('disabled', true)
                        master_data.remove();
                        payslip_report.remove();
                        payroll_report.remove();
                        bpjs_report.remove();
                        ketenagakerjaan_report.remove();
                        mayapada.remove();
                        danamon.remove();
                        bca.remove();
                        generate_spt.remove();
                        spt_report.remove();
                        aja.remove();
                     
                        
                    } 
                });



               

                
                return this._super.apply(this, arguments);
            },
            _onClickAccordion: function(ev){
                let $target = $(ev.currentTarget);
                let _id = $target.attr('data-target');
                let $accordion = $(`#${_id}`);
                if($accordion.hasClass('show')){
                    $accordion.removeClass('show').addClass('collapse');
                    $accordion.parent().find('.accordion-button').addClass('collapse');
                }else{
                    $accordion.removeClass('collapse').addClass('show');
                    $accordion.parent().find('.accordion-button').removeClass('collapse');
                }
            },
            _onOpen: function(ev){ 
                let self = this;
                let $target = $(ev.currentTarget);
                self.do_action( $target.attr('name'));
            }
        });
    
        core.action_registry.add('payroll_flow_tag', payroll_flow);
        return payroll_flow;
    });