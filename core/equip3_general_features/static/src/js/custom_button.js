odoo.define('equip3_general_features.custom_button', function (require){
    "use strict";

    var core = require('web.core');
    var ListView = require('web.ListView');
    var ListController = require('web.ListController');
    var rpc = require('web.rpc');

    var IncludeListView = {
        renderButtons: function() {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                    var syncronize_template = this.$buttons.find('button.o_syncronize_template');
                    syncronize_template.on('click', this.proxy('syncronize_template'))

                    var create_template = this.$buttons.find('button.o_create_template');
                    create_template.on('click', this.proxy('create_template'))
                }


                        },

        syncronize_template: function() {

            var def = rpc.query({
                model: 'qiscus.wa.template',
                method: 'ir_cron_syncronize_template_button',
            }).then(function(data) {
                console.log(data);
                location.reload();
                return false;
            

                
            });},

            create_template: function() {
                var self = this;
                var action = {
                    type: "ir.actions.act_window",
                    name: "Create Content",
                    res_model: "create.template.qiscuss",
                    views: [[false, 'form']],
                    target: 'new',
                    view_mode: 'form'
                };
                return this.do_action(action);
            
            }


            
    };
    ListController.include(IncludeListView);
});