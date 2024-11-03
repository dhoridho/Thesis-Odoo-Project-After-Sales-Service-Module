odoo.define('equip3_hr_travel_extend.travel_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var travel_flow = AbstractAction.extend({
            contentTemplate: "travel_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var reporting = self.$('.accordion-reporting')
                var btn_approval = self.$('.btn-approval')
                var btn_approval2 = self.$('.btn-approval2')
                this.getSession().user_has_group('equip3_hr_employee_access_right_setting.group_hr_travel_supervisor').then(function(has_group) {
                    if(!has_group) {
                        btn_approval.prop('disabled', true)
                        btn_approval2.prop('disabled', true)
                        master_data.remove();
                        reporting.remove();
                        
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
                let $button_name = $target.attr('name')
                if ($button_name != 'action_none'){
                    self.do_action( $button_name);
                }
            }
        });
    
        core.action_registry.add('travel_flow_tag', travel_flow);
        return travel_flow;
    });