odoo.define('equip3_sale_configuration_flow.sale_configuration_flow', function (require){
"use strict";
    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var session = require('web.session');

    var sale_configuration_flow = AbstractAction.extend({
        contentTemplate: "sale_flow_configuration_action",
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

    core.action_registry.add('sale_configuration_flow_tag', sale_configuration_flow);
    return sale_configuration_flow;
});