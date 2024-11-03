odoo.define("equip3_general_printout.ActionMenus", function (require) {

    const {patch} = require("web.utils");
    const ActionMenus = require("web.ActionMenus");

    patch(ActionMenus, "equip3_general_printout.ActionMenus", {
        async _setPrintItems(props) {
            var self = this;
            if (self.env !== undefined &&
                self.env.action !== undefined &&
                self.env.action.res_model !== undefined &&
                self.env.action.res_model === "purchase.order") {
                const printActions = props.items.print || [];
                var items = printActions.filter(k => k.res_model !== undefined && k.res_model === 'printout.editor');
                if (items.length === 0) {
                    printActions.push({
                        name: _("Printout Editor"),
                        type: "ir.actions.act_window",
                        res_model: 'printout.editor',
                        is_open_wizard: true,
                    });
                }
                const printItems = printActions.map(
                    action => ({ action, description: action.name, key: action.id })
                );
                return printItems;
            } else {
                return this._super.apply(this, arguments);
            }
        },
        _onItemSelected(ev) {
            ev.stopPropagation();
            var self = this;
            const {item} = ev.detail;
            if (item.action !== undefined &&
                item.action.is_open_wizard !== undefined &&
                item.action.is_open_wizard) {
                this.trigger('do-action', {
                    action: {
                        name: "Custom Print",
                        type: 'ir.actions.act_window',
                        res_model: 'printout.editor',
                        view_mode: 'form',
                        view_type: 'form',
                        views: [[false, 'form']],
                        target: 'new',
                        context: {'active_ids': this.props.activeIds}
                    },
                });
                // return this.env.services.rpc({
                //     model: "purchase.order",
                //     method: "open_print_editor",
                //     args: [{'active_ids': this.props.activeIds}]
                // }).then(function(result) {
                //     self.env.bus.trigger('do-action', {
                //         action: result
                //     });
                // });
            } else {
                return this._super.apply(this, arguments);
            }
        },
    });
});
