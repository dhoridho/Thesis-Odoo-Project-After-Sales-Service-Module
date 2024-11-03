odoo.define('equip3_construction_operation.tree_view_button', function (require){
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var TreeButton = ListController.extend({
       buttons_template: 'equip3_construction_operation.buttons',
       events: _.extend({}, ListController.prototype.events, {
           'click .open_wizard_action': '_OpenWizard',
       }),
       _OpenWizard: function () {
            var self = this;
            var context = self.model.get(self.handle).getContext();

            this.do_action({
               type: 'ir.actions.act_window',
               res_model: 'progress.history.wiz',
               name :'Create Progress History',
               view_mode: 'form',
               view_type: 'form',
               views: [[false, 'form']],
               target: 'new',
               res_id: false,
               context: {
                    'default_is_create_from_list_view': true,
                    'default_department_type': context.default_department_type,
                },
           });
       }
    });
    var SaleOrderListView = ListView.extend({
       config: _.extend({}, ListView.prototype.config, {
           Controller: TreeButton,
       }),
    });
    viewRegistry.add('button_in_tree', SaleOrderListView);
    
    });