odoo.define('equip3_manuf_reports.KanbanColumn', function (require) {
    
    var KanbanColumn = require('web.KanbanColumn');
    var core = require('web.core');
    var ListController = require('web.ListController');
    var KanbanController = require('web.KanbanController');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var _t = core._t;

    KanbanController.include({
        init: function () {
            this._super.apply(this, arguments);
        },
        renderButtons: function () {
            this._super.apply(this, arguments);
                if (this.$buttons) {
                    this.$buttons.find('.o_kanban_button_export_pdf').click(this.proxy('action_print_pdf'));
                }
        },
        action_print_pdf: function () {
            var self =this
            var user = session.uid;
            rpc.query({
                model: 'custom.mrp.buttons',
                method: 'print_pdf_preview',
                args: [1],
            })
        }
    });
    ListController.include({
        init: function () {
            this._super.apply(this, arguments);
        },
        renderButtons: function($node) {
        this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$buttons.find('.o_list_button_export_pdf').click(this.proxy('action_print_pdf'));
            }
        },
        
        action_print_pdf: function () {
            var self =this
            var user = session.uid;
            rpc.query({
                model: 'custom.mrp.buttons',
                method: 'print_pdf_preview',
                args: [1],
            })
        }
    });
    KanbanColumn.include({
        init: function (parent, data, options, recordOptions) {
            this._super(parent, data, options, recordOptions);
            if (this.modelName === 'mrp.production') {
                this.draggable = false;
            }
        },
    });
    return {
        KanbanColumn,
    };

})