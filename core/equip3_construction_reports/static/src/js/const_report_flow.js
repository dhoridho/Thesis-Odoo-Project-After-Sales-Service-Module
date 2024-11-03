odoo.define('equip3_construction_reports.const_report_flow', function (require){
    "use strict";
    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var session = require('web.session');

    var action = AbstractAction.extend({
        hasControlPanel: !1,
        events: {
            "click button.btn-flow": "_onOpen",
            "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
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

    core.action_registry.add('tag_project_flow', action.extend({
        contentTemplate: "t_project_flow",
        start: function() {
            var self = this;
            var master_data = self.$('.accordion-master-data')
            var reporting = self.$('.accordion-reporting')
            var material_usage = self.$('.menu-button-material-usage')
            var customer = self.$('.menu-button-customer')

            this.getSession().user_has_group('equip3_construction_accessright_setting.group_construction_engineer').then(function(has_group) {
                if(!has_group) {
                    master_data.remove()
                    material_usage.prop('disabled', true)
     
                } 
            });

            this.getSession().user_has_group('abs_construction_management.group_construction_manager').then(function(has_group) {
                if(!has_group) {
                    reporting.remove()
                    customer.remove()
                } 
            });



            
            return this._super.apply(this, arguments);
        },
    }));

    core.action_registry.add('tag_project_budget_flow', action.extend({
        contentTemplate: "t_project_budget_flow",
        start: function() {
            var self = this;
            var master_data = self.$('.accordion-master-data')
            var reporting = self.$('.accordion-reporting')
            var material_usage = self.$('.menu-button-material-usage')
            var cost_sheet = self.$('.menu-button-cost-sheet')
            var budget = self.$('.menu-button-budget-transfer')
            var project_budget = self.$('.menu-button-project-budget')
            var project_budget_change = self.$('.menu-button-budget-change')
            var project_budget_change_2 = self.$('.menu-button-budget-change-2')
            var transfer_project = self.$('.menu-button-budget-tranfer-project')

            this.getSession().user_has_group('equip3_construction_accessright_setting.group_construction_engineer').then(function(has_group) {
                if(!has_group) {
                    master_data.remove()
                    cost_sheet.prop('disabled', true)
                    budget.prop('disabled', true)
                    project_budget.prop('disabled', true)
                    project_budget_change.prop('disabled', true)
                    project_budget_change_2.prop('disabled', true)
                    transfer_project.prop('disabled', true)
     
                } 
            });

            this.getSession().user_has_group('abs_construction_management.group_construction_manager').then(function(has_group) {
                if(!has_group) {
                    reporting.remove()
                } 
            });



            
            return this._super.apply(this, arguments);
        },
        
    }));

    core.action_registry.add('tag_material_purchase_flow', action.extend({
        contentTemplate: "t_material_purchase_flow"
    }));

    core.action_registry.add('tag_subcontracting_flow', action.extend({
        contentTemplate: "t_subcontracting_flow"
    }));

    core.action_registry.add('tag_customer_progressive_claim', action.extend({
        contentTemplate: "t_customer_progressive_claim"
    }));

    core.action_registry.add('tag_vendor_progressive_claim_flow', action.extend({
        contentTemplate: "t_vendor_progressive_claim_flow"
    }));

    core.action_registry.add('construction_sale_configuration_flow_tag', action.extend({
        contentTemplate: "construction_sale_flow_configuration_action",
        start: function() {
            var self = this;
            var reporting = self.$('.accordion-reporting')
            var customer = self.$('.menu-button-customer')
            var product = self.$('.menu-button-product-template')
            var uom = self.$('.menu-button-uom')
            var tax = self.$('.menu-button-tax')
            var project = self.$('.menu-button-project-sales')
            var sales = self.$('.menu-button-cost-sheet-sales')
            var claim_sales = self.$('.menu-button-progressive-claim-sales')

            // this.getSession().user_has_group('equip3_construction_accessright_setting.group_construction_engineer').then(function(has_group) {
            //     if(!has_group) {
            //         master_data.remove()
            //         material_usage.prop('disabled', true)
     
            //     } 
            // });

            this.getSession().user_has_group('sales_team.group_sale_manager').then(function(has_group) {
                if(!has_group) {
                    reporting.remove()
                    customer.remove()
                    product.remove()
                    uom.remove()
                    tax.remove()
                    project.prop('disabled', true)
                    sales.prop('disabled', true)
                    claim_sales.prop('disabled', true)
                } 
            });



            
            return this._super.apply(this, arguments);
        },
    }));

    return action;
});
//odoo.define('equip3_construction_reports.const_report_flow', function (require) {
//    "use strict";
//
//    var core = require('web.core')
//    var AbstractAction = require('web.AbstractAction');
//
//    const accordionFunction = () => {
//        $(document).ready(function () {
//            $('.accordion-action').click(function (e) {
//                let targetAccordion = document.querySelector(`#${e.currentTarget.dataset.target}`)
//                if (targetAccordion.style.maxHeight) {
//                    targetAccordion.style.maxHeight = null;
//                    e.currentTarget.classList.remove('show');
//                } else {
//                    targetAccordion.style.maxHeight = targetAccordion.scrollHeight + 'px';
//                    e.currentTarget.classList.add('show');
//                }
//            })
//        })
//    }
//
//    const defaultProps = {
//        hasControlPanel: !1,
//        start: function() { accordionFunction(); }
//    }
//
//
//    var action = {
//        actionConstructionSalesFlow: {
//            tag: "tag_construction_sales_flow",
//            abstractAction: AbstractAction.extend({
//                ...defaultProps,
//                contentTemplate: "t_construction_sales_flow",
//            })
//        },
//        actionCustomerProgressiveClaim: {
//            tag: "tag_customer_progressive_claim",
//            abstractAction: AbstractAction.extend({
//                ...defaultProps,
//                contentTemplate: "t_customer_progressive_claim",
//            })
//        },
//        actionMaterialPurchaseFlow: {
//            tag: "tag_material_purchase_flow",
//            abstractAction: AbstractAction.extend({
//                ...defaultProps,
//                contentTemplate: "t_material_purchase_flow"
//            })
//        },
//        actionProjectBudgetFlow: {
//            tag: 'tag_project_budget_flow',
//            abstractAction: AbstractAction.extend({
//                ...defaultProps,
//                contentTemplate: "t_project_budget_flow"
//            })
//        },
//        actionProjectFlow: {
//            tag: 'tag_project_flow',
//            abstractAction: AbstractAction.extend({
//                ...defaultProps,
//                contentTemplate: "t_project_flow"
//            })
//        },
//        actionSubcontractingFlow: {
//            tag: 'tag_subcontracting_flow',
//            abstractAction: AbstractAction.extend({
//                ...defaultProps,
//                contentTemplate: "t_subcontracting_flow"
//            })
//        },
//        actionVendorProgressiveClaimFlow: {
//            tag: 'tag_vendor_progressive_claim_flow',
//            abstractAction: AbstractAction.extend({
//                ...defaultProps,
//                contentTemplate: "t_vendor_progressive_claim_flow"
//            })
//        }
//    }
//
//    for (const [index, _] of Object.entries(action)) {
//        core.action_registry.add(action[index].tag, action[index].abstractAction)
//    }
//
//    return action
//})
//odoo.define('equip3_construction_reports.const_report_flow', function (require){
//"use strict";
//    var core = require('web.core');
//    var AbstractAction = require('web.AbstractAction');
//    var session = require('web.session');
//
//    var action = AbstractAction.extend({
//        contentTemplate: "t_project_flow",
//        hasControlPanel: !1,
//        events: {
//            "click button.btn-flow": "_onOpen",
//            "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
//        },
//        _onClickAccordion: function(ev){
//            let $target = $(ev.currentTarget);
//            let _id = $target.attr('data-target');
//            let $accordion = $(`#${_id}`);
//            if($accordion.hasClass('show')){
//                $accordion.removeClass('show').addClass('collapse');
//                $accordion.parent().find('.accordion-button').addClass('collapse');
//            }else{
//                $accordion.removeClass('collapse').addClass('show');
//                $accordion.parent().find('.accordion-button').removeClass('collapse');
//            }
//        },
//        _onOpen: function(ev){
//            let self = this;
//            let $target = $(ev.currentTarget);
//            self.do_action( $target.attr('name'));
//        }
//    });
//
//    core.action_registry.add('tag_project_flow', action);
//    return action;
//});