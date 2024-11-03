odoo.define("equip3_purchase_masterdata.thousand_separator", function(require) {
    "use strict";
    function setSelectionRange(input, selectionStart, selectionEnd) {
      if (input.setSelectionRange) {
        input.focus();
        input.setSelectionRange(selectionStart, selectionEnd);
      }
      else if (input.createTextRange) {
        var range = input.createTextRange();
        range.collapse(true);
        range.moveEnd('character', selectionEnd);
        range.moveStart('character', selectionStart);
        range.select();
      }
    }
  
    function setCaretToPos (input, pos) {
      setSelectionRange(input, pos, pos);
    }
  
  
    function reversed(value){
      value = value.toString()
      return value.split("").reverse().join("");
    }
    function comma_splitted(str, n){
      str = reversed(str)
      var ret = [];
      var i, len;
  
      for(i = 0, len = str.length; i < len; i += n) {
        ret.push(str.substr(i, n))
      }
      return reversed(ret)
    }
  
    function special(val){
      if(!val){
        return '0.00'
      }
      val = val.split(",").join("")
      let s = parseFloat(val).toFixed(2).toString()
      let amts = s.split('.')
      amts[0] = comma_splitted(amts[0],3)
      return [amts.join('.'), amts[0].length]
    }
    function findInputs(){
      document.querySelectorAll('.thousand-separator-input').forEach(field => {
        field.addEventListener('keyup', (event) => {
          let el = event.target
          let special_keys = [37,39]
          if(!special_keys.includes(event.keyCode)){
            let val = el.value
            let result = special(val)
            el.value = (result[0] || val)
            setCaretToPos(el, result[1]);
          }
        })
      })
    }
    $(document).ready(function(){
      setInterval(findInputs,1000)
    })
  })