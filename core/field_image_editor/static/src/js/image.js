odoo.define('field_image_editor.edit', function(require) {
    var core = require('web.core');
    var base_f = require('web.basic_fields');
    var imageWidget = base_f.FieldBinaryImage;
    var session = require('web.session');
    var utils = require('web.utils');
    var field_utils = require('web.field_utils');

    imageWidget.include({

        events: _.extend({}, imageWidget.prototype.events, {
            'click .fa-magic': 'on_magic',
        }),

        on_magic: function(e) {
            var self = this;
            // Load an image and tell our tui imageEditor instance the new and the old image size:
            var data = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
            if (this.value) {
                var name_field = self.name;
                if (name_field == "image_medium" ||
                    name_field == "image_small")
                    name_field = "image";

                if (!utils.is_bin_size(this.value)) {
                    // Use magic-word technique for detecting image type
                    data = 'data:image/' + (this.file_type_magic_word[this.value[0]] || 'png') + ';base64,' + this.value;
                } else {
                    data = session.url('/web/image', {
                        model: this.model,
                        id: JSON.stringify(this.res_id),
                        field: name_field,
                        // unique forces a reload of the image when the record has been updated
                        unique: field_utils.format.datetime(this.recordData.__last_update).replace(/[^0-9]/g, ''),
                    });
                }
            }
            self.tui_image_open(data, {});
        },

        tui_image_open: function(data, file) {
            var self = this;
            var tui_div = jQuery('<div/>', {
                id: 'tui-image-editor-container',
            })
            tui_div.appendTo($('body'));
            // Create an instance of the tui imageEditor, loading a blank image
            var imageEditor = new tui.ImageEditor('#tui-image-editor-container', {
                includeUI: {
                    loadImage: {
                        path: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
                        name: 'Blank'
                    },
                    theme: blackTheme,
                    initMenu: 'filter',
                    menuBarPosition: 'bottom'
                },
            });
            $('#tui-image-editor-container').fadeIn('show');


            var save = $('<div class="tui-image-editor-save-btn" style="background-color: #fff;border: 1px solid #ddd;color: #222;font-family: "Noto Sans", sans-serif;font-size: 12px">Save</div>');
            var close = $('<div class="tui-image-editor-close-btn" style="background-color: #fff;border: 1px solid #ddd;color: #222;font-family: "Noto Sans", sans-serif;font-size: 12px">Close</div>');
            close.insertAfter($('.tui-image-editor-download-btn'));
            save.insertAfter($('.tui-image-editor-download-btn'));
            $('.tui-image-editor-close-btn').click(function() {
                $('#tui-image-editor-container').fadeOut();
            });
            $('.tui-image-editor-save-btn').click(function() {
                var data = imageEditor.toDataURL();
                data = data.split(',')[1];
                self.on_file_uploaded(file.size, file.name, file.type, data);
                $('#tui-image-editor-container').fadeOut();
            });

            // Patch the loadImageFromURL of our tui imageEditor instance:
            imageEditor.loadImageFromURL = (function() {
                var cached_function = imageEditor.loadImageFromURL;

                function waitUntilImageEditorIsUnlocked(imageEditor) {
                    return new Promise((resolve, reject) => {
                        const interval = setInterval(() => {
                            if (!imageEditor._invoker._isLocked) {
                                clearInterval(interval);
                                resolve();
                            }
                        }, 100);
                    })
                }
                return function() {
                    return waitUntilImageEditorIsUnlocked(imageEditor).then(() => cached_function.apply(this, arguments));
                };
            })();

            imageEditor.loadImageFromURL(data, "SampleImage").then(result => {
                imageEditor.ui.resizeEditor({
                    imageSize: {
                        oldWidth: result.oldWidth,
                        oldHeight: result.oldHeight,
                        newWidth: result.newWidth,
                        newHeight: result.newHeight
                    },
                });
            }).catch(err => {
                console.error("Something went wrong:", err);
            })

            // Auto resize the editor to the window size:
            window.addEventListener("resize", function() {
                imageEditor.ui.resizeEditor()
            })
        },
/*        on_file_change: function(e) {
            var self = this;
            console.log(self);
            var file_node = e.target;
            if ((this.useFileAPI && file_node.files.length) || (!this.useFileAPI && $(file_node).val() !== '')) {
                if (this.useFileAPI) {
                    var file = file_node.files[0];
                    if (file.size > this.max_upload_size) {
                        var msg = _t("The selected file exceed the maximum file size of %s.");
                        this.do_warn(_t("File upload"), _.str.sprintf(msg, utils.human_size(this.max_upload_size)));
                        return false;
                    }
                    var filereader = new FileReader();
                    filereader.readAsDataURL(file);
                    filereader.onloadend = function(upload) {
                        self.tui_image_open(filereader.result, file);
                    };
                } else {
                    this.$('form.o_form_binary_form input[name=session_id]').val(this.session.session_id);
                    this.$('form.o_form_binary_form').submit();
                }
                this.$('.o_form_binary_progress').show();
                this.$('button').hide();
            }
        },
*/    });


});