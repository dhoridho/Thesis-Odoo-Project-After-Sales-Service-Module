odoo.define(
  "simpily_access_management.pivot_renderer_patch",
  function (require) {
    "use strict";

    const { patch } = require("web.utils");
    const PivotRenderer = require("web.PivotRenderer");
    var rpc = require("web.rpc");

    patch(PivotRenderer, "PivotRendererHideFieldPatch", {
      async _updateTooltip() {
        await this._super(...arguments);
        const res = await rpc.query({
          model: "access.management",
          method: "get_hidden_field",
          args: ["", this?.props?.modelName],
        });
        this.props.selectionGroupBys = this.props.selectionGroupBys.filter(
          (ele) => !res.includes(ele.name)
        );
      },
    });
  }
);
