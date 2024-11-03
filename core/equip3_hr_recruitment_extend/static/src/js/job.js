odoo.define('equip3_hr_recruitment_extend.job', function (require) {
    'use strict';
    var time = require('web.time');
    var core = require('web.core');

    var publicWidget = require('web.public.widget');
    var _t = core._t;


    publicWidget.registry.JobFormWidget = publicWidget.Widget.extend({
        selector: '.o_survey_form_job',
        events: {
            'click .btn-job': '_onSubmit',
        },

        //--------------------------------------------------------------------------
        // Widget
        //--------------------------------------------------------------------------

        /**
         * @override
         */

        // start: function () {
        //     var self = this;
        //     this.fadeInOutDelay = 400;
        //     return this._super.apply(this, arguments).then(function () {
        //         self.options = self.$target.find('form').data();
        //         const imageUpload = document.querySelector('[is-cv="True"]');
        //         const email = document.querySelector('[is-email="True"]');
        //         const phone = document.querySelector('[is-phone="True"]');
        //         const name = document.querySelector('[is-name="True"]');
        //         const nik = document.querySelector('[is-nik="True"]');
        //         if (imageUpload){
        //             imageUpload.addEventListener("change", async (event) => {
        //                 const image = event.target.files[0];
        //                 if (!image) {
        //                     return;
        //                 }
        //                 const isPDF = image.type === "application/pdf";
        //                 const isImage = image.type.startsWith("image/"); 
        //                 if (isImage){
        //                     const imageData = await loadImageAsDataURL(image);
        //                     const ocrResult = await performOCR(imageData);        
        //                     if (ocrResult.email) {
        //                         if (email){
        //                             email.value = ocrResult.email;
        //                         }
        //                     }
                   
        //                     if (ocrResult.phone) {
        //                         if (phone){
        //                             phone.value = ocrResult.phone.replace(/\D/g, '');
        //                         }
        //                     }
        //                     if (ocrResult.name) {
        //                         if (name){
        //                             name.value = ocrResult.name;
        //                         }
        //                     }

        //                     if (ocrResult.nik) {
        //                         if (nik){
        //                             nik.value = ocrResult.nik;
        //                         }
        //                     }
        //                 }
        //                 else if(isPDF){

        //                     const fileData = await readFileAsArrayBufferpdf(image);
        //                     const text = await extractTextFromPDF(fileData);
        //                     const emailMatch = text.match(/[\w\.-]+@[\w\.-]+/);
        //                     const phoneMatch = text.match(/(?:\+62|08)\d{9,12}/)
        //                     const nameMatch = text.match(/(Full Name:|Name:)\s*([^\n]+)/i);
        //                     const nikMatch = text.match(/(\d{16})/i);
        //                     console.log("phoneMatch")
        //                     console.log(text)
        //                     console.log(phoneMatch)
        //                     if (nameMatch && nameMatch[2]) {
        //                         if (name){
        //                             name.value = nameMatch[2].trim();

        //                         }
    
        //                     }
                            
        //                     if (name){
        //                         name.value = nameMatch && nameMatch[1] ? nameMatch[1].trim() : null

        //                     }

        //                     if (emailMatch) {
        //                         if (email){
        //                             email.value = emailMatch[0];
        //                         }
                                
        //                     }
        //                     if (phoneMatch){
        //                         if (phone){
        //                             phone.value = phoneMatch[0].replace(/\D/g, '')


        //                         }
        //                     }
        //                     if (nikMatch){
        //                         if (nik){
        //                             nik.value = nikMatch[0]


        //                         }
                                

        //                     }
        //                 }
  
        //             }
                    
        //             );

                    
    
        //             function loadImageAsDataURL(file) {
        //                 return new Promise((resolve) => {
        //                     const reader = new FileReader();
        //                     reader.onload = (event) => {
        //                         resolve(event.target.result);
        //                     };
        //                     reader.readAsDataURL(file);
        //                 });
        //             }
                
        //             async function performOCR(imageData) {
        //                 const { data: { text } } = await Tesseract.recognize(imageData);
        //                 const result = { name: null, email: null ,phone:null,nik:null};
        //                 const namePattern = /(Full Name:|Name:)\s*([^\n]+)/i;
        //                 const nameMatch = text.match(namePattern);
        //                 if (nameMatch && nameMatch[2]) {
        //                     result.name = nameMatch[2].trim();
 
        //                 }
                
        //                 const emailMatch = text.match(/[\w\.-]+@[\w\.-]+/);
        //                 if (emailMatch) {
        //                     result.email = emailMatch[0];
        //                 }
                        
    
        //                 const phoneMatch = text.match(/(?:\+62|08)\d{9,12}/)
        //                 if (phoneMatch){
        //                     result.phone = phoneMatch[0].replace(/\D/g, '')

        //                 }
        //                 const digitMatch =text.match(/(\d{16})/);
        //                 if (digitMatch){
        //                     result.nik = digitMatch[0]
        //                 }
                
        //                 return result;
        //             }

        //             function readFileAsArrayBufferpdf(file) {
        //                 return new Promise((resolve) => {
        //                     const reader = new FileReader();
        //                     reader.onload = (event) => {
        //                         resolve(event.target.result);
        //                     };
        //                     reader.readAsArrayBuffer(file);
        //                 });
        //             }
            
        //             async function extractTextFromPDF(fileData) {
        //                 const pdf = await pdfjsLib.getDocument({ data: fileData }).promise;
        //                 let text = '';
            
        //                 for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
        //                     const page = await pdf.getPage(pageNum);
        //                     const pageText = await page.getTextContent();
            
        //                     pageText.items.forEach((item) => {
        //                         text += item.str + ' ';
        //                     });
                        
        //                 if (!text){
        //                     const pageNumber = 1; // Change to the desired page number
        //                     const page = await pdf.getPage(pageNumber);
        //                     const viewport = page.getViewport({ scale: 1.5 }); // Adjust scale as needed
        //                     const canvas = document.createElement("canvas");
        //                     const context = canvas.getContext("2d");
        //                     canvas.width = viewport.width;
        //                     canvas.height = viewport.height;
        //                     const renderContext = {
        //                         canvasContext: context,
        //                         viewport: viewport,
        //                     };
        //                     await page.render(renderContext);
        //                     const imageData = canvas.toDataURL("image/png");
        //                     const ocrResult = await performOCR(imageData);

        //                 }
                        

        //                 }



            
        //                 return text;
        //             }


        //             function readFileAsArrayBuffer(file) {
        //                 return new Promise((resolve) => {
        //                     const reader = new FileReader();
        //                     reader.onload = (event) => {
        //                         resolve(event.target.result);
        //                     };
        //                     reader.readAsArrayBuffer(file);
        //                 });
        //             }



        //         };

                
            
            



        //     });
        // },

        _onSubmit: function (event) {
            // event.preventDefault();
            var $form = this.$('form');
            var formData = new FormData($form[0]);
            var options = {};
            var $target = $(event.currentTarget);
            this._validateForm($form, formData, event)
            // if (this._validateForm($form, formData)) {
            //         event.preventDefault();
            //         console.log(this._validateForm($form, formData));
            //     }
            // else {
            //     console.log("here");
            //     return true
            // }


        },


        _validateForm: function ($form, formData, event) {
            var self = this;
            var errors = {};
            var validationEmailMsg = _t("This answer must be an email address.");
            var validationDateMsg = _t("This is not a date");

            this._resetErrors();

            var data = {};
            formData.forEach(function (value, key) {
                data[key] = value;
            });
            var inactiveQuestionIds = this.options.sessionInProgress ? [] : this._getInactiveConditionalQuestionIds();


            $form.find('[data-question-type]').each(function () {

                var $input = $(this);
                var $questionWrapper = $input.closest(".js_question-wrapper");
                var questionId = $questionWrapper.attr('id');


                // If question is inactive, skip validation.


                var questionRequired = $questionWrapper.data('required');
                var constrErrorMsg = $questionWrapper.data('constrErrorMsg');
                var validationErrorMsg = $questionWrapper.data('validationErrorMsg');
                switch ($input.data('questionType')) {
                    case 'is_employee_skill':
                        $("input[name='employee_skill']").val('[]')
                        var array_pe = []
                        $('#table_emp_skill_table tbody tr.input_data').each(function() {
                            var dict_array_pe = {}
                            $($( this ).find('select')).each(function() {
                              var name_input_pe = $( this ).attr('name')
                              name_input_pe = name_input_pe.replace('_pe','')
                              var value_select_skill = $( this ).val()
                              dict_array_pe[name_input_pe] = value_select_skill
                              if(!value_select_skill || value_select_skill == '0' || value_select_skill ==0){
                                errors[questionId] = 'Please fill in the employee skills form completely'
                              }
                            });
                            array_pe.push(dict_array_pe)

                        });
                        if(array_pe && errors[questionId] == undefined){
                            $('input[name="employee_skill"]').val(JSON.stringify(array_pe))
                        }
                


                        var employee_skill_value = $("input[name='employee_skill']").val()
                
                        if (questionRequired == 'True' && employee_skill_value=='[]' && errors[questionId] == undefined) {
                            errors[questionId] = 'This question requires an answer'
               
                        }
                        break;
                        
                    case 'table':
                        var req_table = $('input[name="have_exp"]').is(":checked")
                        if (req_table){
                            req_table = false
                        }
                        else{
                            req_table = true
                        }
                        
                        $('input[name="past_experience"]').val('')
                        if (req_table) {
                            if($('#table_past_experience_table input').length <= 0){
                                errors[questionId] = constrErrorMsg;
                            }
                            else{
                                $('#table_past_experience_table input').each(function() {
                                  var check_validation_epx_field = true
                                  var checkbox_currently_work = false
                                  if($(this).attr('name')=='end_date_pe' || $(this).attr('name')=='reason_pe'){
                                    checkbox_currently_work = $($($(this).parents()[1]).find('input[name="is_currently_work_here_pe"]')).is(":checked")
                                    if(checkbox_currently_work){
                                        check_validation_epx_field = false
                                    }
                                  }
                                  if($( this ).val()=='' && $(this).attr('name')!='company_phone_pe'&&check_validation_epx_field){
                         
                                    errors[questionId] = constrErrorMsg;
                                  }
                                });
                            }
                                
                        }
                        if (errors[questionId] == undefined){
                            var array_pe = []
                             if (req_table){
                                $('#table_past_experience_table tbody tr.input_data').each(function() {
                                    var dict_array_pe = {}
                                    $($( this ).find('input')).each(function() {
                                      var name_input_pe = $( this ).attr('name')
                                      name_input_pe = name_input_pe.replace('_pe','')
                                      dict_array_pe[name_input_pe] = $( this ).val()
                                      if (name_input_pe=='is_currently_work_here'){
                                        if($(this).is(":checked")){
                                            dict_array_pe[name_input_pe] = true
                                        }
                                        else{
                                            dict_array_pe[name_input_pe] = false
                                        }
                                      }
                                    });
                                    array_pe.push(dict_array_pe)

                                });
                                if(array_pe){
                                    $('input[name="past_experience"]').val(JSON.stringify(array_pe))
                                }
                            }
                                
                        }
                            

                        break;
                        
                    case 'char_box':
                        if (questionRequired && !$input.val()) {
                            errors[questionId] = constrErrorMsg;
                        } else if ($input.val() && $input.attr('type') === 'email' && !self._validateEmail($input.val())) {
                            errors[questionId] = validationEmailMsg;
                        } else {
                            var lengthMin = $input.data('validationLengthMin');
                            var lengthMax = $input.data('validationLengthMax');
                            var length = $input.val().length;
                            if (lengthMin && (lengthMin > length || length > lengthMax)) {
                                errors[questionId] = validationErrorMsg;
                            }
                        }
                        break;
                    case 'numerical_box':
                        if (questionRequired && !data[questionId]) {
                            errors[questionId] = constrErrorMsg;
                        } else {
                            var floatMin = $input.data('validationFloatMin');
                            var floatMax = $input.data('validationFloatMax');
                            var value = parseFloat($input.val());
                            if (floatMin && (floatMin > value || value > floatMax)) {
                                errors[questionId] = validationErrorMsg;
                            }
                        }
                        break;
                    case 'text':
                        if($input.attr('type')=='date'){
                            var date_input_value = $input.val()
                            if (questionRequired && !date_input_value) {
                                errors[questionId] = 'This question requires an answer'
                            }
                            if(date_input_value){
                                if(date_input_value.split('-')[0].length!=4 || date_input_value.charAt(0) == 0) {
                                    errors[questionId] = 'Please insert the correct year format.'
                                    
                                }
                                
                                
                            }
                        }
                        break
                            

                    case 'datetime':
                        if (questionRequired && !data[questionId]) {
                            errors[questionId] = constrErrorMsg;
                        } else if (data[questionId]) {
                            var datetimepickerFormat = $input.data('questionType') === 'datetime' ? time.getLangDatetimeFormat() : time.getLangDateFormat();
                            var momentDate = moment($input.val(), datetimepickerFormat);
                            if (!momentDate.isValid()) {
                                errors[questionId] = validationDateMsg;
                            } else {
                                var $dateDiv = $questionWrapper.find('.o_survey_form_date');
                                var maxDate = $dateDiv.data('maxdate');
                                var minDate = $dateDiv.data('mindate');
                                if ((maxDate && momentDate.isAfter(moment(maxDate)))
                                    || (minDate && momentDate.isBefore(moment(minDate)))) {
                                    errors[questionId] = validationErrorMsg;
                                }
                            }
                        }
                        break;
                    case 'multiple_choice_multiple_answer':
                    case 'multiple_choice_one_answer':
                        if (questionRequired) {
                            var $textarea = $questionWrapper.find('textarea');
                            if (!data[questionId]) {
                                errors[questionId] = constrErrorMsg;
                            } else if (data[questionId] === '-1' && !$textarea.val()) {
                                // if other has been checked and value is null
                                errors[questionId] = constrErrorMsg;
                            }
                        }
                        break;
                    case 'matrix':
                        if (questionRequired) {
                            var subQuestionsIds = $questionWrapper.find('table').data('subQuestions');
                            subQuestionsIds.forEach(function (id) {
                                if (!((questionId + '_' + id) in data)) {
                                    errors[questionId] = constrErrorMsg;
                                }
                            });
                        }
                        break;

                    case 'file':

                        if (questionRequired && !$input.val()) {
                            errors[questionId] = constrErrorMsg;
                        }
                        if ($input.val()) {
                            var _validFileExtensions = [".pdf", ".xls", ".rar", ".doc", ".xlsx",".docx",".jpg",".zip",".png",".mp4"];
                            var sFileName = $input[0].value;
                            const fileSize = $input[0].files[0].size / 1024 / 1024;
                            if (fileSize > $input.data('maxFile')) {
                                errors[questionId] = "file cannot be more than " + $input.data('maxFile') + " mb";

                            }
                            if(!$input.data('pdfFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.pdf' });
                            }
                            if(!$input.data('xlsFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.xls' });
                            }
                            if(!$input.data('rarFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.rar' });
                            }
                             if(!$input.data('docFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.doc' });
                            }

                             if(!$input.data('xlsxFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.xlsx' });
                            }

                             if(!$input.data('docxFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.docx' });
                            }
                             if(!$input.data('jpgFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.jpg' });
                            } if(!$input.data('zipFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.zip' });
                            }if(!$input.data('pngFile')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.png' });
                            }
                            if(!$input.data('mp4File')){
                                _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.mp4' });
                            }
                            if (sFileName.length > 0) {
                                var blnValid = false;
                                for (var j = 0; j < _validFileExtensions.length; j++) {
                                    var sCurExtension = _validFileExtensions[j];
                                    if (sFileName.substr(sFileName.length - sCurExtension.length, sCurExtension.length).toLowerCase() === sCurExtension.toLowerCase()) {
                                        blnValid = true;
                                        break;
                                    }
                                }

                                if (!blnValid) {
                                    errors[questionId] = "Sorry, " + $input[0].files[0].name + " is invalid, allowed extensions are: " + _validFileExtensions.join(", ");
                                }
                            }


                        }

                }
            });
            if (_.keys(errors).length > 0) {
                this.$('.o_survey_form_content').fadeIn(0);
                this._showErrors(errors, event);
            }
            return false;
        },

        _showErrors: function (errors, event) {
            var self = this;
            var errorKeys = _.keys(errors);
            _.each(errorKeys, function (key) {
                self.$("#" + key + '>.o_survey_question_error').append($('<p>', {text: errors[key]})).addClass("slide_in");
                if (errorKeys[0] === key) {
                    self._scrollToError(self.$('.js_question-wrapper#' + key));
                    event.preventDefault();

                }
            });
        },

        _scrollToError: function ($target) {
            // console.log($target);
            var scrollLocation = $target.offset().top;
            var navbarHeight = $('.o_main_navbar').height();

            if (navbarHeight) {
                // In overflow auto, scrollLocation of target can be negative if target is out of screen (up side)
                scrollLocation = scrollLocation >= 0 ? scrollLocation - navbarHeight : scrollLocation + navbarHeight;
            }
            var scrollinside = $("#wrapwrap").scrollTop();
            $('#wrapwrap').animate({
                scrollTop: scrollinside + scrollLocation
            }, 500);
        },

        _resetErrors: function () {
            this.$('.o_survey_question_error').empty().removeClass('slide_in');
            this.$('.o_survey_error').addClass('d-none');
        },

        _getInactiveConditionalQuestionIds: function () {
            var self = this;
            var inactiveQuestionIds = [];
            if (this.options.triggeredQuestionsByAnswer) {
                Object.keys(this.options.triggeredQuestionsByAnswer).forEach(function (answerId) {
                    if (!self.selectedAnswers.includes(parseInt(answerId))) {
                        self.options.triggeredQuestionsByAnswer[answerId].forEach(function (questionId) {
                            inactiveQuestionIds.push(questionId);
                        });
                    }
                });
            }
            return inactiveQuestionIds;
        },

        _validateEmail: function (email) {
            var emailParts = email.split('@');
            return emailParts.length === 2 && emailParts[0] && emailParts[1];
        },

        // -------------------------------------------------------------------------
        // Private
        // -------------------------------------------------------------------------

        // Handlers
        // -------------------------------------------------------------------------


    });

    return publicWidget.registry.JobFormWidget;

});
