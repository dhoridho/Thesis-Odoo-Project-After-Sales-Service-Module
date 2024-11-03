odoo.define('equip3_hr_training.training_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var training_flow = AbstractAction.extend({
            contentTemplate: "training_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var reporting = self.$('.accordion-reporting')
                var approval = self.$('.menu-button-approval')
                var approval1 = self.$('.menu-button-approval1')
                var approval2 = self.$('.menu-button-approval2')
                var approval3 = self.$('.menu-button-approval3')
                var training_conduct = self.$('.menu-button-my-training-request')
                var training_conduct_cancel = self.$('.menu-button-training-conduct-cancellation')
            

                this.getSession().user_has_group('equip3_hr_training.group_hr_training_supervisor').then(function(has_group) {
                    if(!has_group) {
                        
                        approval.prop('disabled', true)
                        approval2.prop('disabled', true)
                        approval3.prop('disabled', true)
                        approval1.prop('disabled', true)
                       
                        
                    } 
                });

                this.getSession().user_has_group('equip3_hr_training.group_hr_training_manager').then(function(has_group) {
                    if(!has_group) {
                        master_data.remove();
                        reporting.remove();
                        training_conduct.prop('disabled', true)
                        training_conduct_cancel.prop('disabled', true)
                        
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
    
        core.action_registry.add('training_flow_tag', training_flow);
        return training_flow;
    });