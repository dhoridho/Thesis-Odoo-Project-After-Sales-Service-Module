odoo.define('acrux_whatsapp_crm.crm_lead', function(require) {
"use strict";
var session = require('web.session');
var FormView = require('acrux_chat.form_view');
var CrmLeadForm = FormView.extend({
    init: function(parent, options) {
        if (options) {
            options.model = 'crm.lead';
            options.record = options.crm_lead;
        }
        this._super.apply(this, arguments);

        this.parent = parent;
        _.defaults(this.context, {
            default_team_id: this.parent.selected_conversation.team_id[0],
            default_phone: this.parent.selected_conversation.number_format,
            default_mobile: this.parent.selected_conversation.number_format,
            default_name: 'Whatsapp: ' + this.parent.selected_conversation.name,
            default_contact_name: this.parent.selected_conversation.name,
            default_conversation_id: this.parent.selected_conversation.id,
            default_user_id: session.uid,
        });
    },
    start: function() {
        return this._super().then(() => this.parent.product_search.minimize());
    },
    recordChange: function(crm_lead_id) {
        return $.when(
            this._super(crm_lead_id),
            this._rpc({
                model: this.parent.model,
                method: 'save_crm_lead',
                args: [[this.parent.selected_conversation.id], crm_lead_id]
            }).then(result => {
                this.parent.selected_conversation.crm_lead_id = result;
                this.record = result;
            })
        );
    },

});

return CrmLeadForm;
});
odoo.define('acrux_whatsapp_crm.conversation', function(require) {
"use strict";
var Conversation = require('acrux_chat.conversation');
Conversation.include({
    init: function(parent, options) {
        this._super.apply(this, arguments);

        this.crm_lead_id = this.options.crm_lead_id || [false, ''];
    },
});
});
odoo.define('acrux_whatsapp_crm.chat_classes', function(require) {
"use strict";
var chat = require('acrux_chat.chat_classes');
return _.extend(chat, {
    CrmLeadForm: require('acrux_whatsapp_crm.crm_lead'),
});
});
odoo.define('acrux_whatsapp_crm.acrux_chat', function(require) {
"use strict";
var chat = require('acrux_chat.chat_classes');
var AcruxChatAction = require('acrux_chat.acrux_chat').AcruxChatAction
AcruxChatAction.include({
    events: _.extend({}, AcruxChatAction.prototype.events, {
        'click li#tab_crm_lead': 'tabCrmLead',
    }),
    _initRender: function() {
        return this._super().then(() => {
            this.$tab_content_lead = this.$('div#tab_content_crm_lead > div.o_group');
        });
    },
    tabCrmLead: function(event) {
        if (!$(event.currentTarget).hasClass('active')
            && this.selected_conversation) {
            if (this.selected_conversation.status == 'current') {
                let lead_id = this.selected_conversation.crm_lead_id;
                if (this.crm_lead_form) {
                    // podria evitarse la recarga innecesaria del formulario
                    // pero quité el código, por ahora que se recargue siempre
                    this.crm_lead_form.destroy();
                    this.crm_lead_form = null;
                }
                if (!this.crm_lead_form) {
                    let options = {
                        context: this.action.context,
                        crm_lead: lead_id,
                        action_manager: this.action_manager,
                    }
                    this.crm_lead_form = new chat.CrmLeadForm(this, options)
                    this.crm_lead_form.appendTo(this.$tab_content_lead);
                }
            }
        }
    },
    tabsClear: function() {
        this._super();
        if (this.crm_lead_form) {
            this.crm_lead_form.destroy();
            this.crm_lead_form = null;
        }
    },
});
});
