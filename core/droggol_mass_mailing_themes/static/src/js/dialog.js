odoo.define('droggol_mass_mailing_themes.dialogs', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var core = require('web.core');
var session = require('web.session');
var translationLoaded = false;  // Odoo editor does not load translation so, we load it manually

var _t = core._t;

/**
 * Extend Dialog class to handle save/cancel of edition components.
 */
var MassMailingDialog = Dialog.extend({
    routePath: '',
    routeForItemDetail: false,
    DialogTitleName: false,
    template: 'droggol_mass_mailing_themes.dialog',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/droggol_mass_mailing_themes/static/src/xml/dialog.xml']
    ),
    /**
     * @constructor
     */
    init: function (parent, options) {
        options = options || {};
        options ['title'] = this.DialogTitleName || 'Droggol';
        this.relatedApp = options.relatedApp || false;
        this.recordsIDs = options.recordsIDs || [];
        this.snippetTemplate = options.snippetTemplate;
        this._super(parent, _.extend({}, {
            size: 'medium',
            buttons: [
                {text: options.save_btn_text || _t("Choose"), close: true, classes: 'btn-primary', click: this._onMassMailDialogSave.bind(this)},
                {text: _t("Discard"), close: true, click: this._onMassMailDialogDiscard.bind(this)}
            ]
        }, options));
    },
    /**
    * @override
    */
    willStart: function () {
        const _super = this._super.bind(this, ...arguments);
        if (translationLoaded) {
            var sup = _super();
        } else {
            var sup = _t.database.load_translations(session, ['droggol_mass_mailing_themes']).then(() => {
                translationLoaded = true;
                return _super()
            });
        }
        var relatedApp = this.relatedApp;
        var self = this;
        var defs = [sup];
        if (!relatedApp) {
            return Promise.all(defs);
        }
        defs.push(this._rpc({
            route: '/droggol_mass_mailing_themes/get_module_state',
            params: {
                module_name: relatedApp,
            },
        }).then(function (res) {
            self.isModuleInstalled = res.is_installed;
            self.extraInfo = res.extra_info;
        }));
        if (this.recordsIDs.length && this.routeForItemDetail) {
            defs.push(this._rpc({
                route: this.routeForItemDetail,
                params: this._getRouteInitParams(),
            }).then(function (res) {
                self.records = res;
            }));
        }
        return Promise.all(defs);
    },
    /**
    * @override
    */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        if (!this.isModuleInstalled) {
            this.$el.empty();
            var $alert = $('<div/>', {
                class: 'alert alert-warning',
                text: "To use this snippet you needs to install '" + this.relatedApp + "' module.",
            });
            $alert.appendTo(this.$el);
            this.$footer.find('.btn-primary').addClass('d-none');
        } else {
            this.$('.d-select2-input').select2({
                width: "100%",
                tokenSeparators: [",", " ", "_"],
                maximumInputLength: 35,
                minimumInputLength: 3,
                multiple: true,
                // Default tags value
                initSelection: function (element, callback) {
                    var data = _.map(self.recordsIDs, function (recordsID) {
                        var rec = _.findWhere(self.records.items, {id: recordsID});
                        return {'id': rec.id, 'text': rec.name};
                    });
                    element.val('');
                    callback(data);
                },
                ajax: {
                    url: this.routePath,
                    dataType: 'json',
                    data: function (term) {
                        var data = self._getTermParam();
                        data.term = term;
                        return data;
                    },
                    results: function (data) {
                        return self._processData(data);
                    },
                },
                formatResult: function (result) {
                    return self._getFormattedResult(result);
                },
            });
            this.$('.d-select2-input').select2('container').find('ul.select2-choices').sortable({
                containment: 'parent',
                start: function () {
                    self.$('.d-select2-input').select2('onSortStart');
                },
                update: function () {
                    self.$('.d-select2-input').select2('onSortEnd');
                }
            });
        }
        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _getCurrentData: function () {
        return {
            routeForItemDetail: this.routeForItemDetail,
            routeParams: this._getRouteParams(),
            resIDs: this._getSelect2Ids(),
            relatedApp: this.relatedApp,
            snippetTemplate: this.snippetTemplate
        };
    },
    _getSelect2Ids: function () {
         // compact to avoid false NaN values
        return _.compact(_.map(this.$('[name="selection"]').val().split(","), function (p) {
            return parseInt(p);
        }));
    },
    _getRouteInitParams: function () {
        return {
            'domain': [['id', 'in', this.recordsIDs]],
        };
    },
    /**
      * @private
      */
    _getRouteParams: function () {
        return {
            'domain': [['id', 'in', this._getSelect2Ids()]],
        };
    },
    /**
     * @private
     */
    _getFormattedResult: function () {
        return '';
    },
    /**
     * @private
     */
    _processData: function () {
        return {};
    },
    /**
     * @private
     */
    _getTermParam: function () {
        return {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    _onMassMailDialogDiscard: function () {
        this.trigger_up('d_mass_mailing_dialog_discard');
    },
    /**
     * @private
     */
    _onMassMailDialogSave: function () {
        this.trigger_up('d_mass_mailing_dialog_save', this._getCurrentData());
    },
});

var ProductSelectorDialog = MassMailingDialog.extend({
    template: 'droggol_mass_mailing_themes.dialog_products',
    routePath: '/droggol_mass_mailing_themes/get_product_by_name',
    routeForItemDetail: '/droggol_mass_mailing_themes/get_products_info',
    DialogTitleName: _t("Select Products"),

    /**
    * @override
    */
    _getFormattedResult: function (result) {
        return '<div class="media border-bottom">' +
                    '<img style="width: 100px;height: auto;" class="img mr-3" src=/web/image/product.template/' + result.id + '/image_256/>' +
                    '<div class="media-body border-left px-2">' +
                        '<p class="font-weight-bold mt-1 mb-1">' + _.escape(result.text) + '</p>' +
                        '<p class="mt-1">' + result.price + '</p>' +
                    '</div>' +
                '</div>';
    },
    /**
    * @override
    */
    _processData: function (data) {
        var ret = [];
        _.each(data, function (x) {
            ret.push({
                id: x.id,
                text: x.display_name,
                price: x.price,
            });
        });
        return {results: ret};
    },
    /**
    * @override
    */
    _getTermParam: function () {
        var termparams = {
            pricelist_id: parseInt($("[name='pricelist']").val()) || false,
        };
        if (this.$('#only_published').length) {
            termparams['only_published'] = this.$('#only_published').prop('checked') ? 'published' : 'all';
        }
        return termparams;
    },
    /**
    * @override
    */
    _getRouteParams: function () {
        var supObj = this._super.apply(this, arguments);
        supObj.pricelist_id = parseInt($("[name='pricelist']").val()) || false;
        return supObj;
    }
});

var BlogSelectorDialog = MassMailingDialog.extend({
    routePath: '/droggol_mass_mailing_themes/get_blog_by_name',
    routeForItemDetail: '/droggol_mass_mailing_themes/get_blogs_info',
    DialogTitleName: _t("Select Blogs"),

    /**
    * @override
    */
    _getFormattedResult: function (result) {
        return '<div class="media border-bottom">' +
                    '<img class="img mr-3" style="width: 70px;height: 70px;object-fit: cover;" src=' + result.blog_img + '>' +
                    '<div class="media-body border-left px-2">' +
                        '<p class="font-weight-bold mt-1 mb-1">' + _.escape(result.text) + '</p>' +
                        '<p class="mt-2">By: ' + _.escape(result.author_name) + '</p>' +
                    '</div>' +
                '</div>';
    },
    /**
    * @override
    */
    _processData: function (data) {
        var ret = [];
        _.each(data, function (x) {
            ret.push({
                id: x.id,
                text: x.name,
                author_name: x.author_name,
                blog_img: x.blog_img,
            });
        });
        return {results: ret};
    },
});

var EventSelectorDialog = MassMailingDialog.extend({
    routePath: '/droggol_mass_mailing_themes/get_event_by_name',
    routeForItemDetail: '/droggol_mass_mailing_themes/get_events_info',
    DialogTitleName: _t("Select Events"),

    /**
    * @override
    */
    _getFormattedResult: function (result) {
        return '<div class="media">' +
                    '<div class="media-body px-2">' +
                        '<p class="font-weight-bold mt-1 mb-1">' + _.escape(result.text) + '</p>' +
                        '<p class="mt-1 mb-1">By: ' + _.escape(result.organizer_name) + '</p>' +
                        '<small><i class="fa fa-clock-o"/> ' + _.escape(result.date_begin) + ' to ' + _.escape(result.date_end) + '</small>' +
                    '</div>' +
                '</div>';
    },
    /**
    * @override
    */
    _processData: function (data) {
        var ret = [];
        _.each(data, function (x) {
            ret.push({
                id: x.id,
                text: x.name,
                organizer_name: x.organizer_name,
                date_begin: x.date_begin,
                date_end: x.date_end,
            });
        });
        return {results: ret};
    },
});

return {
    'MassMailingDialog': MassMailingDialog,
    'ProductSelectorDialog': ProductSelectorDialog,
    'BlogSelectorDialog': BlogSelectorDialog,
    'EventSelectorDialog': EventSelectorDialog,
};
});
