odoo.define('equip3_purchase_rental.rental_configuration_flow', function (require){
"use strict";
    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var session = require('web.session');

    var rental_configuration_flow = AbstractAction.extend({
        contentTemplate: "rental_flow_configuration_action",
        hasControlPanel: !1,
        events: {
            "click button.btn-flow": "_onOpen",
            "click button.btn-flow-active": "_onOpen",
            "click button.btn-flow-deactive": "_onOpen",
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

    core.action_registry.add('rental_configuration_flow_tag', rental_configuration_flow);
    return rental_configuration_flow;
});