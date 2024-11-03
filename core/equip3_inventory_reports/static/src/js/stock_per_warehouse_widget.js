odoo.define('equip3_inventory_reports.StockPerWarehouseWidget', function(require){
    "use strict";

    const Widget = require('web.Widget');

    var FieldSelection = Widget.extend({
        type: 'selection',
        template: 'StockPerWhSelection',

        events: {
            'input .o_record_input': '_onInput',
            'click .o_open_dropdown': '_onClick',
            'click .o_record_name:not(.o_not_found)': '_onSelect',
        },
    
        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.name = params.name;
            this.label = params.label;

            this.default = params.default || false;
            this.value = params.value || this.default;
            this.disabled = params.disabled || false;
            this.selections = params.selections || [];
            this.readonly =  params.readonly;
            this.default = params.default || false;

            this.savedValue = this.value;
            this.isDirty = false;

            this.onchange = params.onchange || function(){};
        },
    
        start: function(){
            this.$el = $(this.el);
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$input = self.$el.find('.o_record_input');
                self.$dropdown = self.$el.find('.o_record_dropdown');
                self._setValue(self.value);
            });
        },

        _getDisplayName: async function(value){
            let displayName = '';
            let displayNames = _.filter(await this._getRecords(''), function(record){return record.key === value;});
            if (displayNames.length){
                displayName = displayNames[0].name;
            }
            return displayName;
        },
    
        _onInput: function(ev){
            ev.stopPropagation();
            let query = $(ev.target).val().toLowerCase();
            this._searchRecord(query);
        },
    
        _onClick: function(ev){
            ev.preventDefault();
            if (this.disabled){
                return;
            }
            this.$dropdown.toggleClass('d-none');
            this.trigger_up('dropdown_clicked', {
                filter_name: this.name
            });
            if (!this.$dropdown.hasClass('d-none')){
                this._searchRecord('', true);
            }
        },
    
        _onSelect: function(ev){
            ev.preventDefault();
            let $target = $(ev.target);
            let recordKey = $target.data('record-key');
            let recordText = $target.text();
            this._setValue(recordKey, recordText);
    
            this.$dropdown.addClass('d-none');
            this.onchange();
        },
    
        _getRecords: async function(query){
            return await _.filter(this.selections, function(selection){return selection.name.toLowerCase().includes(query)});
        },
    
        _searchRecord: async function(query, force=false){
            if (query === '' && !force){
                this.$dropdown.addClass('d-none');
                this._resetValue();
                this.onchange();
            } else {
                let records = await this._getRecords(query);
                this._doSearch(records, query);
            }
        },
    
        _doSearch: function(records, query){
            this.$dropdown.html('');
            if (records.length > 0){
                for (let record of records){
                    let $li = $('<li class="o_record_name" data-record-key="' + record.key + '">' + record.name + '</li>');
                    this.$dropdown.append($li);
                }
            } else {
                let $li = $('<li class="o_record_name o_not_found"><i>No result found for: '+ query +'</i></li>');
                this.$dropdown.append($li);
            }
            this.$dropdown.removeClass('d-none');
        },
    
        _setValue: async function(value, label){
            this.value = value;
            if (label === undefined){
                if (value === this.default){
                    label = ''
                } else {
                    label = await this._getDisplayName(value);
                }
            }
            this.$input.val(label);
            this.isDirty = this.value !== this.savedValue;
        },

        _saveValue: function(){
            this.savedValue = this.value;
            this.isDirty = false;
        },
    
        _resetValue: function(){
            this._setValue(this.default, '');
        },

        _setDisabled: function(disabled){
            this.disabled = disabled;
            if (this.$input){
                this.$input.prop('disabled', disabled);
            }
        }
    });
    
    var FieldMany2One = FieldSelection.extend({
        type: 'many2one',

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.model = params.model;
            this.domain = params.domain || [];
            this.rec_name = params.rec_name;
            this.key = params.key || 'id';
        },
    
        _getRecords: async function(query){
            let domain = this.domain.slice();
            domain.push([this.rec_name, 'ilike', query]);
    
            let records = await this._rpc({
                model: this.model,
                method: 'search_read',
                domain: domain,
                fields: [this.key, this.rec_name],
                limit: 10
            })

            let result = [];
            var self = this;
            _.each(records, function(record){
                result.push({key: record[[self.key]], name: record[[self.rec_name]]});
            });
            return result;
        }
    });

    var FieldSelectionMany = Widget.extend({
        type: 'selection',
        template: 'StockPerWhSelectionMany',
        events: {
            'input .o_record_input': '_onInput',
            'click .o_open_dropdown': '_onClick',
            'click .o_record_name:not(.o_not_found)': '_onSelect',
        },

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.name = params.name;
            this.label = params.label;

            this.default = params.default || false;
            this.value = params.value || this.default;
            this.disabled = params.disabled || false;
            this.selections = params.selections || [];
            this.readonly =  params.readonly;
            this.default = params.default || false;

            this.savedValue = this.value;
            this.isDirty = false;

            this.onchange = params.onchange || function(){};
        },

        start: function() {
            this.$el = $(this.el);
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                // Set the jQuery elements
                self.$input = self.$el.find('.o_record_input');
                self.$dropdown = self.$el.find('.o_record_dropdown');
                self._setValue(self.value);
                // Enable multi select using select2
                self.$input.select2({
                    placeholder: 'Select ' + self.name,
                    width: 'resolve',
                    allowClear: true,
                    formatNoMatches: false,
                    multiple: true,
                    theme: "classic"
                });
            });
        },

        _getDisplayName: async function(value){
            let displayName = '';
            let displayNames = _.filter(await this._getRecords(''), function(record){return record.key === value;});
            if (displayNames.length){
                displayName = displayNames[0].name;
            }
            return displayName;
        },

        _onInput: async function(ev){
            ev.stopPropagation();
            let query = $(ev.target).val().toLowerCase();
            this._searchRecord(query);
        },

        _onClick: async function(ev){
            ev.preventDefault();
            if (this.disabled){
                return;
            }
            this.$dropdown.toggleClass('d-none');
            this.trigger_up('dropdown_clicked', {
                filter_name: this.name
            });
            if (!this.$dropdown.hasClass('d-none')){
                this._searchRecord('', true);
            }
        },

        _onSelect: async function(ev){
            ev.preventDefault();
            let $target = $(ev.target);
            let recordKey = $target.data('record-key');
            let recordText = $target.text();
            this._setValue(recordKey, recordText);
            this.$dropdown.addClass('d-none');
            this.onchange();
        },

        _getRecords: async function(query){
            return await _.filter(this.selections, function(selection){return selection.name.toLowerCase().includes(query)});
        },

        _searchRecord: async function(query, force=false){
            if (query === '' && !force){
                this.$dropdown.addClass('d-none');
                this._resetValue();
                this.onchange();
            } else {
                let records = await this._getRecords(query);
                this._doSearch(records, query);
            }
        },

        _doSearch: async function(records, query){
            this.$dropdown.html('');
            this.$dropdown.removeClass('d-none');
        },

        _setValue: async function(value, label){
            this.value = value;
            if (label === undefined){
                if (value === this.default){
                    label = ''
                } else {
                    label = await this._getDisplayName(value);
                }
            }
            this.$input.val(label);
            this.isDirty = this.value !== this.savedValue;
        },

        _saveValue: async function(){
            this.savedValue = this.value;
            this.isDirty = false;
            // Dynamic update of selection
            let self = this;
            let records = await this._getRecords('');
            let data = [];
            _.each(records, function(record){
                data.push({id: record['key'], text: record['name']});
            });
            this.$input.select2({
                width: 'resolve',
                allowClear: true,
                multiple: true,
                data: data,
            });
            this.$input.on("change", function (ev) { self.onchange(ev) });
        },

        _resetValue: async function(){
            this._setValue(this.default, '');
        },

        _setDisabled: async function(disabled){
            this.disabled = disabled;
            if (this.$input){
                this.$input.prop('disabled', disabled);
            }
        }
    });

    var FieldMany2Many = FieldSelectionMany.extend({
        type: 'many2many',

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.model = params.model;
            this.domain = params.domain || [];
            this.rec_name = params.rec_name;
            this.key = params.key || 'id';
        },

        _getRecords: async function(query){
            let domain = this.domain.slice();
            domain.push([this.rec_name, 'ilike', query]);

            let records = await this._rpc({
                model: this.model,
                method: 'search_read',
                domain: domain,
                fields: [this.key, this.rec_name],
                theme: "classic"
            })
            let result = [];
            var self = this;
            _.each(records, function(record){
                result.push({key: record[[self.key]], name: record[[self.rec_name]]});
            });
            return result;
        }
    });

    var FieldBoolean = Widget.extend({
        type: 'boolean',
        template: 'StockPerWhBoolean',
    
        events: {
            'click': '_onClick'
        },
    
        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.name = params.name;
            this.disabled = params.disabled;
            this.readonly = params.readonly;
            this.default = params.default || false;
            this.value = params.value || this.default;
            this.isDirty = false;
            this.savedValue = this.value;
            this.onchange = params.onchange || function(){};
        },
    
        start: function(){
            this.$el = $(this.el);
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$input = self.$el.find('.o_bool_input');
                self._setValue(self.value);
            });
        },
        
        _onClick:  function(ev){
            ev.preventDefault();
            if (this.disabled){
                return;
            }
            this._setValue(!this.value);
            this.onchange();
        },
    
        _setValue: function(value){
            this.value = value;
            this.$input.prop('checked', value === true);
            this.isDirty = this.value != this.savedValue;
        },

        _saveValue: function(){
            this.savedValue = this.value;
            this.isDirty = false;
        },
    
        _resetValue: function(){
            this._setValue(this.default);
        },

        _setDisabled: function(disabled){
            this.disabled = disabled;
            if (this.$input){
                this.$input.prop('disabled', disabled);
            }
        }
    });

    var Button = Widget.extend({
        template: 'StockPerWhButton',

        events: {
            'click': '_onClick'
        },

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.name = params.name;
            this.label = params.label;
            this.onclick = params.onclick || function(){};
            this.disabled = params.disabled || false;
        },

        _onClick: function(ev){
            ev.stopPropagation();
            if (!this.disabled){
                this.onclick();
            }
        },

        _setDisabled: function(disabled){
            this.disabled = disabled;
            if (this.$el){
                this.$el.prop('disabled', disabled);
            }
        }
    });

    var StockPerWhControlPanel = Widget.extend({
        template: 'StockPerWhControlPanel',

        custom_events: {
            dropdown_clicked: '_onDropDownClicked'
        },

        filterNames: [
            'warehouse', 'location', 'brand', 'product_category', 'lot', 'product_code',
            'product_name', 'sold_product', 'minus_stock', 'fsn_color'
        ],

        buttonNames: [
            'btn_apply',
            'btn_reset'
        ],

        init: function(parent, params){
            this._super.apply(this, arguments);

            this.warehouse = new FieldMany2One(this, {name: 'warehouse', label: 'Warehouse', model: 'stock.warehouse', rec_name: 'name', onchange: this._onWarehouseChange.bind(this)});
            this.location = new FieldMany2Many(this, {name: 'location', label: 'Location', model: 'stock.location', domain: [['warehouse_id', '=', this.warehouse.value]], rec_name: 'complete_name', readonly: '!%(warehouse)', onchange: this._onLocationChange.bind(this)});
            this.brand = new FieldMany2Many(this, {name: 'brand', label: 'Brand', model: 'product.brand', rec_name: 'brand_name', readonly: '!%(warehouse)', onchange: this._checkButtons.bind(this)});
            this.product_category = new FieldMany2Many(this, {name: 'product_category', label: 'Product Category', model: 'product.category', rec_name: 'name', readonly: '!%(warehouse)', onchange: this._checkButtons.bind(this)});
            this.lot = new FieldMany2Many(this, {name: 'lot', label: 'Lot/Serial Number', model: 'stock.production.lot', rec_name: 'name', readonly: '!%(warehouse)', onchange: this._checkButtons.bind(this)});
            this.product_code = new FieldMany2Many(this, {name: 'product_code', label: 'Product Code', model: 'product.product', key: 'default_code', rec_name: 'default_code', domain: [['default_code', 'not in', [false, '', ' ']]], readonly: '!%(warehouse)', onchange: this._checkButtons.bind(this)});
            this.product_name = new FieldMany2Many(this, {name: 'product_name', label: 'Product Name', model: 'product.product', key: 'product_display_name', rec_name: 'product_display_name', domain: [['product_display_name', 'not in', [false, '', ' ']]], readonly: '!%(warehouse)', onchange: this._checkButtons.bind(this)});
            this.sold_product =  new FieldSelection(this, {name: 'sold_product', label: 'Sold Product', selections: [{key: 7, name: '7 Days'}, {key: 1, name: '1 Day'}, {key: 30, name: '30 Days'}, {key: 90, name: '90 Days'}], readonly: '!%(warehouse)', onchange: this._onSoldProductChange.bind(this)});
            this.minus_stock = new FieldBoolean(this, {name:'minus_stock', readonly: '!%(warehouse)', onchange: this._checkButtons.bind(this)});
            this.fsn_color = new FieldBoolean(this, {name:'fsn_color', readonly: '!%(sold_product)', onchange: this._checkButtons.bind(this)});
            this.btn_apply = new Button(this, {name: 'apply', label: 'Apply', disabled: true, onclick: this._onClickApply.bind(this)});
            this.btn_reset = new Button(this, {name: 'reset', label: 'Reset', disabled: true, onclick: this._onClickReset.bind(this)});
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                _.each(self.filterNames.concat(self.buttonNames), function(name){
                    self[[name]].appendTo(self.$el.find('.o_filter_' + name));
                });
                self._applyModifiers();
            });
        },

        _applyModifiers: function(){
            var self = this;
            _.each(this.filterNames, function(name){
                let filter = self[[name]];
                if (filter.readonly){
                    let expr = filter.readonly;
                    _.each(expr.match(/%\(([^)]+)\)/g), function(exp){
                        let fieldName = exp.slice(2, -1);
                        let newExp = 'self.' + fieldName + '.value';
                        expr = expr.replace(exp, newExp);
                    });
                    let disabled = eval(expr);
                    filter._setDisabled(disabled);
                }
            });
        },

        _clean: function(){
            var self = this;
            _.each(this.filterNames, function(name){
                self[[name]]._saveValue();
            });
        },

        _onWarehouseChange: function(){
            var self = this;
            _.each(this.filterNames, function(name){
                if (name !== 'warehouse'){
                    self[[name]]._resetValue();
                }
            });
            this.location.domain = [['warehouse_id', '=', this.warehouse.value]];
            this.trigger_up('apply_filters');
        },

        _onLocationChange: function(){
            this.trigger_up('apply_filters');
        },

//        _onProductCategoryChange: function(){
//            this.trigger_up('apply_filters');
//        },

        _onSoldProductChange: function(){
            let disabled = this.sold_product.value === false;
            if (disabled){
                this.fsn_color._setValue(false);
//                this.minus_stock._setValue(false);
            }
            this.fsn_color._setDisabled(disabled);
//            this.minus_stock._setDisabled(disabled);
            this._checkButtons();
        },

        _checkButtons: function(){
            let isDirty = false;
            let hasChange = false;
            var self = this;
            _.each(this.filterNames, function(name){
                if (!['warehouse', 'location'].includes(name)){
                    let filter = self[[name]];
                    // Enable or Disable buttons based on many2many tags
                    let SelectedIds = [];
                    let Elm = document.getElementsByClassName("o_"+filter.name+"_tags");
                    if(Elm) {
                        let Data = $(Elm[0]).select2('data');
                        _.each(Data, function(item){
                            SelectedIds.push(item.id);
                        });
                    }
                    if (SelectedIds.length){
                        isDirty = true;
                        hasChange = true;
                    }
                    // Enable or disable based on Many2one
                    if (filter.isDirty){
                        isDirty = true;
                    }
                    if (filter.value !== filter.default){
                        hasChange = true;
                    }
                }
            });
            this.btn_apply._setDisabled(!isDirty);
            this.btn_reset._setDisabled(!hasChange);
        },

        _onClickApply: function(){
            this.trigger_up('apply_filters');
        },

        _onClickReset: function(){
            var self = this;
            _.each(this.filterNames, function(name){
                if (!['warehouse', 'location'].includes(name)){
                    self[[name]]._resetValue();
                }
            });
            this.trigger_up('apply_filters', {
                warehouse: this.warehouse.value,
                location: this.location.value
            });
        },

        _onDropDownClicked: function(ev){
            this.$el.find('.o_record_dropdown:not(.o_'+ ev.data.filter_name +'_dropdown)').addClass('d-none');
        },
    });

    return {
        FieldSelection: FieldSelection,
        FieldMany2One: FieldMany2One,
        FieldMany2Many: FieldMany2Many,
        FieldBoolean: FieldBoolean,
        StockPerWhControlPanel: StockPerWhControlPanel
    }
});