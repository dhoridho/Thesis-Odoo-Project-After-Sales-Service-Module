odoo.define("acrux_chat/static/src/js/file_uploader.js", (function(require) {
    "use strict";
    const FileUploader = require("mail/static/src/components/file_uploader/file_uploader.js"), framework = require("web.framework");
    return class extends FileUploader {
        constructor(...args) {
            super(...args);
        }
        async _performUpload(files) {
            for (const file of files) {
                const uploadingAttachment = this.env.models["mail.attachment"].find((attachment => attachment.isTemporary && attachment.filename === file.name));
                try {
                    const response = await this.env.browser.fetch("/web/binary/upload_attachment_chat", {
                        method: "POST",
                        body: this._createFormData(file),
                        signal: uploadingAttachment.uploadingAbortController.signal
                    });
                    let html = await response.text();
                    const template = document.createElement("template");
                    template.innerHTML = html.trim(), window.eval(template.content.firstChild.textContent);
                } catch (e) {
                    if ("AbortError" !== e.name) throw e;
                }
            }
        }
        async _onAttachmentUploaded(ev, ...filesData) {
            try {
                await super._onAttachmentUploaded(ev, ...filesData);
            } catch (e) {
                framework.unblockUI();
            }
            return Promise.resolve();
        }
    };
})), odoo.define("acrux_chat.ActionManager", (function(require) {
    "use strict";
    var ActionManager = require("web.ActionManager");
    return ActionManager.include({
        _executeAction: function(action, options) {
            if (action.context.is_acrux_chat_room && "inline" == action.target) {
                var controller = this.controllers[action.controllerID];
                this.actions[action.jsID] = action, action.action_ready = this._startController(controller).guardedCatch((() => {
                    this._removeAction(action.jsID);
                }));
            } else action.action_ready = this._super(action, options);
            return action.action_ready;
        }
    }), ActionManager;
})), odoo.define("acrux_chat.BasicController", (function(require) {
    "use strict";
    var BasicController = require("web.BasicController");
    return BasicController.include({
        _discardChanges: function(recordID, options) {
            return this._super(recordID, options).then((_x => {
                if (this.acrux_widget) {
                    let env = this.model.get(this.handle, {
                        env: !0
                    });
                    recordID || env.currentId || this.acrux_widget.discardChange();
                }
                return _x;
            }));
        },
        update: function(params, options) {
            return this._super(params, options).then((_x => {
                if (this.acrux_widget) {
                    let env = this.model.get(this.handle, {
                        env: !0
                    });
                    return this.acrux_widget.recordUpdated(env).then((() => _x));
                }
                return _x;
            }));
        },
        _pushState: function(state) {
            this.model.get(this.handle).getContext().is_acrux_chat_room || this._super(state);
        },
        saveRecord: function(recordID, options) {
            return this._super(recordID, options).then((_x => {
                if (this.acrux_init_conv) {
                    let env = this.model.get(this.handle, {
                        env: !0
                    });
                    this.acrux_init_conv(env.currentId);
                }
                return _x;
            }));
        }
    }), BasicController;
})), odoo.define("acrux_chat.form_view", (function(require) {
    "use strict";
    var Widget = require("web.Widget"), dom = require("web.dom");
    return Widget.extend({
        init: function(parent, options) {
            this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options),
            this.context = _.extend({
                is_acrux_chat_room: !0
            }, this.options.context), this.model = this.options.model, this.form_name = this.options.form_name,
            this.record = this.options.record, this.action_manager = this.options.action_manager,
            this.acrux_form_widget = null, this.action = {}, this.created_date = new Date;
        },
        start: function() {
            return this._super().then((() => this.do_action(this.getDoActionDict(), this.getOptions()).then((action => {
                this.action = action, this.action.controllers.form.then((r => {
                    this.acrux_form_widget = r.widget, this.acrux_form_widget.acrux_widget = this, this._showAcruxFormView();
                }));
            }))));
        },
        destroy: function() {
            return this.$el && this.action_manager._removeAction(this.action.jsID), this._super();
        },
        getDoActionDict: function() {
            return {
                type: "ir.actions.act_window",
                view_type: "form",
                view_mode: "form",
                res_model: this.model,
                views: [ [ this.form_name, "form" ] ],
                target: "inline",
                context: this.context,
                res_id: this.record[0],
                flags: this.getDoActionFlags()
            };
        },
        getDoActionFlags: function() {
            let flags = {
                withControlPanel: !1,
                footerToButtons: !1,
                hasSearchView: !1,
                hasSidebar: !1,
                mode: "edit",
                searchMenuTypes: !1
            };
            return this.record[0] && (flags.mode = "readonly"), flags;
        },
        getOptions: function() {
            return {
                replace_last_action: !1,
                pushState: !1,
                clear_breadcrumbs: !1
            };
        },
        _showAcruxFormView: function() {
            let $buttons = $("<div>");
            return dom.append(this.$el, this.acrux_form_widget.$el, {
                in_DOM: !0,
                callbacks: [ {
                    widget: this
                }, {
                    widget: this.acrux_form_widget
                } ]
            }), this.acrux_form_widget.renderButtons($buttons), $buttons.find(".o_form_button_create").click((() => this._onCreate())),
            $buttons.find(".o_form_button_edit").click((() => this._onEdit())), this.$el.prepend($buttons.contents()),
            this.$el.children().first().css("padding", "5px"), this.$el.children().first().css("background", "white"),
            Promise.resolve();
        },
        on_attach_callback: function() {
            this.$el.css("height", "100%"), this.$el.children().first().css("position", "relative"),
            this.$el.children().first().css("height", "92%"), this.$el.children().first().css("overflow", "auto"),
            this._fix_attach();
        },
        _fix_attach: function() {
            this.$(".o_form_sheet").eq(0).css("margin", "0"), this.$(".o_form_sheet").eq(0).css("padding", "1em"),
            this.$(".o_form_sheet").children().first().css("margin", "0"), this.$(".o_FormRenderer_chatterContainer").hide();
        },
        recordUpdated: function(env) {
            return this._fix_attach(), env && env.currentId && this.record[0] != env.currentId ? this.recordChange(env.currentId) : Promise.resolve();
        },
        recordChange: function(record) {
            return Promise.resolve();
        },
        isExpired: function() {
            return new Date - this.created_date >= 108e5;
        },
        isSameRecord: function(record_id) {
            return this.record[0] == record_id;
        },
        _onCreate: function() {
            this.old_record = Array.from(this.record);
        },
        _onEdit: function() {
            this.old_record = null;
        },
        discardChange: function() {
            if (this.old_record) {
                let options = this.getDoActionFlags();
                options.currentId = this.old_record[0], options.ids = [ this.old_record[0] ], options.context = this.context,
                options.modelName = this.model, options.mode = "readonly", this.acrux_form_widget.reload(options),
                this.old_record = null;
            }
        }
    });
})), odoo.define("acrux_chat.user_status", (function(require) {
    "use strict";
    var Widget = require("web.Widget"), session = require("web.session");
    return Widget.extend({
        template: "acrux_chat_user_status",
        events: {
            "click label#chat_status_active": "changeStatus",
            "click label#chat_status_inactive": "changeStatus",
            "click .navbar-toggler": "showMobilePanel"
        },
        init: function(parent, options) {
            this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options),
            this.context = _.extend({}, this.options.context), this.acrux_chat_active = this.options.acrux_chat_active;
        },
        willStart: function() {
            return Promise.all([ this._super(), this.getUserStatus() ]);
        },
        start: function() {
            return this._super().then((() => this._initRender()));
        },
        _initRender: function() {
            return this.$lables_status = this.$("label#chat_status_active, label#chat_status_inactive"),
            this.acrux_chat_active ? this.$("label#chat_status_active").addClass("active") : this.$("label#chat_status_inactive").addClass("active"),
            Promise.resolve();
        },
        getUserStatus: function() {
            return this._rpc({
                model: "res.users",
                method: "read",
                args: [ [ session.uid ], [ "acrux_chat_active" ] ]
            }).then((result => {
                this.acrux_chat_active = result[0].acrux_chat_active;
            }));
        },
        changeStatus: function(event) {
            let toggle = !1;
            "chat_status_active" == $(event.target).prop("id") ? this.acrux_chat_active || (toggle = !0) : this.acrux_chat_active && (toggle = !0),
            toggle && (this.$lables_status.toggleClass("active"), this.acrux_chat_active = !this.acrux_chat_active,
            this._rpc({
                model: "res.users",
                method: "set_chat_active",
                args: [ [ session.uid ], {
                    acrux_chat_active: this.acrux_chat_active
                } ]
            }));
        },
        changeStatusNotify: function(data) {
            this.acrux_chat_active != data.status && this.$lables_status.toggleClass("active"),
            this.acrux_chat_active = data.status;
        },
        isActive: function() {
            return this.acrux_chat_active;
        },
        showMobilePanel: function(_event) {
            this.parent.selected_conversation && this.parent.showChatPanel();
        }
    });
})), odoo.define("acrux_chat.init_conversation", (function(require) {
    "use strict";
    var core = require("web.core"), Widget = require("web.Widget"), QWeb = core.qweb;
    return Widget.extend({
        template: "acrux_chat_init_conversation",
        events: {
            "click .o_button_conv_search": "searchConversation",
            "keypress .conv_search": "onKeypress",
            "click .o_button_create_conversation": "createConversation",
            "click .o_acrux_chat_conv_items > .o_conv_record": "selectConversation"
        },
        init: function(parent, options) {
            this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options),
            this.context = _.extend({
                is_acrux_chat_room: !0
            }, this.options.context), this.conv_list = this.options.conv_list || [];
        },
        start: function() {
            return this._super().then((() => this._initRender()));
        },
        _initRender: function() {
            return this.$input_search = this.$("input.conv_search"), this.$conv_items = this.$(".o_acrux_chat_conv_items"),
            Promise.resolve();
        },
        searchConversation: function() {
            let field, domain, model, val = this.$input_search.val();
            if (val && "" != val.trim()) return val = val.trim(), model = "acrux.chat.conversation",
            field = [ "id", "name", "number_format", "image_url", "connector_id", "border_color" ],
            domain = [ "|", "|", [ "name", "ilike", val ], [ "number_format", "ilike", val ], [ "number", "ilike", val ] ],
            this._rpc({
                model: "acrux.chat.conversation",
                method: "search_read",
                args: [ domain, field ]
            }).then((result => {
                result = this.postProcessorResult(result);
                let html = QWeb.render("acrux_chat_conv_list", {
                    conv_list: result
                });
                this.conv_list = result, this.$conv_items.html(html);
            }));
            this.empty();
        },
        postProcessorResult: function(result) {
            return result;
        },
        selectConversation: function(event) {
            let conversation_id = $(event.currentTarget).data("id");
            return this._rpc({
                model: this.parent.model,
                method: "init_and_notify",
                args: [ [ conversation_id ] ]
            });
        },
        onKeypress: function(event) {
            13 === event.which && $(event.currentTarget).hasClass("conv_search") && (event.preventDefault(),
            this.searchConversation());
        },
        empty: function() {
            this.$input_search.val(""), this.$conv_items.html(""), this.conv_list = [];
        },
        createConversation: function(_event) {
            let action = {
                name : "Conversation",
                type: "ir.actions.act_window",
                view_type: "form",
                view_mode: "form",
                res_model: this.parent.model,
                views: [ [ !1, "form" ] ],
                target: "new",
                context: this.context
            };
            this.do_action(action).then((action => {
                action.controllers.form.then((result => {
                    result.widget.acrux_init_conv = recordID => {
                        recordID && (result.dialog.close(), this._rpc({
                            model: this.parent.model,
                            method: "init_and_notify",
                            args: [ [ recordID ] ]
                        }));
                    };
                }));
            }));
        }
    });
})), odoo.define("acrux_chat.product_search", (function(require) {
    "use strict";
    var core = require("web.core"), Widget = require("web.Widget"), field_utils = require("web.field_utils"), QWeb = core.qweb;
    return Widget.extend({
        template: "acrux_chat_product_search",
        events: {
            "click .o_button_product_search": "searchProduct",
            "keypress .product_search": "onKeypress"
        },
        init: function(parent, options) {
            this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options),
            this.context = _.extend({}, this.options.context), this.product_list = this.options.product_list || [];
        },
        start: function() {
            return this._super().then((() => this._initRender()));
        },
        _initRender: function() {
            return this.$el.resizable({
                handles: "s"
            }), this.$input_search_product = this.$("input.product_search"), this.$input_search_product.focus((() => this.maximize())),
            this.$product_items = this.$(".o_acrux_chat_product_items"), this.makeProductDragAndDrop(),
            Promise.resolve();
        },
        makeProductDragAndDrop: function() {
            this.parent.$chat_message.droppable({
                drop: (_event, ui) => {
                    if (this.parent.selected_conversation && "current" == this.parent.selected_conversation.status) {
                        let product = this.find(ui.draggable.data("id"));
                        product && this.sendProduct(product);
                    }
                },
                accept: ".o_product_record",
                activeClass: "drop-active",
                hoverClass: "drop-hover"
            });
        },
        sendProduct: function(product) {
            let options = {
                from_me: !0,
                ttype: "product",
                res_model: "product.product",
                res_id: product.id,
                res_model_obj: product
            };
            return this.parent.selected_conversation.createMessage(options);
        },
        searchProduct: function() {
            let val = this.$input_search_product.val() || "";
            return this._rpc({
                model: this.parent.model,
                method: "search_product",
                args: [ val.trim() ]
            }).then((result => {
                result.forEach((x => {
                    x.list_price = this.parent.format_monetary(x.list_price), x.write_date = field_utils.parse.datetime(x.write_date),
                    x.unique_hash_image = field_utils.format.datetime(x.write_date).replace(/[^0-9]/g, "");
                }));
                let html = QWeb.render("acrux_chat_product_list", {
                    product_list: result
                });
                this.product_list = result, this.$product_items.html(html), this.$product_items.children().draggable({
                    revert: !0,
                    revertDuration: 0,
                    containment: this.parent.$el,
                    appendTo: this.parent.$el,
                    helper: "clone"
                });
            }));
        },
        onKeypress: function(event) {
            13 === event.which && $(event.currentTarget).hasClass("product_search") && (event.preventDefault(),
            this.searchProduct());
        },
        minimize: function() {
            this.$el.animate({
                height: "45px"
            }, 500);
        },
        maximize: function() {
            "45px" == this.$el.css("height") && this.$el.animate({
                height: "30%"
            }, 500);
        },
        find: function(product_id) {
            return this.product_list.find((x => x.id == product_id));
        }
    });
})), odoo.define("acrux_chat.message", (function(require) {
    "use strict";
    const components = {
        Attachment: require("mail/static/src/components/attachment/attachment.js")
    }, {Component} = owl;
    var core = require("web.core"), Widget = require("web.Widget"), QWeb = core.qweb, _t = core._t;
    return Widget.extend({
        template: "acrux_chat_message",
        init: function(parent, options) {
            if (this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options),
            this.context = _.extend({}, this.options.context), this.id = this.options.id, this.ttype = this.options.ttype || "text",
            this.from_me = this.options.from_me || !1, this.text = this.options.text || "",
            this.res_model = this.options.res_model || !1, this.res_id = this.options.res_id || !1,
            this.error_msg = this.options.error_msg || !1, this.res_model_obj = this.options.res_model_obj,
            this.date_message = new Date(this.options.date_message) || new Date, !this.date_message || this.date_message instanceof Date || (this.date_message = new Date(this.date_message)),
            "location" == this.ttype && this.createLocationObj(), [ "image", "video", "file" ].includes(this.ttype) && this.res_model_obj && !(this.res_model_obj instanceof components.Attachment)) {
                let props = {
                    isDownloadable: !0,
                    isEditable: !1,
                    showExtension: !0,
                    showFilename: !0,
                    attachmentLocalId: this.res_model_obj.localId
                };
                this.res_model_obj = new components.Attachment(null, props);
            }
        },
        willStart: function() {
            let def = !1;
            if (this.res_model && !this.res_model_obj) {
                let field_read;
                field_read = "product.product" == this.res_model ? [ "id", "name", "list_price", "qty_available", "uom_id" ] : [ "id", "checksum", "mimetype", "name", "url" ],
                def = this._rpc({
                    model: this.res_model,
                    method: "read",
                    args: [ this.res_id, field_read ]
                }).then((result => {
                    if (result.length > 0) if (this.res_model_obj = result[0], "product.product" == this.res_model) {
                        let price = this.res_model_obj.list_price;
                        price = this.parent.parent.format_monetary(price), this.res_model_obj.list_price = price;
                    } else {
                        let filename = this.res_model_obj.name || _t("unnamed");
                        if (this.res_model_obj.filename = filename, "audio" != this.ttype) {
                            let tmp, Attachment = Component.env.models["mail.attachment"];
                            tmp = Attachment.findFromIdentifyingData(this.res_model_obj), tmp || (tmp = Attachment.insert(this.res_model_obj));
                            let props = {
                                isDownloadable: !0,
                                isEditable: !1,
                                showExtension: !0,
                                showFilename: !0,
                                attachmentLocalId: tmp.localId
                            };
                            this.res_model_obj = new components.Attachment(null, props);
                        }
                    } else "product.product" == this.res_model ? this.res_model_obj = {
                        name: _t("Product not found")
                    } : (this.res_model_obj = {
                        name: _t("File not found")
                    }, this.res_model_obj.filename = this.res_model_obj.name);
                }));
            }
            return Promise.all([ this._super(), def ]);
        },
        start: function() {
            return this._super().then((() => this._initRender()));
        },
        _initRender: function() {
            let def = !1;
            return this.res_model_obj && ("product.product" == this.res_model ? this.$(".oe_product_details > ul > li").last().remove() : (this.$("div.caption").html(""),
            "audio" == this.ttype && (def = this.audioController()), this.res_model_obj instanceof components.Attachment && (def = this.res_model_obj.mount(this.$("div#o_attach_zone")[0])))),
            Promise.all([ def ]);
        },
        destroy: function() {
            return this.$audio && (this.$audio.off("loadeddata"), this.$audio.off("error"),
            this.$audio.off("timeupdate"), this.$audio.off("ended")), this._super.apply(this, arguments);
        },
        export_to_json: function() {
            let out = {};
            return out.text = this.text, out.from_me = this.from_me, out.ttype = this.ttype,
            out.contact_id = this.parent.id, out.res_model = this.res_model, out.res_id = this.res_id,
            out;
        },
        setErrorMessage: function(error_msg) {
            this.error_msg = error_msg;
        },
        getDateTmpl: function() {
            return QWeb.render("acrux_chat_chat_date", {
                widget: this
            });
        },
        getDate: function() {
            return this.date_message.toLocaleString().split(" ")[0];
        },
        getHour: function() {
            let out = this.date_message.toLocaleString();
            return out.includes(",") ? (out = out.split(", ")[1], out = out.replace(/:\d\d /, " ")) : (out = out.split(" ")[1],
            out = out.replace(/:\d\d /, " "), out = out.replace(/:\d\d$/, "")), out;
        },
        audioController: function() {
            let resolve, def = new Promise((r => resolve = r));
            this.$player = this.$(".o_acrux_audio_player"), this.$audio = this.$player.prev(),
            this.audio_obj = this.$audio[0], this.$progress = this.$player.find(".progress"),
            this.$time = this.$player.find(".time"), this.$progress_play = this.$progress.find(".playback"),
            this.$player_play = this.$player.find(".play > a"), this.$player.addClass("o_hidden"),
            this.$player_play.click((event => {
                event.preventDefault(), this.audio_obj.paused ? (this.audio_obj.play(), $(event.target).html("⏸️")) : (this.audio_obj.pause(),
                $(event.target).html("▶"));
            }));
            let calculateTime = num => {
                let zero = x => x < 10 ? "0" + x : x, minutes = Math.floor(num / 60), seconds = Math.round(num) % 60, hours = Math.floor(minutes / 60), out = "";
                return minutes = Math.round(minutes) % 60, hours && (out = zero(hours) + ":"), out += zero(minutes) + ":" + zero(seconds),
                out;
            };
            return this.$audio.on("loadeddata", (_event => {
                this.$player.removeClass("o_hidden"), this.$time.html(calculateTime(this.audio_obj.duration)),
                resolve();
            })), this.$audio.on("error", (_event => {
                this.$player.html(_t("Audio not found")), this.$player.removeClass("o_acrux_audio_player"),
                this.$player.removeClass("o_hidden"), resolve();
            })), this.$audio.on("timeupdate", (event => {
                let audio = event.target, percentage = 100 * audio.currentTime / audio.duration;
                percentage = Math.round(percentage), this.$progress_play.width(percentage + "%"),
                this.$time.html(calculateTime(audio.currentTime));
            })), this.$audio.on("ended", (_event => {
                this.audio_obj.currentTime = 0, this.$player_play.html("▶"), this.$time.html(calculateTime(this.audio_obj.duration));
            })), this.$progress.click((event => {
                let relative_position, percentage;
                relative_position = event.pageX - this.$progress.offset().left, percentage = relative_position / this.$progress.outerWidth(),
                this.audio_obj.currentTime = this.audio_obj.duration * percentage;
            })), def;
        },
        createLocationObj: function() {
            if (this.text) try {
                let text = this.text.split("\n"), loc_obj = {};
                loc_obj.name = text[0].trim(), loc_obj.address = text[1].trim(), loc_obj.coordinate = text[2].trim(),
                text = loc_obj.coordinate.replace("(", "").replace(")", ""), text = text.split(","),
                loc_obj.coordinate = {
                    x: text[0].trim(),
                    y: text[1].trim()
                }, loc_obj.map_url = "https://maps.google.com/maps/search/", loc_obj.map_url += `${loc_obj.name}/@${loc_obj.coordinate.x},${loc_obj.coordinate.y},17z?hl=es`,
                loc_obj.map_url = encodeURI(loc_obj.map_url), this.location = loc_obj;
            } catch (err) {
                console.log("error location"), console.log(err);
            }
        }
    });
})), odoo.define("acrux_chat.default_answer", (function(require) {
    "use strict";
    return require("web.Widget").extend({
        template: "acrux_chat_default_answer",
        events: {
            "click .o_acrux_chat_default_answer_send": "sendAnswer"
        },
        init: function(parent, options) {
            this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options),
            this.context = _.extend({}, this.options.context), this.name = this.options.name || "",
            this.sequence = this.options.sequence || "", this.id = this.options.id || "", this.text = this.options.text || "",
            this.ttype = this.options.ttype || "", this.res_model = this.options.res_model,
            this.res_id = this.options.res_id;
        },
        sendAnswer: function(_event) {
            if (this.parent.selected_conversation && "current" == this.parent.selected_conversation.status) {
                let text;
                text = this.text && "" != this.text ? this.text : this.name;
                let options = {
                    from_me: !0,
                    text,
                    ttype: this.ttype,
                    res_model: this.res_model,
                    res_id: this.res_id
                };
                this.parent.selected_conversation.createMessage(options);
            }
        }
    });
})), odoo.define("acrux_chat.conversation", (function(require) {
    "use strict";
    var core = require("web.core"), Widget = require("web.Widget"), Message = require("acrux_chat.message"), session = require("web.session"), framework = require("web.framework"), QWeb = core.qweb;
    return Widget.extend({
        template: "acrux_chat_conversation",
        init: function(parent, options) {
            this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options),
            this.context = _.extend({}, this.options.context), this.id = this.options.id || 0,
            console.log(this.context)
            this.name = this.options.name || "", this.number_format = this.options.number_format,
            this.status = this.options.status || "new", this.border_color = this.options.border_color || "#FFFFFF",
            this.image_url = this.options.image_url, this.count_new_msg = 0, this.team_id = this.options.team_id || [ !1, "" ],
            this.session = session, this.setMessages(this.options.messages);
        },
        start: function() {
            return this._super().then((() => this._initRender()));
        },
        _initRender: function() {
            return this.$number_new_msg = this.$(".o_number_new_msg"), this.$(".acrux_image_perfil").css("box-shadow", "0 0 7px " + this.border_color),
            this.$number_new_msg.addClass("o_hidden"), Promise.resolve();
        },
        destroy: function() {
            return this.parent.selected_conversation && this == this.parent.selected_conversation && (this.parent.$chat_title.html(""),
            this.parent.$chat_message.html("")), this._super.apply(this, arguments);
        },
        setMessages: function(messages) {
            this.messages_ids = new Set, this.messages && this.messages.forEach((x => x.destroy())),
            messages && messages instanceof Array && messages.length > 0 ? messages[0] instanceof Message ? (this.messages = messages,
            this.messages.forEach((x => this.messages_ids.add(x.id)))) : (this.messages = [],
            this.addClientMessage(messages)) : this.messages = [];
        },
        addCompanyMessage: function(msg) {
            this.messages_ids.has(msg.id) || (this.messages.length ? this.messages[this.messages.length - 1].getDate() != msg.getDate() && this.parent.$chat_message.append(msg.getDateTmpl()) : this.parent.$chat_message.append(msg.getDateTmpl()),
            this.messages.push(msg), msg.appendTo(this.parent.$chat_message).then((() => {
                this.needScroll() && this.scrollConversation();
            })));
        },
        showMessages: function() {
            let def, conv_title = QWeb.render("acrux_chat_conv_title", {
                conversation: this
            }), $el = this.parent.$chat_message;
            return this.parent.$chat_title.html(conv_title), $el.empty(), def = this.messages.length ? this._syncLoop(0, this.messages, -1, $el).then((() => {
                setTimeout((() => this.scrollConversation()), 200);
            })) : Promise.resolve(), this.$el.addClass("active"), "current" == this.status && this.messageSeen(),
            def;
        },
        addClientMessage: function(messages) {
            let def, show = this.parent.selected_conversation && this.parent.selected_conversation.id == this.id, $el = this.parent.$chat_message;
            return messages && (messages = (messages = messages.map((r => new Message(this, r)))).filter((r => !this.messages_ids.has(r.id))),
            show && messages.length && (def = this._syncLoop(0, messages, this.messages.length - 1, $el).then((() => {
                this.needScroll() && this.scrollConversation();
            })), document.hidden || this.messageSeen()), messages.forEach((r => {
                this.messages.push(r), this.messages_ids.add(r.id);
            }))), def || Promise.resolve();
        },
        addExtraClientMessage: function(messages) {
            let show = this.parent.selected_conversation && this.parent.selected_conversation.id == this.id, def = Promise.resolve(), $el = $("<div>");
            return messages && (messages = (messages = messages.map((r => new Message(this, r)))).filter((r => !this.messages_ids.has(r.id))),
            show && (framework.blockUI(), def = this._syncLoop(0, messages, -1, $el).then((() => {
                if (messages.length) {
                    let first_msg, last_msg = messages[messages.length - 1];
                    this.messages.length && (first_msg = this.messages[0], first_msg.getDate() == last_msg.getDate() && first_msg.$el.prev().hasClass("o_acrux_date") && first_msg.$el.prev().remove()),
                    this.parent.$chat_message.prepend($el.contents()), last_msg.$el[0].scrollIntoView();
                }
            })).finally((() => framework.unblockUI()))), messages.length && def.then((() => {
                messages.forEach((r => this.messages_ids.add(r.id))), this.messages = messages.concat(this.messages);
            }))), def;
        },
        _syncLoop: function(i, arr, last_index, $el) {
            let out;
            return out = i < arr.length ? this._syncShow(i, arr, last_index, $el).then((() => this._syncLoop(i + 1, arr, last_index, $el))) : Promise.resolve(),
            out;
        },
        _syncShow: function(i, arr, last_index, $el) {
            let out_def, r = arr[i];
            return i ? (r.getDate() != arr[i - 1].getDate() && $el.append(r.getDateTmpl()),
            out_def = r.appendTo($el)) : (last_index >= 0 ? this.messages[last_index].getDate() != r.getDate() && $el.append(r.getDateTmpl()) : $el.append(r.getDateTmpl()),
            out_def = r.appendTo($el)), out_def;
        },
        setMessageError: function(messages) {
            let out = [];
            if (messages && this.messages.length) {
                let show = this.parent.selected_conversation && this.parent.selected_conversation.id == this.id;
                messages.forEach((r => {
                    let msg = this.messages.find((x => x.id == r.id));
                    msg && (out.push(msg), msg.setErrorMessage(r.error_msg), show && msg.renderElement());
                }));
            }
            return out;
        },
        syncMoreMessage: function() {
            this.messages.length >= 50 && this._rpc({
                model: "acrux.chat.conversation",
                method: "build_dict",
                args: [ [ this.id ], 50, this.messages.length ]
            }).then((result => {
                this.addExtraClientMessage(result[0].messages);
            }));
        },
        needScroll: function() {
            return this.calculateScrollPosition() >= .75;
        },
        calculateScrollPosition: function() {
            let scroll_postion = this.parent.$chat_message.height();
            return scroll_postion += this.parent.$chat_message.scrollTop(), scroll_postion / this.parent.$chat_message[0].scrollHeight;
        },
        scrollConversation: function() {
            if (this.parent.$chat_message.children().length) {
                let element = this.parent.$chat_message.children().last();
                element.children().length && (element = element.children().last()), element[0].scrollIntoView();
            }
        },
        incressNewMessage: function() {
            this.count_new_msg += 1, 1 == this.count_new_msg && this.$number_new_msg.removeClass("o_hidden"),
            this.$number_new_msg.text(this.count_new_msg);
        },
        createMessage: function(options) {
            let msg = new Message(this, options), json_data = msg.export_to_json();
            if (options.is_direct == true) { json_data.is_direct = true; } else { json_data.is_direct = false; }
            return options.custom_field && (json_data[options.custom_field] = !0), new Promise(((resolve, reject) => {
                this._rpc({
                    model: "acrux.chat.conversation",
                    method: "send_message",
                    args: [ [ this.id ], json_data ]
                }).then((result => {
                    msg.id = result.id, msg.date_message = new Date(result.date_message), msg.res_id = result.res_id,
                    msg.res_model = result.res_model, this.addCompanyMessage(msg), resolve(msg);
                }), (result => {
                    reject(result);
                }));
            }));
        },
        messageSeen: function() {
            this.count_new_msg > 0 && this._rpc({
                model: "acrux.chat.conversation",
                method: "conversation_send_read",
                args: [ [ this.id ] ]
            }, {
                shadow: !0
            }), this.count_new_msg = 0, this.$number_new_msg.addClass("o_hidden");
        }
    });
})), odoo.define("acrux_chat.toolbox", (function(require) {
    "use strict";
    const {FieldCommand} = require("mail/static/src/model/model_field_command.js"), components = {
        Attachment: require("mail/static/src/components/attachment/attachment.js"),
        FileUploader: require("acrux_chat/static/src/js/file_uploader.js")
    }, {Component} = owl, {useRef, useState} = owl.hooks;
    var Widget = require("web.Widget"), framework = require("web.framework");
    class ToolBoxComponent extends Component {
        constructor(...args) {
            super(...args), this.attachment = useState({
                value: null
            }), this._parent_widget = this.props.parent_widget, this._fileUploaderRef = useRef("fileUploader");
        }
        get attachments() {
            let out = [];
            return this.attachment.value && out.push(this.attachment.value.localId), out;
        }
        get newAttachmentExtraData() {
            return {
                composers: new FieldCommand(((_field, record, _options) => {
                    parseInt(record.localId.replace("mail.attachment_", "")) < 0 ? framework.blockUI() : framework.unblockUI();
                }))
            };
        }
        openBrowserFileUploader() {
            this._fileUploaderRef.comp.openBrowserFileUploader(), this._parent_widget.$input.focus();
        }
        _onAttachmentCreated(ev) {
            this.attachment.value = ev.detail.attachment, this._parent_widget.enableDisplabeAttachBtn();
        }
        _onAttachmentRemoved(ev) {
            this.attachment.value = null, this._parent_widget.enableDisplabeAttachBtn();
        }
    }
    var ToolBox = Widget.extend({
        template: "acrux_chat_toolbox",
        events: {
            "click .o_chat_toolbox_send": "sendMessage",
            "keypress .o_chat_toolbox_text_field": "onKeypress",
            "click .o_chat_button_add_attachment": "clickAddAttachment",
            "click .o_attachment_delete": "deleteAttachment",
            "change input.o_input_file": "changeAttachment",
            "click .o_attachment_view": "viewAttachment"
        },
        init: function(parent, options) {
            this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options),
            this.context = _.extend({}, this.options.context);
        },
        start: function() {
            return this._super().then((() => this._initRender()));
        },
        _initRender: function() {
            let classes = ".o_chat_toolbox_done, ";
            return classes += ".o_chat_toolbox_container, .o_chat_toolbox_send", this.$input = this.$(".o_chat_toolbox_text_field"),
            this.$attachment_button = this.$(".o_chat_button_add_attachment"), this.$attachment_zone = this.$(".o_toolbox_file_uploader"),
            this.$other_inputs = this.$(".o_chat_toolbox_done, .o_chat_toolbox_container, .o_chat_toolbox_send"),
            this.$write_btn = this.$(".o_chat_toolbox_write"), this.$write_btn.click((() => this.blockClient())),
            this.$(".o_chat_toolbox_done").click((() => this.releaseClient())), Promise.resolve();
        },
        destroy: function() {
            return this.component && (this.component.destroy(), this.component = void 0), this._super.apply(this, arguments);
        },
        on_attach_callback: function() {
            if (this.component) return;
            let props = {
                parent_widget: this
            };
            this.component = new ToolBoxComponent(null, props), this.env = Component.env, this.component.env = this.env,
            this.component.mount(this.$attachment_zone[0]);
        },
        blockClient: function() {
            this.parent.selected_conversation && "new" == this.parent.selected_conversation.status && this._rpc({
                model: this.parent.model,
                method: "block_conversation",
                args: [ [ this.parent.selected_conversation.id ] ]
            }).then((() => {
                this.$write_btn.addClass("o_hidden"), this.$other_inputs.removeClass("o_hidden"),
                this.parent.selected_conversation.status = "current", this.parent.selected_conversation.showMessages(),
                this.parent.selected_conversation.prependTo(this.parent.$current_chats), this.parent.selected_conversation.$el.addClass("active"),
                this.parent.tabsClear();
            }), (() => this.parent.removeSelectedConversation()));
        },
        releaseClient: function() {
            this.parent.selected_conversation && "current" == this.parent.selected_conversation.status && this._rpc({
                model: this.parent.model,
                method: "release_conversation",
                args: [ [ this.parent.selected_conversation.id ] ]
            }).then((() => {
                this.parent.removeSelectedConversation(), this.parent.showConversationPanel();
            }));
        },
        do_show: function() {
            this._super(), this.parent.selected_conversation ? "current" == this.parent.selected_conversation.status ? (this.$write_btn.addClass("o_hidden"),
            this.$other_inputs.removeClass("o_hidden")) : "new" == this.parent.selected_conversation.status && (this.$write_btn.removeClass("o_hidden"),
            this.$other_inputs.addClass("o_hidden")) : (this.$write_btn.removeClass("o_hidden"),
            this.$other_inputs.addClass("o_hidden"));
        },
        sendMessage: function() {
            let out = Promise.resolve(), options = {
                from_me: !0
            }, text = this.$input.val().trim();
            if ("" != text && (options.ttype = "text", options.text = text), this.component.attachment.value) {
                let attachment = this.component.attachment.value;
                attachment.mimetype.includes("image") ? options.ttype = "image" : attachment.mimetype.includes("audio") ? options.ttype = "audio" : attachment.mimetype.includes("video") ? options.ttype = "video" : options.ttype = "file",
                options.res_model = "ir.attachment", options.res_id = attachment.id, options.res_model_obj = attachment;
            }
            options.is_direct=true;
            return options.ttype && (out = this.parent.selected_conversation.createMessage(options).then((msg => (this.$input.val(""),
            this.$input.focus(), this.component.attachment.value = null, this.enableDisplabeAttachBtn(),
            msg)))), out;
        },
        onKeypress: function(event) {
            13 !== event.which || event.shiftKey || (event.preventDefault(), this.sendMessage());
        },
        clickAddAttachment: function() {
            this.component.openBrowserFileUploader();
        },
        enableDisplabeAttachBtn: function() {
            this.$attachment_button.prop("disabled", Boolean(this.component.attachment.value));
        }
    });
    return Object.assign(ToolBoxComponent, {
        components,
        props: {
            parent_widget: Object
        },
        template: "acrux_chat_toolbox_component"
    }), ToolBox;
})), odoo.define("acrux_chat.chat_classes", (function(require) {
    "use strict";
    return {
        Message: require("acrux_chat.message"),
        Conversation: require("acrux_chat.conversation"),
        ToolBox: require("acrux_chat.toolbox"),
        DefaultAnswer: require("acrux_chat.default_answer"),
        ProductSearch: require("acrux_chat.product_search"),
        InitConversation: require("acrux_chat.init_conversation"),
        UserStatus: require("acrux_chat.user_status")
    };
})), odoo.define("acrux_chat.acrux_chat", (function(require) {
    "use strict";
    require("bus.BusService");
    var core = require("web.core"), AbstractAction = require("web.AbstractAction"), session = require("web.session"), chat = require("acrux_chat.chat_classes"), config = require("web.config"), Dialog = require("web.Dialog"), field_utils = require("web.field_utils"), _t = core._t, chat_is_read_resolve = null, chat_is_read = new Promise((r => chat_is_read_resolve = r)), AcruxChatAction = AbstractAction.extend({
        contentTemplate: "acrux_chat_action",
        hasControlPanel: !1,
        events: {
            "click .o_acrux_chat_notification .fa-close": "_onCloseNotificationBar",
            "click .o_acrux_chat_request_permission": "_onRequestNotificationPermission",
            "click .o_acrux_chat_item": "selectConversation",
            "click div.o_chat_title .navbar-toggler": "showConversationPanel"
        },
        init: function(parent, action, options) {
            this._super.apply(this, arguments), this.action_manager = parent, this.model = "acrux.chat.conversation",
            this.domain = [], this.action = action, this.options = options || {}, this.notification_bar = window.Notification && "default" === window.Notification.permission,
            this.selected_conversation = this.options.selected_conversation, this.conversations = this.options.conversations || [],
            this.default_answers = this.options.default_answers || [], this.defaultChannelID = this.options.active_id || this.action.context.active_id || this.action.params.default_active_id || "acrux_chat_live_id";
            let widget_options = {
                context: this.action.context
            };
            this.toolbox = new chat.ToolBox(this, widget_options), this.product_search = new chat.ProductSearch(this, widget_options),
            this.init_conversation = new chat.InitConversation(this, widget_options), this.user_status = new chat.UserStatus(this, widget_options),
            odoo.debranding_new_name ? this.company_name = odoo.debranding_new_name : this.company_name = "Odoo",
            this.startBus();
        },
        startBus: function() {
            let chat_model = this.model, channel = JSON.stringify([ session.db, chat_model ]), channel_private = JSON.stringify([ session.db, chat_model, session.uid ]);
            this.call("bus_service", "addChannel", channel), this.call("bus_service", "addChannel", channel_private),
            this.call("bus_service", "onNotification", this, (notifications => {
                var data = notifications.filter((function(item) {
                    return item[0][1] === chat_model;
                })).map((function(item) {
                    return item[1];
                }));
                this.onNotification(data);
            }));
        },
        willStart: function() {
            return Promise.all([ this._super(), this.getDefaultAnswers(), this.getRequiredViews(), this.getCurrency() ]);
        },
        start: function() {
            return Promise.all([ this._super(), session.is_bound ]).then((() => this._initRender().then((() => chat_is_read_resolve(this)))));
        },
        _initRender: function() {
            return this.$chat_content = this.$(".o_acrux_chat_content"), this.$sidebar_left = this.$(".o_sidebar_left"),
            this.$first_main_tab = this.$(".o_sidebar_right").find("ul.nav.nav-tabs").children("li").first().find("a"),
            this.$chat_message = this.$("div.o_chat_thread"), this.$current_chats = this.$(".o_acrux_chat_items.o_current_chats"),
            this.$new_chats = this.$(".o_acrux_chat_items.o_new_chats"), this.$chat_title = this.$("div.o_chat_title"),
            this.default_answers.forEach((x => x.appendTo(this.$("table#default_answers")))),
            this.$chat_message.on("scroll", (event => {
                if (0 == $(event.target).scrollTop() && this.selected_conversation) return this.selected_conversation.syncMoreMessage();
            })), core.bus.on("acrux_chat_msg_seen", this, this.chatMessageSeen), config.device.isMobile && this.showConversationPanel(),
            this.onResizeWindow(), this.onWindowShow(), Promise.all([ this.toolbox.appendTo(this.$(".o_acrux_chat_content")), this.product_search.prependTo(this.$(".o_sidebar_right")), this.init_conversation.appendTo(this.$("div#tab_content_init_chat")), this.user_status.appendTo(this.$sidebar_left.find(".o_acrux_group").first()) ]).then((() => {
                this.toolbox.do_hide(), this.user_status.isActive() && this.changeStatusView();
            }));
        },
        destroy: function() {
            return this.$el && (this.$chat_message.off("scroll"), core.bus.off("acrux_chat_msg_seen")),
            this._super.apply(this, arguments);
        },
        do_show: function() {
            this._super.apply(this, arguments), this.action_manager.do_push_state({
                action: this.action.id
            });
        },
        on_attach_callback: function() {
            this._super(...arguments), this.toolbox && this.toolbox.on_attach_callback();
        },
        getServerConversation: function() {
            return this._rpc({
                model: this.model,
                method: "search_active_conversation",
                args: []
            }).then((result => {
                result.forEach((r => {
                    this.conversations.push(new chat.Conversation(this, r));
                }));
            }));
        },
        getCurrency: function() {
            return this._rpc({
                model: "res.company",
                method: "read",
                args: [ [ session.company_id ], [ "currency_id" ] ]
            }).then((result => {
                this.currency_id = result[0].currency_id[0], this.currency = session.get_currency(this.currency_id);
            }));
        },
        getDefaultAnswers: function() {
            return this._rpc({
                model: "acrux.chat.default.answer",
                method: "search_read",
                args: [ [], [ "name", "sequence", "id", "text", "ttype", "res_model", "res_id" ] ]
            }).then((result => {
                result.forEach((r => this.default_answers.push(new chat.DefaultAnswer(this, r))));
            }));
        },
        getRequiredViews: function() {
            return Promise.resolve();
        },
        format_monetary: function(val) {
            return val = field_utils.format.monetary(val, null, {
                currency: this.currency
            }), $("<span>").html(val).text();
        },
        chatMessageSeen: function() {
            this.selected_conversation && "current" == this.selected_conversation.status && this.selected_conversation.messageSeen();
        },
        onResizeWindow: function() {
            let original_device = config.device.isMobile;
            $(window).resize((() => {
                config.device.isMobile != original_device && (config.device.isMobile ? this.showConversationPanel() : (this.showChatPanel(),
                this.$sidebar_left.removeClass("d-none")), original_device = config.device.isMobile);
            }));
        },
        onWindowShow: function() {
            document.addEventListener("visibilitychange", (function(_ev) {
                document.hidden || core.bus.trigger("acrux_chat_msg_seen");
            }));
        },
        changeStatusView: function() {
            this.conversations.forEach((x => x.destroy())), this.conversations = [], this.user_status.isActive() && this.getServerConversation().then((() => this.showConversations())),
            this.selected_conversation = null, this.toolbox.do_hide(), this.tabsClear();
        },
        showConversations: function() {
            this.getNewConversation().forEach((x => x.appendTo(this.$new_chats))), this.getCurrentConversation().forEach((x => x.appendTo(this.$current_chats)));
        },
        showConversationPanel: function() {
            this.$chat_content.hide(), this.$sidebar_left.removeClass("d-none");
        },
        showChatPanel: function() {
            config.device.isMobile && this.$sidebar_left.addClass("d-none"), this.$chat_content.show();
        },
        getNewConversation: function() {
            return this.conversations.filter((x => "new" == x.status));
        },
        getCurrentConversation: function() {
            return this.conversations.filter((x => "new" != x.status));
        },
        selectConversation: function(event) {
            let finish, id = $(event.currentTarget).data("id"), conv_id = this.conversations.find((x => x.id == id));
            return conv_id && this.selected_conversation != conv_id ? (this.selected_conversation && this.selected_conversation.$el.removeClass("active"),
            this.selected_conversation = conv_id, finish = this.selected_conversation.showMessages(),
            this.tabsClear()) : finish = Promise.resolve(), this.toolbox.do_show(), this.toolbox.$input.focus(),
            this.showChatPanel(), finish;
        },
        onNotification: function(data) {
            data && data.forEach((d => {
                d.delete_conversation && this.user_status.isActive() && d.delete_conversation.forEach((m => this.onDeleteConversation(m))),
                d.delete_taken_conversation && this.user_status.isActive() && d.delete_taken_conversation.forEach((m => this.onDeleteTakenConversation(m))),
                d.new_messages && this.user_status.isActive() && d.new_messages.forEach((m => this.onNewMessage(m))),
                d.init_conversation && this.user_status.isActive() && d.init_conversation.forEach((m => this.onInitConversation(m))),
                d.change_status && d.change_status.forEach((m => this.onChangeStatus(m))), d.error_messages && this.user_status.isActive() && this.onErrorMessages(d.error_messages);
            }));
        },
        onNewMessage: function(d) {
            let def_out, conv = this.conversations.find((x => x.id == d.id));
            if (conv) conv.incressNewMessage(), def_out = conv.addClientMessage(d.messages),
            document.hidden && "current" == conv.status && Notification && "granted" === Notification.permission && new Notification(_t("New messages from ") + conv.name); else if ("new" == d.status) {
                let conv = new chat.Conversation(this, d);
                this.conversations.push(conv), def_out = conv.appendTo(this.$new_chats).then((() => {
                    conv.incressNewMessage();
                }));
            } else def_out = Promise.resolve();
            return def_out;
        },
        onDeleteConversation: function(conv_data) {
            conv_data.sellman_id[0] != session.uid && this.deleteConversation(conv_data);
        },
        onDeleteTakenConversation: function(conv_data) {
            conv_data.sellman_id[0] == session.uid && this.deleteConversation(conv_data);
        },
        onInitConversation: function(conv_data) {
            if (conv_data.sellman_id[0] == session.uid) {
                let def, conv = this.conversations.find((x => x.id == conv_data.id));
                conv && ("new" == conv.status ? (this.deleteConversation(conv), conv = null) : this.selected_conversation && this.selected_conversation.id != conv.id && conv.setMessages(conv_data.messages)),
                conv ? def = Promise.resolve() : (conv = new chat.Conversation(this, conv_data),
                this.conversations.push(conv), def = conv.appendTo(this.$current_chats)), def.then((() => this.selectConversation({
                    currentTarget: conv.el
                })));
            }
        },
        onChangeStatus: function(data) {
            data.sellman_id[0] == session.uid && (this.user_status.changeStatusNotify(data),
            this.changeStatusView());
        },
        onErrorMessages: function(error_messages) {
            let message_found, conv_to_show, msg_to_show, conv_found = [], show_conv = !0;
            if (error_messages.forEach((conv_data => {
                let conv = this.conversations.find((x => x.id == conv_data.id));
                conv && (message_found = conv.setMessageError(conv_data.messages), conv_found.push(conv),
                this.selected_conversation && this.selected_conversation.id == conv.id ? show_conv = !1 : "current" == conv.status && (conv_to_show = conv,
                message_found.length && (msg_to_show = message_found[0])));
            })), conv_found.length) {
                let msg = _t("Error in conversation with ");
                conv_found.forEach(((val, index) => {
                    index && (msg += ", "), msg += val.name;
                })), Dialog.alert(this, msg, {
                    confirm_callback: () => {
                        show_conv && conv_to_show && this.selectConversation({
                            currentTarget: conv_to_show.el
                        }).then((() => {
                            msg_to_show.el.scrollIntoView();
                        }));
                    }
                });
            }
        },
        deleteConversation: function(conv_data) {
            let conv = this.conversations.find((x => x.id == conv_data.id));
            this.conversations = this.conversations.filter((x => x.id != conv_data.id)), conv && (conv == this.selected_conversation ? this.removeSelectedConversation() : conv.destroy());
        },
        removeSelectedConversation: function() {
            this.selected_conversation && (this.conversations = this.conversations.filter((x => x.id != this.selected_conversation.id)),
            this.selected_conversation.destroy(), this.selected_conversation = null), this.toolbox.do_hide(),
            this.tabsClear();
        },
        tabsClear: function() {
            this.init_conversation.empty(), this.$first_main_tab.trigger("click");
        },
        _onCloseNotificationBar: function() {
            this.$(".o_acrux_chat_notification").slideUp();
        },
        _onRequestNotificationPermission: function(event) {
            event.preventDefault(), this.$(".o_acrux_chat_notification").slideUp();
            var def = window.Notification && window.Notification.requestPermission();
            def && def.then((value => {
                "granted" !== value ? this.call("bus_service", "sendNotification", _t("Permission denied"), this.company_name + _t(" will not have the permission to send native notifications on this device.")) : this.call("bus_service", "sendNotification", _t("Permission granted"), this.company_name + _t(" has now the permission to send you native notifications on this device."));
            }));
        }
    });
    return core.action_registry.add("acrux.chat.conversation_tag", AcruxChatAction),
    {
        AcruxChatAction,
        is_ready: chat_is_read
    };
}));
