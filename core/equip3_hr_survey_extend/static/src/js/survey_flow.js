odoo.define('equip3_hr_survey_extend.survey_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var survey_flow = AbstractAction.extend({
            contentTemplate: "survey_configuration_action",
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
                let $button_name = $target.attr('name')
                if ($button_name != 'action_none'){
                    self.do_action( $button_name);
                }
            }
        });
    
        core.action_registry.add('survey_flow_tag', survey_flow);
        return survey_flow;
    });