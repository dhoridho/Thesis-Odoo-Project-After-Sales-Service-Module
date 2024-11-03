odoo.define('droggol_mass_mailing_themes.snippet.options', function (require) {
'use strict';

var options = require('web_editor.snippets.options');
var core = require('web.core');
var qweb = core.qweb;
var MassMailingDialogs = require('droggol_mass_mailing_themes.dialogs');
var ProductSelectorDialog = MassMailingDialogs.ProductSelectorDialog;
var BlogSelectorDialog = MassMailingDialogs.BlogSelectorDialog;
var EventSelectorDialog = MassMailingDialogs.EventSelectorDialog;

options.registry.d_mass_mailing_theme_option_daddy = options.Class.extend({
    xmlDependencies: ['/droggol_mass_mailing_themes/static/src/xml/snippets_template.xml'],

    /**
    * @override
    */
    onBuilt: function () {
        var relatedApp = this.$target.data('relatedApp');
        this._openDialog(relatedApp, this.$target.data('template'));
    },
    manageBlock: function (previewMode, value, $opt) {
        var snippetParams = this.$target.attr('value');
        this.snippetParams = snippetParams ? JSON.parse(snippetParams) : false;
        if (this.snippetParams && _.has(this.snippetParams, 'relatedApp') && _.has(this.snippetParams, 'recordsIDs') && _.has(this.snippetParams, 'snippetTemplate')) {
            this._openDialog(this.snippetParams.relatedApp, this.snippetParams.snippetTemplate, this.snippetParams.recordsIDs);
        }
    },
    _openDialog: function (relatedApp, snippetTemplate, recordsIDs) {
        var relatedDialog = _.find(this._getRelatedDialog(), function (dialog, module) {
            return module === relatedApp;
        });
        var dialog = new relatedDialog(this, {relatedApp: relatedApp, recordsIDs: recordsIDs ? recordsIDs : false, snippetTemplate: snippetTemplate});
        dialog.on('d_mass_mailing_dialog_discard', this, function () {
            // remove if nothing to append
            if (!this.$target.children().length) {
                this.$target.remove();
            }
        });
        dialog.on('d_mass_mailing_dialog_save', this, function (ev) {
            if (ev.data.resIDs.length) {
                this.$target.attr('value', JSON.stringify({snippetTemplate: ev.data.snippetTemplate, relatedApp: ev.data.relatedApp, recordsIDs: ev.data.resIDs}));
                this._fetchAndAppend(ev.data);
            } else {
                this.$target.remove();
            }
        });
        dialog.open();
    },
    /**
    * @override
    */
    _getRelatedDialog: function () {
        return {
            'sale': ProductSelectorDialog,
            'website_blog': BlogSelectorDialog,
            'event': EventSelectorDialog,
        };
    },
    /**
    * @override
    */
    _fetchAndAppend: function (data) {
        var self = this;
        this._rpc({
            route: data.routeForItemDetail,
            params: data.routeParams,
        }).then(function (result) {
            var items = result.items;
            result['items'] = _.map(data.resIDs, function (id) {
                return _.findWhere(items, {id: id});
            });
            self.$target.empty().append(qweb.render('droggol_mass_mailing_themes.' + data.snippetTemplate, result));
        });
    },
});

});
