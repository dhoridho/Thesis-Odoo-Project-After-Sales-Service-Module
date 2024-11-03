odoo.define('oi_web_search.SearchMenu', function (require) {
    "use strict";
    
    const DropdownMenu = require('web.DropdownMenu');
    const OwlDialog = require('web.OwlDialog');
    const { ComponentAdapter } = require('web.OwlCompatibility');
    const { useModel } = require('web/static/src/js/model.js');
    
    const relational_fields = require('web.relational_fields');
    const basic_fields = require('web.basic_fields');
    const AbstractField = require('web.AbstractField');
    
    const { FIELD_OPERATORS, FIELD_TYPES } = require('web.searchUtils');
    
    const BasicModel = require('web.BasicModel');
    const Domain = require('web.Domain');
    const session = require('web.session');
    
    const core = require('web.core');
    const qweb = core.qweb;
    const _t = core._t;
    const _lt = core._lt;    
    
    const py_utils = require('web.py_utils');
    const field_utils = require('web.field_utils');
    
    const Dialog = require('web.Dialog');
    
    const DomainSelector = require("web.DomainSelector");
    
    const DomainSelectorDialog = Dialog.extend({
        init: function (parent, model, domain, options) {
            this.model = model;
            this.options = _.extend({
                readonly: true,
                debugMode: false,
            }, options || {});
            var self = this;
            var buttons;
            if (this.options.readonly) {
                buttons = [
                    {text: _t("Close"), close: true},
                ];
            } else {
                buttons = [
                    {text: _t("Search"), classes: "btn-primary", close: true, click: function () {
                        this.trigger_up("domain_selected", {
                        	domain: this.domainSelector.getDomain(),
                        	description : self.$('.o_input_description').val()
                        	});
                    }},
                    {text: _t("Cancel"), close: true},
                ];
            }

            this._super(parent, _.extend({}, {
                title: _t("Domain"),
                buttons: buttons,
            }, options || {}));

            this.domainSelector = new DomainSelector(this, model, domain, options);
        },
        start: function () {
            var self = this;
            this.opened().then(function () {
                // this restores default modal height (bootstrap) and allows field selector to overflow
                self.$el.css('overflow', 'visible').closest('.modal-dialog').css('height', 'auto');
            });
            return Promise.all([
                this._super.apply(this, arguments),
                this.domainSelector.appendTo(this.$el)
            ]);
        },
    });    
    
    const OPERATORS_SELECTION = {
            boolean: [
                { symbol: "=", description: _lt("is true"), value: true },
                { symbol: "!=", description: _lt("is false"), value: true },
            ],
            char: [
                { symbol: "ilike", description: _lt("contains") },
                { symbol: "not ilike", description: _lt("doesn't contain") },
                { symbol: "=", description: _lt("is equal to") },
                { symbol: "!=", description: _lt("is not equal to") },
                { symbol: "=", description: _lt("is set"), value: false },
                { symbol: "!=", description: _lt("is not set"), value: false },
            ],
            date: [
                { symbol: "=", description: _lt("is equal to") },
                { symbol: "!=", description: _lt("is not equal to") },
                { symbol: ">", description: _lt("is after") },
                { symbol: "<", description: _lt("is before") },
                { symbol: ">=", description: _lt("is after or equal to") },
                { symbol: "<=", description: _lt("is before or equal to") },
                { symbol: "between", description: _lt("is between") },
                { symbol: "=", description: _lt("is set"), value: false },
                { symbol: "!=", description: _lt("is not set"), value: false },
            ],
            number: [
                { symbol: "=", description: _lt("is equal to") },
                { symbol: "!=", description: _lt("is not equal to") },
                { symbol: ">", description: _lt("greater than") },
                { symbol: "<", description: _lt("less than") },
                { symbol: ">=", description: _lt("greater than or equal to") },
                { symbol: "<=", description: _lt("less than or equal to") },
                { symbol: "between", description: _lt("is between") },
                { symbol: "=", description: _lt("is set"), value: false },
                { symbol: "!=", description: _lt("is not set"), value: false },
            ],
            selection: [
                { symbol: "in", description: _lt("is") },
                { symbol: "not in", description: _lt("is not") },
                { symbol: "=", description: _lt("is set"), value: false },
                { symbol: "!=", description: _lt("is not set"), value: false },
            ],
            one2many: [
                { symbol: "!=", description: _lt("is set"), value: false },
                { symbol: "=", description: _lt("is not set"), value: false },
            ],            
        };    
    
    const FIELD_OPERATOR = {
            boolean: 'boolean',
            char: 'char',
            date: 'date',
            datetime: 'date',
            float: 'number',
            id: 'number',
            integer: 'number',
            html: 'char',
            many2many: 'selection',
            many2one: 'selection',
            monetary: 'number',
            one2many: 'one2many',
            text: 'char',
            selection: 'selection'
    };

    const FieldMany2ManyTags = relational_fields.FieldMany2ManyTags.extend({
    	_renderEdit: function () {
    		var self = this;
    		return this._super.apply(this, arguments).then(function(){
    			self.many2one.additionalContext = self.additionalContext;
    			self.many2one._getSearchBlacklist = function () {
    				if (self.value === false) {
    					self.value  = {
    	    					count : 0,
    	    					data : [],
    	    					res_ids : []
    	    			}
    				}
    				var res_ids = [];
    				_.each(self.value.res_ids, function(res_id){
    					if (_.isObject(res_id))
    						res_ids.push(res_id.id);
    					else
    						res_ids.push(res_id);
    				});    				
    	            return res_ids;
    	        };    		
    	        self.many2one._getSearchCreatePopupOptions = function(view, ids, context, dynamicFilters) {
    	            return {
    	                res_model: this.field.relation,
    	                domain: this.record.getDomain({fieldName: this.name}),
    	                context: _.extend({}, this.record.getContext(this.recordParams), context || {}),
    	                dynamicFilters: dynamicFilters || [],
    	                title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
    	                initial_ids: ids,
    	                initial_view: view,
    	                disable_multiple_selection: false,
    	                no_create: true,
    	                kanban_view_ref: this.attrs.kanban_view_ref,
    	                on_selected: function (records) {
    	                    _.each(records, function(record){
                                self._rpc({
                                    model: self.field.relation,
                                    method: 'search_read',
                                    kwargs: {
                                        domain: [['id', '=', record.id]],
                                        fields: ['id','name','display_name'],
                                    },
                                }).then(function(data) {
                                    var action = data;
                                    self._addTag(action[0]);
                                });
                                // self._addTag(record);
                            });
    	                },
    	                on_closed: function () {
    	                    self.activate();
    	                },
    	            };
    	        };
    		});
    	},
    	
    });    
    
    const FieldSelectionTags = AbstractField.extend({
    	supportedFieldTypes: ['selection'],
    	tag_template: "FieldMany2ManyTag",
    	className: "o_field_many2manytags",

        custom_events: _.extend({}, AbstractField.prototype.custom_events, {
            field_changed: '_onFieldChanged',        
        }),
        
        events: _.extend({}, AbstractField.prototype.events, {
            'click .o_delete': '_onDeleteTag',
        }),
        
        init: function () {
            this._super.apply(this, arguments);
            this.selections = [];
            this.selections_values = [];
        },    
        _reset: function () {
            this._super.apply(this, arguments);
            this.selections = [];
            this.selections_values = [];
        },
        
        _renderEdit: function () {
            var self = this;
            this._renderTags();
            if (this.selection) {
                this.selection.destroy();
            }
            this.selection = new relational_fields.FieldSelection(this, this.name, this.record, {
                mode: 'edit',
                noOpen: true,
                viewType: this.viewType,
                attrs: this.attrs,
            });
            
            this.selection.values = _.filter(this.selection.values, function (v) {
                return !_.contains(self.selections_values, v[0]);
            });
                    
            return this.selection.appendTo(this.$el);
        },
        /**
         * @private
         */
        _renderReadonly: function () {
            this._renderTags();
        },	
        _renderTags: function () {
            this.$el.html(qweb.render(this.tag_template, this._getRenderTagsContext()));
        },
        _getRenderTagsContext: function () {
            var elements = this.selections;
            return {
                colorField: this.colorField,
                elements: elements,
                hasDropdown: this.hasDropdown,
                readonly: this.mode === "readonly",
            };
        },
        _addTag: function (data) {
            if (!_.contains(this.selections_values, data)) {
            	this.selections_values.push(data);
            	this.selections.push({
            		id : data,
            		display_name : this.selection._formatValue(data)
            	});
            	this._setValue(JSON.stringify(this.selections_values));
            	this._renderEdit();
            }
            
        },
        _removeTag: function (value) {
        	if (_.contains(this.selections_values, value)) {
        		this.selections_values = _.filter(this.selections_values, function(v){
        			return v !=value;
        		});
        		this.selections = _.filter(this.selections, function(v){
        			return v.id !=value;
        		});
        		this._setValue(JSON.stringify(this.selections_values));
            	this._renderEdit();
        	}
        },
        
        _onFieldChanged: function (ev) {
            if (ev.target !== this.selection) {
                return;
            }
            ev.stopPropagation();
            
            var newValue = ev.data.changes[this.name];
            if (newValue) {
            	this._addTag(newValue);
            }
            
        },
        
        _onDeleteTag: function (event) {
            event.preventDefault();
            event.stopPropagation();
            this._removeTag($(event.target).parent().data('id'));
        },
        
    });
    
    
    class SearchMenu extends DropdownMenu {
    	
    	constructor() {
    		super(...arguments);
    		this.model = useModel('searchModel');    		    		
    		this.filters_fields = this.model.get('filters', f => f.type === 'field');
    		_.each(this.filters_fields, function(field){
    			field.range = _.contains(['date', 'datetime', 'float', 'integer', 'monetary'], field.fieldType);
    		});
    		this.res_model = this.env.action.res_model;
    		this._model = new BasicModel(this);
    		this.form_fields= [];
    		this.form_fields2= [];
    		this.OPERATORS = FIELD_OPERATORS;
    		this.all_form_fields= [];
    		this.all_form_fields2= [];
    	}
    	
    	async willStart() {
    		this.recordID = await this._makeRecord();
    	}
    	    	
    	get icon() {
    		return "fa fa-search";
    	}
    	
        get title() {
            return this.env._t("Search");
        }    	
        
        _trigger_rpc(event){
        	if (event.data.callback) {
            	var prom = new Promise((resolve, reject) => { 
            		session.rpc(...event.data.args).then(function(result){
            			resolve(result);
            		});
            	}); 
            	prom.abort = function () {};
            	event.data.callback(prom);         		
        	}
        }
        
        _trigger_get_session(event){
            if (event.data.callback) {
                event.data.callback(session);
            }     	
        }        
        
        _trigger_field_changed(event){
        	event.stopPropagation();  
        	var self = this;
        	var field = event.target;
        	var value = event.data.changes[field.name];    	
        	
        	if (value.operation === 'ADD_M2M') {
        		if (Array.isArray(value.ids)){
        			var ids = _.pluck(value.ids, 'id');
        			session.rpc({
                        model: field.field.relation,
                        method: 'name_get',
                        args: [ids],
                    })
                    .then(function (name_gets) {
                    	_.each(value.ids, function (rec) {
                            var name_get = _.find(name_gets, function (n) {
                                return n[0] === rec.id;
                            });
                            rec.display_name = name_get[1];
                            
                            field.value.data.push({data : rec, res_id : rec.id , id : rec.id});
                            field.value.res_ids.push(rec.id);
                            field.value.count +=1;
                        });
                    	field._renderEdit();
                    	self.$('button.o_dropdown_toggler_btn').dropdown('toggle');
                    });    		
        		}
        		else {
        			var res_id = value.ids.id;
        			if (field.value === false) {
        				field.value = {
        						data : [],
        						res_ids : [],
        						count : 0
        				}
        			}
        				
        			field.value.data.push({data : value.ids, res_id : res_id , id : res_id});
                	field.value.res_ids.push(res_id);
                	field.value.count +=1;
                	field._renderEdit();
        		}
        		    		
        	}
        	else if (value.operation === 'FORGET') {
        		
        		field.value.data = _.filter(field.value.data, function(record){
        			return !_.contains(value.ids, record.id); 
        		});
        		field.value.res_ids = _.filter(field.value.data, function(res_id){
        			return !_.contains(value.ids, res_id); 
        		});
        		field.value.count = field.value.data.length;
        		field._renderEdit();
        	}    	
        	else {    		
        		field.value = value;    		
        	}
        	
        }
        
        _trigger_up_owl(ev) {
            const evType = ev.name;
            const payload = ev.data;
            if (evType === 'call_service') {
                let args = payload.args || [];
                if (payload.service === 'ajax' && payload.method === 'rpc') {
                    // ajax service uses an extra 'target' argument for rpc
                    args = args.concat(ev.target);
                }
                const service = this.env.services[payload.service];
                const result = service[payload.method].apply(service, args);
                payload.callback(result);
            } else if (evType === 'get_session') {
                if (payload.callback) {
                    payload.callback(this.env.session);
                }
            } else if (evType === 'load_views') {
                const params = {
                    model: payload.modelName,
                    context: payload.context,
                    views_descr: payload.views,
                };
                this.env.dataManager
                    .load_views(params, payload.options || {})
                    .then(payload.on_success);
            } else if (evType === 'load_filters') {
                return this.env.dataManager
                    .load_filters(payload)
                    .then(payload.on_success);
            } else {
                payload.__targetWidget = ev.target;
                this.trigger(evType.replace(/_/g, '-'), payload);
            }
        }
        
        _trigger_up(event) {
        	if (event.name =='call_service' && event.data.service == 'ajax' && event.data.method == 'rpc') {
        		this._trigger_rpc(event);
        	}
        	else if (event.name =='field_changed') {
        		this._trigger_field_changed(event);
        	}        	
        	else if (event.name =='get_session') {
        		this._trigger_get_session(event);
        	} 
        	else if (event.name =='domain_changed' || event.name == 'field_chain_changed') {
        		
        	}         	
        	else if (event.name =='domain_selected') {
        		const filter = {
        				description : event.data.description || _lt("Filter"),
    					domain: Domain.prototype.arrayToString(event.data.domain),
    					type: 'filter',
    				}
        		this.model.dispatch('createNewFilters', [filter]);
        	}         	
        	else if (event.name =='load_views') {
        		const payload = event.data;
                const params = {
                        model: payload.modelName,
                        context: payload.context,
                        views_descr: payload.views,
                    };
                this.env.dataManager
                    .load_views(params, payload.options || {})
                    .then(payload.on_success);
        	}
        	else {
            	this._trigger_up_owl(event);
        	}
        }
        
        
        async _makeRecord() {
        	var fieldsInfo = {};                          
        	var fields = _.clone(this.props.fields);
        	_.each(fields, function(field){
        		delete field.domain; 
        		
        		if (field.type =='one2many') {
        			field.type ='char';
        		}
        	});
            return this._model.makeRecord(this.res_model, fields, fieldsInfo);
        }
        
        _get_field_widget(fieldType) {
        	switch (fieldType) {
	        	case 'many2one':
	        	case 'many2many':
	        		return FieldMany2ManyTags;
	        	case 'text':
	        	case 'char':
	        		return basic_fields.FieldChar;
	        	case 'selection':
	        		return FieldSelectionTags;
	        	case 'date':
	        		return basic_fields.FieldDate;
	        	case 'datetime':
	        		return basic_fields.FieldDateTime;
	        	case 'float':
	        	case 'monetary':
	        		return basic_fields.FieldFloat;
	        	case 'integer':
	        		return basic_fields.FieldInteger;
        	}
        	return basic_fields.FieldChar;
        }
        
        _render_fields () {
        	var self = this;
        	var record = this._model.get(this.recordID);      
        	const widget = $(this.el);
        	self.form_fields={};
        	self.form_fields2={};
        	_.extend(record.context, self.env.action.context);  
        	_.each(this.filters_fields, function(field){        		
        		const Widget = self._get_field_widget(field.fieldType);
        		if (Widget === false)
        			return;        		
        		const options = {
                        mode: 'edit',
                        additionalContext : _.extend({}, self.env.action.context),
                        attrs: {
                        	string : field.description,
                        	options : {
                        		no_create: true
                        		}
                        }
                    }
        		if (field.range) {
            		const o_input1 = widget.find(_.str.sprintf(".o_input1[name='%s']", field.fieldName));
            		const o_input2 = widget.find(_.str.sprintf(".o_input2[name='%s']", field.fieldName));
            		var form_field1 = new Widget(self, field.fieldName, record, options); 
            		var form_field2 = new Widget(self, field.fieldName, record, options); 
        			self.form_fields[field.fieldName] = form_field1;         
        			form_field1.appendTo(o_input1);   
        			self.form_fields2[field.fieldName] = form_field2;         
        			form_field2.appendTo(o_input2);              			
        		}
        		else {
        			const o_input = widget.find(_.str.sprintf(".o_input[name='%s']", field.fieldName));
        			var form_field = new Widget(self, field.fieldName, record, options);    
        			self.form_fields[field.fieldName] = form_field;         
        			form_field.appendTo(o_input);
        		}
        	});
        }
        
        async render(force = false) {
        	var self = this;
        	return super.render(force).then(function(){
        		self._render_fields();
        	});
        }
        
        _get_field_value (field_name, index){
        	const widget = index==1 ? this.all_form_fields[field_name] : this.all_form_fields2[field_name];
        	if (!widget)
        		return false;
        	const field = widget.field;
        	var value = widget.value;
        	var name = value;
        	if (field.type == 'date' || field.type == 'datetime') {
            	if (!value)
            		return false;
            	name = field_utils.format[field.type](value);
        		value = value.toJSON();        		
        	}
        	else if (field.type == 'selection') {
        		value = widget.selections_values;
        		name = _.map(widget.selections, obj => obj.display_name);
        	}
        	else if (field.type == 'many2many' || field.type == 'many2one') {
        		name = _.map(value.data, obj => obj.data.display_name);       		
        		value = value.res_ids;        		
        	}        	
        	if (Array.isArray(name)) {
        		var many = name.length > 1;
        		name = name.join(",");
        		if (many)
        			name = _.str.sprintf("(%s)", name);
        		
        	}
        	return {
        		value : value,
        		name : name,
        	}
        }
        
        _onAllFieldsSearch(dialog, is_and) {
        	const filters = []; 
        	const self = this;
			dialog.$('.o_input_operator').each(function(){
				const $select = $(this);
				const field_type = $select.data('field-type');
				const field_name = $select.data('name');
    			const value = $select.val();        
    			if (value=== "" || !$select.is(':visible'))
    				return;
				const operator = _.find(OPERATORS_SELECTION[FIELD_OPERATOR[field_type]], function(op){
					return op.symbol == value;
				});                       			
    			var domain;
    			var description = [self.props.fields[field_name].description, operator.description];
    			if (operator.value !== undefined) {
    				domain = [[field_name, value, operator.value]];                    				
    			}
    			else if (value == "between") {
    				const value1 = self._get_field_value(field_name,1);
    				const value2 = self._get_field_value(field_name,2);
    				if (value1.value === false || value2.value === false)
    					return;    				
    				domain = [[field_name, '>=', value1.value], [field_name, '<=', value2.value]];
    				description.push(value1.name, self.env._t("and"), value2.name);
    			}
    			else {
    				const value1 = self._get_field_value(field_name,1);
    				if (value1.value === false)
    					return;
    				domain = [[field_name, value, value1.value]];
    				description.push(value1.name);
    			}
    			filters.push({
    				description : description.join(" "),
					domain: Domain.prototype.arrayToString(domain),
					type: 'filter',
				});
			});
			self.all_form_fields = [];
			self.all_form_fields2 = [];        
			if (is_and) {
				_.each(filters, function(filter){
					self.model.dispatch('createNewFilters', [filter]);
				});
			}
			else {
				self.model.dispatch('createNewFilters', filters);
			}				
			
        }
        
        async _onAdvanceButtonClick() {
        	var self = this;    
        	var $content = $(qweb.render('web.SearchMenu.domain', {'widget' : self}));
        	var title = _t('Advance Search');
        	this.dialog_domain = new DomainSelectorDialog(self, self.res_model, "[]", {
        		readonly : false,
        		$content : $content,
        		title : title
        	});
        	this.dialog_domain.open();
        	this.state.open = false;
        }
        
        async _onAllFieldsButtonClick() {
        	var self = this;
        	var title = _t('Advance Search');
        	var fields = _.values(self.props.fields);
        	fields = _.filter(fields, field => field.searchable);
        	fields = _.sortBy(fields, field => field.string);
        	var $content = $(qweb.render('oi_web_search.all.fields', {'widget' : self, debug: odoo.debug, fields : fields, OPERATORS_SELECTION : OPERATORS_SELECTION, FIELD_OPERATOR: FIELD_OPERATOR}));
        	var dialog = new Dialog(this, {
                title: title,
                size : 'extra-large',
                buttons : [
                	{
                		text : _t('Match All'),
                		classes: 'btn-primary',
                		close : true,
                		click : function(){
                			self._onAllFieldsSearch(dialog, true);
                		}
                	},
                	{
                		text : _t('Match Any'),
                		classes: 'btn-primary',
                		close : true,
                		click : function(){
                			self._onAllFieldsSearch(dialog, false);
                		}
                	},                	
                	{
                		text: _t('Cancel'),
                		close: true,
                		click : function(){
                			self.all_form_fields = [];
                			self.all_form_fields2 = [];
                		}
                	}
                ],
                $content: $content,
                onForceClose : function(){
        			self.all_form_fields = [];
        			self.all_form_fields2 = [];
                }
            });

        	dialog.opened().then(function(){
        		dialog.$('input.filter_fields').keydown(function(event){
        			const $input = $(this);
        			const value = $input.val().toUpperCase();
        			dialog.$('div.field_row').each(function(){
        				const $div = $(this);
        				const field_name = $div.data('name');
        				const field_string = $div.data('string');
        				$div.toggleClass('o_hidden', value !== "" && !_.str.contains(field_name, value) && !_.str.contains(field_string, value));
        			});
        		});
        		
        		dialog.$('.o_input_operator').change(function(event){
        			const $select = $(this);
        			const field_type = $select.data('field-type');
        			if (field_type == 'boolean')
        				return;
        			const field_name = $select.data('name');
        			const value = $select.val();        
        			const field = self.props.fields[field_name];
        			const o_input = dialog.$(_.str.sprintf("div.o_field_input[name='%s']", field_name));      
        			const o_input1 = dialog.$(_.str.sprintf("div.o_input1[name='%s']", field_name));     
        			const o_input2 = dialog.$(_.str.sprintf("div.o_input2[name='%s']", field_name));   
    				const operator = _.find(OPERATORS_SELECTION[FIELD_OPERATOR[field_type]], function(op){
    					return op.symbol == value;
    				});         			
        			const hide_input =  value === "" || operator.value === false;
        			o_input.toggleClass('o_hidden', hide_input);
        			o_input2.toggleClass('o_hidden', value !== "between");
        			
        			if (!hide_input && self.all_form_fields[field_name] === undefined) {
        				const Widget = self._get_field_widget(field_type);
        				const record = self._model.get(self.recordID);      
                		const options = {
                                mode: 'edit',
                                additionalContext : _.extend({}, self.env.action.context),
                                attrs: {
                                	string : field.description,
                                	options : {
                                		no_create: true
                                		}
                                }
                            } ;       				
                		const form_field = new Widget(self, field_name, record, options);    
            			self.all_form_fields[field_name] = form_field;         
            			o_input1.length > 0 ? form_field.appendTo(o_input1) : form_field.appendTo(o_input) ;
            			if (o_input2.length > 0) {
            				const form_field2 = new Widget(self, field_name, record, options);   
            				self.all_form_fields2[field_name] = form_field2;    
            				form_field2.appendTo(o_input2);
            			}
            			
        			}
        		});
        	});
        	dialog.open();
        	this.state.open = false;
        }
        
        async _onApplyButtonClick() {
        	const self = this;
        	const filters = [];
        	_.each(this.form_fields, function(widget, fieldName){
        		var field = _.find(self.filters_fields, {fieldName : fieldName});
        		const widget2 = self.form_fields2[fieldName] || false;
        		if (widget.value === false && (!widget2 || widget2.value === false))
        			return;
        		
        		if (field.fieldType == 'many2one' || field.fieldType == 'many2many') {
        			_.each(widget.value && widget.value.data, function(data) {
        				var id = data.id;
        				var display_name = data.data.display_name;
        				if (_.isObject(id)) {
        					display_name = id.display_name;
        					id = id.id;        					
        				}
            			self.model.dispatch('addAutoCompletionValues', {
                            filterId: field.id,
                            value: id,
                            label: display_name || data.id,
                            operator: field.operator || '=',
                        });            			            			
        			});        			
        		}
        		else if (field.fieldType == 'selection') {
        			_.each(widget.selections, function(data) {
            			self.model.dispatch('addAutoCompletionValues', {
                            filterId: field.id,
                            value: data.id,
                            label: data.display_name || data.id,
                            operator: field.operator || '=',
                        });            			        				
        			});
        		}
        		else if (field.fieldType == 'text' || field.fieldType == 'char' || field.fieldType == 'one2many') {
        			self.model.dispatch('addAutoCompletionValues', {
                        filterId: field.id,
                        value: widget.value,
                        label: widget.value,
                        operator: field.operator || 'ilike',
                    });            			        			
        		}
        		else if (field.range) {
        			var value1 = widget.value;
        			var value2 = widget2 && widget2.value;
        			var label1 = value1;
        			var label2 = value2;
        			var field_operator = 'number';
        			if (field.fieldType == 'date' || field.fieldType == 'datetime') {
        				value1 = value1 && value1.toJSON();
        				value2 = value2 && value2.toJSON();
        				label1 = label1 && field_utils.format[field.fieldType](label1);
        				label2 = label2 && field_utils.format[field.fieldType](label2);
        				field_operator = field.fieldType;
        			}
        			var operator;
        			var descriptionArray;
        			var domainArray;
        			if (value1 !==false && value2 !==false) {
        				operator = _.find(self.OPERATORS['date'], function(op){
        					return op.symbol == 'between';
        				});        			        				
        				descriptionArray = [field.description, operator.description, label1, self.env._t("and"), label2];
        				domainArray = [[fieldName, '>=', value1], [fieldName, '<=', value2]];
        			}
        			else if (value1 !==false) {
        				operator = _.find(self.OPERATORS[field_operator], function(op){
        					return op.symbol == '>=';
        				});        				
        				descriptionArray = [field.description, operator.description, label1];
        				domainArray = [[fieldName, '>=', value1]];
        			}        	
        			else if (value2 !==false) {
        				operator = _.find(self.OPERATORS[field_operator], function(op){
        					return op.symbol == '<=';
        				});        				        				
        				descriptionArray = [field.description, operator.description, label2];
        				domainArray = [[fieldName, '<=', value2]];
        			}         			
    				filters.push({
    					description: descriptionArray.join(" "),
    					domain: Domain.prototype.arrayToString(domainArray),
    					type: 'filter',
    				})	

        		}
        	});
        	this.model.dispatch('createNewFilters', filters);
        	this.state.open = false;
        }
    }
    
    SearchMenu.template = 'oi_web_search.SearchMenu';
    
    SearchMenu.components = Object.assign({}, DropdownMenu.components, {
    	OwlDialog,
    });    
    
    SearchMenu.props = Object.assign({}, DropdownMenu.props, {
        fields: Object,
    });    
    
    return SearchMenu;
});    