odoo.define("advanced_web_domain_widget.DomainSelector", function (require) {
    "use strict";

    var core = require("web.core");
    var datepicker = require("web.datepicker");
    var field_utils = require("web.field_utils");
    var ModelFieldSelector = require("advanced_web_domain_widget.ModelFieldSelector");
    var ModelRecordSelector = require("advanced_web_domain_widget.ModelRecordSelector");
    const TerabitsDomainSelector = require("advanced_web_domain_widget.TerabitsDomainSelector").TerabitsDomainLeaf;

    var _t = core._t;

    var TerabitsDomainSelectorah = TerabitsDomainSelector.include({
        init: function (parent, model, domain, options) {
            this._super.apply(this, arguments);
        },
        willStart: function () {
             
            // if (this.__proto__.template =="TerabitsDomainLeaf"){
                var defs = [];

                // In edit mode, instantiate a field selector. This is done here in
                // willStart and prepared by appending it to a dummy element because the
                // TerabitsDomainLeaf rendering need some information which cannot be computed
                // before the ModelFieldSelector is fully rendered (TODO).
                 
                this.fieldSelector = new ModelFieldSelector(
                    this,
                    this.model,
                    this.chain !== undefined ? this.chain.toString().split(".") : [],
                    this.options
                );
                defs.push(this.fieldSelector.appendTo($("<div/>")).then((function () {
                    var wDefs = [];
                    var selectedField = this.fieldSelector.getSelectedField() || {};
                    if ((this.operator == 'in' && _.contains(['many2one', 'many2many', 'one2many'], selectedField.type) || selectedField.name == "id") && typeof (this.currentDomain[0][2][0]) == 'string') {
                        this.value = [];
                    } else {
                        this.value = this.currentDomain[0][2];
                    }
                    this.title = selectedField.string;
                    this.recordReader = new ModelRecordSelector(
                        this,
                        selectedField.relation,
                        this.chain !== undefined ? this.chain.toString().split(".") : [],
                        this.options,
                        this.title
                    );
                    if (!this.readonly) {
                        // Set list of operators according to field type
                        this.displayValue = this.value;
                        this.operators = this._getOperatorsFromType(selectedField.type, selectedField.name);
                        if (_.contains(["child_of", "parent_of", "like", "not like", "=like", "=ilike"], this.operator)) {
                            // In case user entered manually or from demo data
                            this.operators[this.operator] = operator_mapping[this.operator];
                        } else if (!this.operators[this.operator]) {
                            // In case the domain uses an unsupported operator for the
                            // field type
                            this.operators[this.operator] = "?";
                        }
                        // Set list of values according to field type

                        this.selectionChoices = null;
                        if (selectedField.type === "boolean") {
                            this.selectionChoices = [["1", _t("set (true)")], ["0", _t("not set (false)")]];
                        } else if (selectedField.type === "selection") {
                            this.selectionChoices = selectedField.selection;
                        }
                        else if ((_.contains(['many2one', 'many2many', 'one2many'], selectedField.type) || selectedField.name == "id") && (_.contains(['in', 'not in'], this.operator))) {
                            var model_rel = selectedField.name == "id"? selectedField.model: selectedField.relation
                            // var def = this.get_rec(model_rel)
                            // var model_rel = selectedField.relation
                            this.selectionChoices = null
                            // this.recordReader.appendTo($("<div/>"))
                             
                            var self = this;
                            const ids = (this.value) ? this.value : [];
                            wDefs.push(this._rpc({
                                model: model_rel,
                                method: 'search_read',
                                kwargs: {
                                    domain: [['id', 'in', ids]],
                                    fields: ['id', 'display_name'],
                                },
                            }).then(function (data) {
                                self.value = [];
                                if(model_rel == 'res.users' && _.contains(ids,0)){
                                    self.tagsvalues.push([0, 'Environment User']);
                                    self.value.push(0);
                                }
                                if(model_rel == 'res.company' && _.contains(ids,0)){
                                    self.tagsvalues.push([0, 'Environment Company']);
                                    self.value.push(0);
                                }
                                _.each(data, function (rec, index) {
                                    self.tagsvalues.push([rec.id, rec.display_name]);
                                    // to remove invalid id which is not in records
                                    self.value.push(rec.id);
                                    
                                })
                            }));

                            wDefs.push(this.recordReader.appendTo($('<div/>')).then((function () {
                                this.displayValue = [];
                                // this.value = [];
                            }).bind(this)));
                        }
                        // Adapt display value and operator for rendering

                        try {
                            if (selectedField && !selectedField.relation && !_.isArray(this.value)) {
                                this.displayValue = field_utils.format[selectedField.type](this.value, selectedField);
                            }
                        } catch (err) {/**/ }
                        this.displayOperator = this.operator;
                        if (selectedField.type === "boolean") {
                            this.displayValue = this.value ? "1" : "0";
                        } else if ((this.operator === "!=" || this.operator === "=") && this.value === false) {
                            this.displayOperator = this.operator === "!=" ? "set" : "not set";
                        }
                        // TODO the value could be a m2o input, etc...
                        if (_.contains(["date", "datetime"], selectedField.type)) {
                            this.valueWidget = new (selectedField.type === "datetime" ? datepicker.DateTimeWidget : datepicker.DateWidget)(this);
                            wDefs.push(this.valueWidget.appendTo("<div/>").then((function () {
                                this.valueWidget.$el.addClass("o_domain_leaf_value_input");
                                this.valueWidget.setValue(moment(this.value));
                                this.valueWidget.on("datetime_changed", this, function () {
                                    this._changeValue(this.valueWidget.getValue());
                                });
                            }).bind(this)));
                        }
                        return Promise.all(wDefs);
                    }
                }).bind(this)));

                return Promise.all(defs);
        },
    })

    return TerabitsDomainSelectorah;
});