odoo.define("advanced_web_domain_widget.ModelRecordSelector", function (require) {
    "use strict";

    var core = require("web.core");
    var Widget = require("web.Widget");

    var _t = core._t;

    var TerabitsModelRecordSelector = Widget.extend({
        template: "TerabitsModelRecordSelector",
        events: {},
        editionEvents: {
            // Handle popover opening and closing 
            "click .o_record_selector_value": "_onFocusIn",
            "click .o_record_selector_close": "_onCloseClick",
            // Handle a direct change in the debug input
            "change input.o_field_selector_debug": "_onDebugInputChange",
            // Handle a change in the search input
            "keyup .o_field_selector_search > input": "_onSearchInputChange",
        },
        init: function (parent, model, chain, options, title) {
            this._super.apply(this, arguments);

            this.title = title;
            this.model = title == "ID"? parent.model: model;
            this.chain = chain;
            this.options = _.extend({
                order: 'string',
                readonly: true,
                filters: {},
                fields: null,
                filter: function () { return true; },
                followRelations: true,
                debugMode: false,
                showSearchInput: true,
            }, options || {});
            this.options.filters = _.extend({
                searchable: true,
            }, this.options.filters);

            if (typeof this.options.followRelations !== 'function') {
                this.options.followRelations = this.options.followRelations ?
                    function () { return true; } :
                    function () { return false; }; 
            }

            this.records = [];

            if (!this.options.readonly) {
                _.extend(this.events, this.editionEvents);
            }
        },

        /**
         * @see Widget.willStart()
         * @returns {Promise}
         */
        willStart: function () {
             
            return Promise.all([
                this._super.apply(this, arguments),
                this._prefill()
            ]);
        },
        /**
         * @see Widget.start
         * @returns {Promise}
         */
        start: function () {     
            this.$value = this.$(".o_record_selector_value");
            this.$popover = this.$(".o_record_selector_popover");
            this.$input = this.$popover.find(".o_record_selector_popover_footer > input");
            this.$searchInput = this.$popover.find(".o_field_selector_search > input");
            
            this._render();
            return this._super.apply(this, arguments);
        },
        /**
         * Saves a new field chain (array) and re-render.
         *
         * @param {string[]} chain - the new field chain
         * @returns {Promise} resolved once the re-rendering is finished
         */
        setChain: function (chain) {
            if (_.isEqual(chain, this.chain)) {
                return Promise.resolve();
            }

            this.chain = chain;
            return this._prefill().then(this._render.bind(this));
        },
        /**
         * Search the records based on selected fields relation
         *
         * @private
         * @param {string} model
         * @param {Object} filters @see ModelFieldSelector.init.options.filters
         * @returns {Object[]} a list of the model fields info, sorted by field
         *                     non-technical names
         */
        _getModelRecordsFromCache: function (model, filters) {
            var def = undefined
            if (!def) {
                 ;
                var def = this._rpc({
                    model: model,
                    method: 'get_widget_name',
                    kwargs: {
                        domain: [],
                        fields: ['id', 'display_name'],
                    },
                }).then((function (data) {
                    if (data) {
                        this.records = data
                    }
                    if(model == 'res.users'){
                        this.records.push({'id': 0, 'display_name': 'Environment User'})
                    }
                    if(model == 'res.company'){
                        this.records.push({'id': 0, 'display_name': 'Environment Company'})
                    }
                    // if(model == 'res.users'){
                    //     this.records.push({'id':0,'display_name':'Environment User'})
                    // } 

                }).bind(this));
            }
            return def.then((function (data) {
            }).bind(this));
        },
        _hidePopover: function () {
            if (!this._isOpen) return;

            this._isOpen = false;
            this.$popover.addClass('d-none');
        },
        /**
         * Prepares the popover by filling its resords according to the current fields relation.
         *
         * @private
         * @returns {Promise} resolved once the whole field chain has been
         *                     processed
         */
        _prefill: function () {
            this.records = [];
            return this._pushRecordData(this.model).then((function () {
            }).bind(this));
        },
        /**
         * Gets the records of a particular model and adds them to a 
         * popover page.
         *
         * @private
         * @param {string} model - the model name whose fields have to be fetched
         * @returns {Promise} resolved once the fields have been added
         */
        _pushRecordData: function (model) {
            var def;
            if (this.model === model) {
                def = this._getModelRecordsFromCache(model, this.options.filters);
            }
            return def.then((function (fields) {
                if(fields){
                    this.records.push(fields);
                }
            }).bind(this));
        },
        /**
         * Updates the rendering of the value. It also adapts the content of the popover.
         *
         * @private
         */
        _render: function () {
            var title = this.title;
            this.$(".o_record_selector_popover_header .o_field_selector_title").text(title);

            var lines = this.records;
            if (this.searchValue) {
                var matches = fuzzy.filter(this.searchValue, _.pluck(lines, 'display_name'));
                lines = _.map(_.pluck(matches, 'index'), function (i) {
                    return lines[i];
                });
            }
            this.$(".o_record_selector_page").replaceWith(core.qweb.render(this.template + ".page", {
                lines: lines,
                debug: this.options.debugMode,
            }));
        },

        /**
         * Shows the popover to select the field chain. This assumes that the
         * popover has finished its rendering (fully rendered widget or resolved
         * deferred of @see setChain). If already open, this does nothing.
         *
         * @private
         */
        _showPopover: function () {
            if (this._isOpen) return;

            this._isOpen = true;
            this.$popover.removeClass('d-none');
        },
        /**
         * Called when the widget is focused -> opens the popover
         */
        _onFocusIn: function () {
             
            clearTimeout(this._hidePopoverTimeout);

            this._showPopover();
        },
        /**
         * Called when the widget is blurred -> closes the popover
         */
        _onFocusOut: function () {
            this._hidePopoverTimeout = _.defer(this._hidePopover.bind(this));
        },
        /**
         * Called when the popover "cross" icon is clicked -> closes the popover
         */
        _onCloseClick: function () {
            this._hidePopover();
        },
        /**
         * Called when the debug input value is changed -> adapts the chain
         */
        _onDebugInputChange: function () {
            var userChainStr = this.$input.val();
            var userChain = userChainStr.split(".");
            if (!this.options.followRelations && userChain.length > 1) {
                this.do_warn(
                    _t("Relation not allowed"),
                    _t("You cannot follow relations for this field chain construction")
                );
                userChain = [userChain[0]];
            }
            this.setChain(userChain).then((function () {
                this.trigger_up("field_chain_changed", { chain: this.chain });
            }).bind(this));
        },
        /**
         * Called when the search input value is changed -> adapts the popover
         */
        _onSearchInputChange: function () {
            this.searchValue = this.$searchInput.val();
            this._render();
        },

    });

    return TerabitsModelRecordSelector;

});
