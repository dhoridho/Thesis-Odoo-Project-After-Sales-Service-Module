odoo.define('one2many_selection.form_widgets', function (require) {
	"use strict";

	var core = require('web.core');
	var utils = require('web.utils');
	var _t = core._t;
	var rpc = require('web.rpc');
	var fieldRegistry = require('web.field_registry');
	var ListRenderer = require('web.ListRenderer');
	var FieldOne2Many = require('web.relational_fields').FieldOne2Many;

	ListRenderer.include({
		_updateSelection: function () {
	        this.selection = [];
	        var self = this;
	        var $inputs = this.$('tbody .o_list_record_selector input:visible:not(:disabled)');
	        var allChecked = $inputs.length > 0;
	        $inputs.each(function (index, input) {
	            if (input.checked) {
	                self.selection.push($(input).closest('tr').data('id'));
	            } else {
	                allChecked = false;
	            }
	        });
	        if (this.selection.length > 0) {
	        	$('.button_delete_lines').show()
	        } else {
	        	$('.button_delete_lines').hide()
	        }
	        this.$('thead .o_list_record_selector input').prop('checked', allChecked);
	        this.trigger_up('selection_changed', { selection: this.selection });
	        this._updateFooter();
	    },
	})

	var One2ManySelectable = FieldOne2Many.extend({
		template: 'One2ManySelectable',
		events: {
			"click .button_delete_lines": "action_delete_selected_lines",
		},

		action_delete_selected_lines: function() {		
			var self = this;
			var selected_ids = self.get_selected_ids_one2many();
			var model = self.value.model 
			
			if (selected_ids.length === 0) {
				this.do_warn(_t("You must choose at least one record."));
				return false;
			}
			rpc.query({
                'model': model,
                'method': 'unlink',
                'args': [selected_ids],
            }).then(function(result){
                self.trigger_up('reload');
            });
		},

		_getRenderer: function () {
            if (this.view.arch.tag === 'kanban') {
                return One2ManyKanbanRenderer;
            }
            if (this.view.arch.tag === 'tree') {
                return ListRenderer.extend({
                    init: function (parent, state, params) {
                        this._super.apply(this, arguments);
                        this.hasSelectors = true;
                    },
                });
            }
            return this._super.apply(this, arguments);
        },

		get_selected_ids_one2many: function () {
            var self = this;
            var ids = [];
            this.$el.find('td.o_list_record_selector input:checked').closest('tr').each(function () {
            	ids.push(parseInt(self._getResId($(this).data('id'))));
            });
            return ids;
        },

        _getResId: function (recordId) {
            var record;
            utils.traverse_records(this.recordData[this.name], function (r) {
                if (r.id === recordId) {
                    record = r;
                }
            });
            return record.res_id;
        },
	});
	fieldRegistry.add('one2many_selectable', One2ManySelectable);
});