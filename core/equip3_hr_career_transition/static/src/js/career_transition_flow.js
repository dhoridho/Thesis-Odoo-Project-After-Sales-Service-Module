odoo.define('equip3_hr_career_transition.career_transition_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');

        var career_transition_flow = AbstractAction.extend({
            contentTemplate: "career_transition_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var reporting = self.$('.accordion-reporting')
                var transition_request_to_approve = self.$('.menu-button-transition-request-to-approve')
                var contract = self.$('.menu-button-contract')

                this.getSession().user_has_group('equip3_hr_career_transition.career_transition_team_approver').then(function(has_group) {
                    if(!has_group) {
                        master_data.remove();
                        reporting.remove();
                        transition_request_to_approve.prop('disabled', true)
                        contract.prop('disabled', true)
                        
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

        core.action_registry.add('career_transition_flow_tag', career_transition_flow);
        return career_transition_flow;
    });